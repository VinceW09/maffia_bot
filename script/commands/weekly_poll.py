import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks


DATA_DIR = Path(__file__).parent.parent.parent / "data"

DEFAULT_FILE = DATA_DIR / "default_config.json"
WEEK_FILE = DATA_DIR / "current_week.json"
SCRIPTS_FILE = DATA_DIR / "scripts.json"
SHEETS_DIR = DATA_DIR / "sheets"


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


@app_commands.default_permissions(administrator=True)
class WeeklyPoll(commands.GroupCog, group_name="botc", group_description="Hantera veckovis hvit maffia-träff"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ensure_files()
        self.weekly_reset_loop.start()

    def cog_unload(self):
        self.weekly_reset_loop.cancel()

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
                "day_of_week": 2,
                "hour": 14,
                "minute": 15,
                "duration_hours": 6,
                "location": "N207",
                "announcement_channel_id": None,
                "script_upload_channel_id": None
            })

        sat_str = self.get_current_saturday_str()
        if not os.path.exists(WEEK_FILE) or load_json(WEEK_FILE).get("last_saturday") != sat_str:
            self.reset_current_week(sat_str)

    def reset_current_week(self, sat_str: str):
        defaults = load_json(DEFAULT_FILE)
        save_json(WEEK_FILE, {
            "last_saturday": sat_str,
            "day_of_week": defaults["day_of_week"],
            "hour": defaults["hour"],
            "minute": defaults["minute"],
            "location": defaults["location"],
            "poll_message_ids": [],
            "event_id": None
        })

    def get_session_datetime(self, week_data: dict) -> datetime:
        now = datetime.now().astimezone()

        if now.weekday() >= 5:
            monday = now + timedelta(days=(7 - now.weekday()))
        else:
            monday = now - timedelta(days=now.weekday())

        target_day = monday + timedelta(days=week_data["day_of_week"])
        return target_day.replace(
            hour=week_data["hour"],
            minute=week_data["minute"],
            second=0,
            microsecond=0
        )

    @tasks.loop(minutes=5)
    async def weekly_reset_loop(self):
        sat_str = self.get_current_saturday_str()
        week = load_json(WEEK_FILE)
        if week.get("last_saturday") != sat_str:
            self.reset_current_week(sat_str)

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
                "Vänligen bifoga character sheet **och** skriv namnet i samma meddelande",
                mention_author=False
            )
            await err.delete(delay=8)
            return
        
        if len(script_name) > 55:
            await message.add_reaction("❌")
            err = await message.reply(
                "För långt namn...",
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
        if day:
            week["day_of_week"] = day_map[day]
        if hour is not None:
            week["hour"] = hour
        if minute is not None:
            week["minute"] = minute
        if location:
            week["location"] = location
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
        if day:
            defaults["day_of_week"] = day_map[day]
        if hour is not None:
            defaults["hour"] = hour
        if minute is not None:
            defaults["minute"] = minute
        if location:
            defaults["location"] = location
        if announcement_channel:
            defaults["announcement_channel_id"] = announcement_channel.id
        if script_channel:
            defaults["script_upload_channel_id"] = script_channel.id
        save_json(DEFAULT_FILE, defaults)
        await interaction.response.send_message("Ändrade **standard** inställningar.", ephemeral=True)

    @app_commands.command(name="scripts", description="Visa sparade scripts")
    async def manage_scripts(self, interaction: discord.Interaction):
        scripts = load_json(SCRIPTS_FILE)

        if not scripts:
            return await interaction.response.send_message("Inga scripts sparade", ephemeral=True)

        lines = []
        for name, info in scripts.items():
            has_img = "🖼️" if info.get("image") else ""
            lines.append(f"• **{name}** {has_img}")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="poll", description="Skapa veckans event, skicka poll och lägg upp scripts i en tråd")
    async def create_poll(self, interaction: discord.Interaction, message: str, make_event: Optional[bool] = False):
        await interaction.response.defer(ephemeral=True)

        sat_str = self.get_current_saturday_str()
        week = load_json(WEEK_FILE)
        if week.get("last_saturday") != sat_str:
            self.reset_current_week(sat_str)
            week = load_json(WEEK_FILE)

        defaults = load_json(DEFAULT_FILE)
        channel = interaction.guild.get_channel(defaults["announcement_channel_id"])
        if not channel or not isinstance(channel, discord.TextChannel):
            return await interaction.followup.send(
                "Kunde inte hitta announcements-kanalen. Kontrollera `/botc edit_default`.",
                ephemeral=True
            )

        scripts = load_json(SCRIPTS_FILE)
        if not scripts:
            return await interaction.followup.send(
                "Det finns inga sparade scripts att rösta om!",
                ephemeral=True
            )

        session_start = self.get_session_datetime(week)
        end_time = session_start + timedelta(hours=defaults.get("duration_hours", 6))

        if make_event:
            event = await interaction.guild.create_scheduled_event(
                name="Hvit Maffia Träff",
                description=defaults.get("description", "BOTC"),
                start_time=session_start,
                end_time=end_time,
                location=week["location"],
                entity_type=discord.EntityType.external,
                privacy_level=discord.PrivacyLevel.guild_only
            )

        now = datetime.now().astimezone()
        remaining = session_start - now
        poll_duration = max(timedelta(hours=1), min(remaining, timedelta(days=32)))

        script_items = list(scripts.keys())
        chunks = [script_items[i:i + 10] for i in range(0, len(script_items), 10)]
        total_polls = len(chunks)

        announcement_content = f"{message}\n{event.url if make_event else ''}"
        poll_messages = []

        for index, chunk in enumerate(chunks, start=1):
    
            title = f"Vilka scripts? ({index}/{total_polls})" if total_polls > 1 else "Vilka scripts?"

            poll = discord.Poll(
            question=title,
            duration=poll_duration,
            multiple=True
            )
            for script_name in chunk:
                poll.add_answer(text=script_name)

            content = announcement_content if index == 1 else None
            msg = await channel.send(content=content, poll=poll)
            poll_messages.append(msg)

        thread = await poll_messages[-1].create_thread(
            name="Character Sheets — Veckans Scripts",
        )

        for script_name, info in scripts.items():
            img_path = info.get("image")
            if img_path and os.path.exists(img_path):
                await thread.send(
                    content=f"{script_name}",
                    file=discord.File(img_path)
                )
            else:
                await thread.send(content=f"**{script_name}** *(ingen bild hittades)*")

        await thread.edit(locked=True)

        week["poll_message_ids"] = [m.id for m in poll_messages]
        week["event_id"] = (event.id) if make_event else None
        save_json(WEEK_FILE, week)

        await interaction.followup.send(
            f"Skapade event, skickade poll och lade upp alla character sheets i tråden {thread.mention}!",
            ephemeral=True
        )

    @app_commands.command(name="winner", description="Annoncera veckans script efter pollen")
    async def announce_winner(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        poll_ids = load_json(WEEK_FILE)["poll_message_ids"]
        announcement_channel = await self.bot.fetch_channel(load_json(DEFAULT_FILE)["announcement_channel_id"])
        
        if not announcement_channel or not poll_ids:
            await interaction.followup.send("Hittade ingen aktiv poll att räkna röster från.", ephemeral=True)
            return

        highest_votes = 0
        winners: list[str] = []
        for poll_id in poll_ids:
            try:
                poll_message = await announcement_channel.fetch_message(poll_id)
            except discord.NotFound:
                continue

            if not poll_message.poll:
                continue

            for answer in poll_message.poll.answers:
                if answer.vote_count > highest_votes:
                    highest_votes = answer.vote_count
                    winners = [answer.text]
                elif answer.vote_count == highest_votes and highest_votes > 0:
                    winners.append(answer.text)

        if not winners:
            await interaction.followup.send("Ingen röstade på något script den här veckan!")
            return

        if len(winners) == 1:
            winner_name = winners[0]

            script_data = load_json(SCRIPTS_FILE)[winner_name]

            image_path = script_data["image"]
            text = f"Veckans vinnande script med **{highest_votes}** röst{'er' if highest_votes > 1 else ''} är: **{winner_name}**!"

            if image_path and os.path.exists(image_path):
                await announcement_channel.send(content=text, file=discord.File(image_path))
            else:
                await announcement_channel.send(content=text)
        else:
            if len(winners) == 2:
                formatted = f"**{winners[0]}** och **{winners[1]}**"
            else:
                formatted = ", ".join(f"**{w}**" for w in winners[:-1]) + f" och **{winners[-1]}**"

            await announcement_channel.send(
                f"Oavgjort med **{highest_votes}** röst{'er' if highest_votes > 1 else ''} mellan {formatted}!"
            )

        await interaction.followup.send("Vinnaren har annonserats!", ephemeral=True)

    @app_commands.command(name="reset", description="Återställ veckans inställningar instant")
    async def reset_week_now(self, interaction: discord.Interaction):
        sat_str = self.get_current_saturday_str()
        self.reset_current_week(sat_str)
        await interaction.response.send_message(
            "Veckan har återställts till standardinställningarna och du kan nu skicka en ny `/botc poll`!",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(WeeklyPoll(bot))