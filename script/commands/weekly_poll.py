import json
import os
import re
from datetime import datetime, timedelta
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks


DATA_DIR = Path(__file__).parent.parent.parent / "data"

DEFAULT_FILE = DATA_DIR + "default_config.json"
WEEK_FILE = DATA_DIR + "current_week.json"
SCRIPTS_FILE = DATA_DIR + "scripts.json"
SHEETS_DIR = DATA_DIR + "sheets"


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


class ScriptSheetView(discord.ui.View):
    def __init__(self, scripts: dict):
        super().__init__(timeout=None)
        for script_name in list(scripts.keys())[:25]:
            btn = discord.ui.Button(
                label=f"Sheet: {script_name}",
                style=discord.ButtonStyle.secondary,
                custom_id=f"botc_sheet:{script_name}"
            )
            btn.callback = self.make_callback(script_name)
            self.add_item(btn)

    def make_callback(self, script_name: str):
        async def callback(interaction: discord.Interaction):
            scripts = load_json(SCRIPTS_FILE)
            script = scripts.get(script_name)
            if not script:
                return await interaction.response.send_message("Script ej hittat.", ephemeral=True)

            image_path = script.get("image")
            if not image_path or not os.path.exists(image_path):
                return await interaction.response.send_message("Charachter sheet för scriptet kunde inte hittas.", ephemeral=True)

            try:
                await interaction.user.send(
                    content=f"**{script_name} — Character Sheet**",
                    file=discord.File(image_path)
                )
                await interaction.response.send_message(f"Skickade **{script_name}** till dig!", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("Jag kunde inte DM:a dig! Vänligen aktivera DMs från server medlemmar.", ephemeral=True)
        return callback


@app_commands.default_permissions(administrator=True)
class WeeklyPoll(commands.GroupCog, group_name="botc", group_description="Hantera veckovis hvit maffia-träff"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ensure_files()
        self.scheduler_loop.start()

    def cog_unload(self):
        self.scheduler_loop.cancel()

    def get_current_saturday_str(self) -> str:
        now = datetime.now().astimezone()
        days_since_sat = (now.weekday() - 5) % 7
        return (now - timedelta(days=days_since_sat)).strftime("%Y-%m-%d")

    def ensure_files(self):
        os.makedirs(SHEETS_DIR, exist_ok=True)

        if not os.path.exists(SCRIPTS_FILE):
            save_json(SCRIPTS_FILE, {})

        if not os.path.exists(DEFAULT_FILE):
            save_json(DEFAULT_FILE, {
                "day_of_week": 2, "hour": 14, "minute": 15, "duration_hours": 6,
                "location": "N207", "description": "BOTC",
                "announcement_channel_id": 1574732413823750245, "script_upload_channel_id": 1574732658322309233
            })

        sat_str = self.get_current_saturday_str()
        if not os.path.exists(WEEK_FILE) or load_json(WEEK_FILE).get("last_saturday") != sat_str:
            self.reset_current_week(sat_str)

    def reset_current_week(self, sat_str: str):
        defaults = load_json(DEFAULT_FILE)
        save_json(WEEK_FILE, {
            "last_saturday": sat_str,
            "skipped": False,
            "day_of_week": defaults["day_of_week"],
            "hour": defaults["hour"],
            "minute": defaults["minute"],
            "location": defaults["location"],
            "poll_posted": False,
            "poll_message_id": None,
            "event_id": None
        })

    def get_session_datetime(self, week_data: dict) -> datetime:
        now = datetime.now().astimezone()
    
        if now.weekday() >= 5: monday = now + timedelta(days=(7 - now.weekday()))
        else: monday = now - timedelta(days=now.weekday())

        target_day = monday + timedelta(days=week_data["day_of_week"])
        return target_day.replace(
            hour=week_data["hour"],
            minute=week_data["minute"],
            second=0,
            microsecond=0
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        defaults = load_json(DEFAULT_FILE)
        if message.channel.id != defaults.get("script_upload_channel_id"):
            return

        script_name = message.content.strip().split("\n")[0].strip()
        if not script_name or not message.attachments:
            await message.add_reaction("❌")
            err = await message.reply(
                "Vänligen bifoga charachter sheet **och** skriv namnet i samma meddelande",
                mention_author=False
            )
            await err.delete(delay=8)
            return

        attachment = message.attachments[0]
        if not attachment.content_type or not attachment.content_type.startswith("image/"):
            await message.add_reaction("❌")
            err = await message.reply("Bilden måste vara en bildfil (PNG, JPG, etc.).", mention_author=False)
            await err.delete(delay=8)
            return

        ext = os.path.splitext(attachment.filename)[1] or ".png"
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", script_name)
        saved_image_path = os.path.join(SHEETS_DIR, f"{safe_name}{ext}")
        await attachment.save(saved_image_path)

        scripts = load_json(SCRIPTS_FILE)
        scripts[script_name] = {
            "image": saved_image_path,
            "message_id": message.id
        }
        save_json(SCRIPTS_FILE, scripts)

        await message.add_reaction("✅")

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        defaults = load_json(DEFAULT_FILE)
        if payload.channel_id != defaults.get("script_upload_channel_id"):
            return

        scripts = load_json(SCRIPTS_FILE)
        script_to_remove = None

        for name, info in scripts.items():
            if info.get("message_id") == payload.message_id:
                script_to_remove = name
                break

        if script_to_remove:
            img_path = scripts[script_to_remove].get("image")
            if img_path and os.path.exists(img_path):
                os.remove(img_path)

            del scripts[script_to_remove]
            save_json(SCRIPTS_FILE, scripts)
            print(f"[BOTC] Deleted script '{script_to_remove}' because its upload message was deleted.")

    @app_commands.command(name="skip", description="Ställa in/återställa veckans maffia-träff")
    async def skip_week(self, interaction: discord.Interaction, skip: bool = True):
        week = load_json(WEEK_FILE)
        week["skipped"] = skip
        save_json(WEEK_FILE, week)
        await interaction.response.send_message(f"Denna veckas hvit maffia-träff är nu **{'inställd' if skip else 'återställd'}**.", ephemeral=True)

    @app_commands.command(name="edit_week", description="Ändra info för denna vecka endast (Lör-Fre)")
    async def edit_week(
        self,
        interaction: discord.Interaction,
        day: Optional[Literal["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag"]] = None,
        hour: Optional[app_commands.Range[int, 0, 23]] = None,
        minute: Optional[app_commands.Range[int, 0, 59]] = None,
        location: Optional[str] = None,
    ):
        day_map = {"Måndag": 0, "Tisdag": 1, "Onsdag": 2, "Torsdag": 3, "Fredag": 4}
        week = load_json(WEEK_FILE)
        if day: week["day_of_week"] = day_map[day]
        if hour is not None: week["hour"] = hour
        if minute is not None: week["minute"] = minute
        if location: week["location"] = location
        save_json(WEEK_FILE, week)
        await interaction.response.send_message("Ändrade **denna veckas** info.", ephemeral=True)

    @app_commands.command(name="edit_default", description="Ändra standard infon/inställningar")
    async def edit_default(
        self,
        interaction: discord.Interaction,
        day: Optional[Literal["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag"]] = None,
        hour: Optional[app_commands.Range[int, 0, 23]] = None,
        minute: Optional[app_commands.Range[int, 0, 59]] = None,
        location: Optional[str] = None,
        announcement_channel: Optional[discord.TextChannel] = None,
        script_channel: Optional[discord.TextChannel] = None
    ):
        day_map = {"Måndag": 0, "Tisdag": 1, "Onsdag": 2, "Torsdag": 3, "Fredag": 4}
        defaults = load_json(DEFAULT_FILE)
        if day: defaults["day_of_week"] = day_map[day]
        if hour is not None: defaults["hour"] = hour
        if minute is not None: defaults["minute"] = minute
        if location: defaults["location"] = location
        if announcement_channel: defaults["announcement_channel_id"] = announcement_channel.id
        if script_channel: defaults["script_upload_channel_id"] = script_channel.id
        save_json(DEFAULT_FILE, defaults)
        await interaction.response.send_message("Ändrade **standard** inställningar.", ephemeral=True)

    @app_commands.command(name="scripts", description="Visa scripts")
    async def manage_scripts(self, interaction: discord.Interaction):
        scripts = load_json(SCRIPTS_FILE)

        if not scripts:
            return await interaction.response.send_message("Inga scripts sparade", ephemeral=True)

        lines = []
        for name, info in scripts.items():
            has_img = "🖼️" if info.get("image") else ""
            lines.append(f"• **{name}** {has_img} {info.get('url', '')}")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @tasks.loop(minutes=1)
    async def scheduler_loop(self):
        await self.bot.wait_until_ready()

        sat_str = self.get_current_saturday_str()
        week = load_json(WEEK_FILE)
        if week.get("week_saturday") != sat_str:
            self.reset_current_week(sat_str)
            week = load_json(WEEK_FILE)

        if week.get("skipped"):
            return

        defaults = load_json(DEFAULT_FILE)
        now = datetime.now().astimezone()
        session_start = self.get_session_datetime(week)
        poll_open_time = session_start - timedelta(days=2)

        channel = self.bot.get_channel(defaults["announcement_channel_id"])
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        if not week["poll_posted"] and poll_open_time <= now < session_start:
            scripts = load_json(SCRIPTS_FILE)
            if not scripts:
                return

            end_time = session_start + timedelta(hours=defaults.get("duration_hours", 3))
            event = await channel.guild.create_scheduled_event(
                name="Hvit Maffia Träff",
                start_time=session_start,
                end_time=end_time,
                location=week["location"],
                entity_type=discord.EntityType.external,
                privacy_level=discord.PrivacyLevel.guild_only
            )

            poll = discord.Poll(
                question="Vilka scripts?",
                duration=timedelta(hours=47, minutes=30),
                multiple=True
            )
            for script_name in list(scripts.keys())[:10]:
                poll.add_answer(text=script_name[:55])

            msg = await channel.send(
                content=f"@aktiv Hvit Maffia Träff på **{discord.utils.format_dt(session_start, 'F')}** i **{week['location']}**\n{event.url}",
                poll=poll,
                view=ScriptSheetView(scripts)
            )

            week["poll_posted"] = True
            week["poll_message_id"] = msg.id
            week["event_id"] = event.id
            save_json(WEEK_FILE, week)


async def setup(bot: commands.Bot):
    await bot.add_cog(WeeklyPoll(bot))