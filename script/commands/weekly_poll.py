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

POLL_FILE = DATA_DIR / "poll.json"
SCRIPTS_FILE = DATA_DIR / "scripts.json"
SHEETS_DIR = DATA_DIR / "sheets"


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


@app_commands.default_permissions(administrator=True)
class WeeklyPoll(commands.GroupCog, group_name="botc", group_description="Admin-kommandon gällande botc poll/script hantering."):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ensure_files()

    def ensure_files(self):
        os.makedirs(SHEETS_DIR, exist_ok=True)

        if not os.path.exists(SCRIPTS_FILE):

            all_keys = [f"{num}{let}" for num in string.digits for let in string.ascii_uppercase]
            random.shuffle(all_keys)
        
            new_scripts_json = {
                "available_keys": all_keys,
                "script_channel_id": None,
                "scripts": {}
            }

            save_json(SCRIPTS_FILE, new_scripts_json)

        if not os.path.exists(POLL_FILE):
            new_poll_json = {
                "poll_channel_id": None,
                "message_ids": []
            }
            save_json(POLL_FILE, new_poll_json)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        scripts_json = load_json(SCRIPTS_FILE)
        if message.channel.id != defaults.get("script_channel_id"):
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

        key = scripts_json["available_keys"].pop()
        scripts["scripts"][key] = {
            "name": script_name,
            "image": saved_image_path,
            "in_poll": False,
            "message_id": message.id
        }
        save_json(SCRIPTS_FILE, scripts_json)

        await message.add_reaction("✅")

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        scripts_json = load_json(SCRIPTS_FILE)
        if payload.channel_id != defaults.get("script_channel_id"):
            return

        scripts = scripts_json["scripts"]
        script_to_remove = None

        for key, script_data in scripts.items():
            if script_data.get("message_id") == payload.message_id:
                script_to_remove = key
                break

        if script_to_remove:
            img_path = scripts[script_to_remove].get("image")
            if img_path and os.path.exists(img_path):
                os.remove(img_path)
            
            del scripts[script_to_remove]

            if script_to_remove not in scripts_json["available_keys"]:
                scripts_json["available_keys"].append(script_to_remove)

            save_json(SCRIPTS_FILE, scripts_json)
            print(f"[BOTC] Deleted script with key '{script_to_remove}' because its upload message was deleted.")

    @app_commands.command(name="set_script_channel", description="Ändra script kanal **rensar script databas**")
    async def set_script_channel(self, interaction: discord.Interaction, script_channel: discord.TextChannel):

        script_json = load_json(SCRIPTS_FILE)
        script_json["script_channel_id"] = script_channel.id
        save_json(SCRIPTS_FILE, script_json)

        await interaction.response.send_message(f"Ändrade scripts_kanalen till {script_channel}", ephemeral=True)

    @app_commands.command(name="saved_scripts", description="Visa sparade script")
    async def saved_scripts(self, interaction: discord.Interaction):
        scripts_json = load_json(SCRIPTS_FILE)

        if not scripts_json["scripts"]:
            return await interaction.response.send_message("Inga scripts sparade", ephemeral=True)
        
        scripts = scripts_json["scripts"].items()

        lines = []
        for key, script_data in scripts_json["scripts"].items():
            lines.append(f" - **{script_data['name']}**{' :ballot_box:' if script_data['in_poll'] else ''}: {key}")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="display_script", description="Visa sparat script")
    async def display_script(self, interaction: discord.Interaction, script_key: str, channel: discord.TextChannel):
        scripts_json = load_json(SCRIPTS_FILE)

        if not scripts_json["scripts"][script_key]:
            return await interaction.response.send_message("Scriptet finns inte.", ephemeral=True)

        script = scripts_json["scripts"][script_key]
        img_path = script.get("image")
        if img_path and os.path.exists(img_path):
            channel.send(content=(f"**{script['name']}**"), file=discord.File(img_path))
        else:
            return await interaction.response.send_message("Hittade inte bilden", ephemeral=True)

    @app_commands.command(name="add_script", description="Addera script till poll")
    async def display_script(self, interaction: discord.Interaction, script_key: str):
        scripts_json = load_json(SCRIPTS_FILE)

        if not scripts_json["scripts"][script_key]:
            return await interaction.response.send_message("Scriptet finns inte.", ephemeral=True)

        script = scripts_json["scripts"][script_key]
        
        if script["in_poll"]:
            return await interaction.response.send_message("Redan tillagt", ephemeral=True)
        else:
            script["in_poll"] = True
            script_channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
            script_message = await script_channel.fetch_message(script["message_id"])
            await script_message.add_reaction("🗳️")
            return await interaction.response.send_message(f"{script['name']} är nu tillagt.", ephemeral=True)

    @app_commands.command(name="remove_script", description="Ta bort script från poll")
    async def display_script(self, interaction: discord.Interaction, script_key: str):
        scripts_json = load_json(SCRIPTS_FILE)

        if not scripts_json["scripts"][script_key]:
            return await interaction.response.send_message("Scriptet finns inte.", ephemeral=True)

        script = scripts_json["scripts"][script_key]
        
        if not script["in_poll"]:
            return await interaction.response.send_message("Redan borttaget", ephemeral=True)
        else:
            script["in_poll"] = False
            script_channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
            script_message = await script_channel.fetch_message(script["message_id"])
            await script_message.remove_reaction("🗳️")
            return await interaction.response.send_message(f"{script['name']} är nu tillagt.", ephemeral=True)
            
    @app_commands.command(name="poll", description="Skicka poll och lägg upp scripts i en tråd")
    async def create_poll(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        await interaction.response.defer(ephemeral=True)

        scripts_json = load_json(SCRIPTS_FILE)
        scripts = scripts_json["scripts"]
        if not scripts:
            return await interaction.followup.send(
                "Det finns inga sparade scripts att rösta om!",
                ephemeral=True
            )

        poll_duration = timedelta(days=30)

        script_names = [data["name"] for data in scripts.values() if data["in_poll"]]
        chunks = [script_names[i:i + 10] for i in range(0, len(script_names), 10)]
        total_polls = len(chunks)

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

            content = message if index == 1 else None
            msg = await channel.send(content=content, poll=poll)
            poll_messages.append(msg)

        thread = await poll_messages[-1].create_thread(
            name="Character Sheets — Veckans Scripts",
        )

        for key, script_data in scripts.items():
            img_path = script_data["image"]
            if img_path and os.path.exists(img_path):
                await thread.send(
                    content=f"{script_name}",
                    file=discord.File(img_path)
                )
            else:
                await thread.send(content=f"**{script_name}** *(ingen bild hittades)*")

        await thread.edit(locked=True)

        poll_json = load_json(POLL_FILE)
        poll_json["poll_channel_id"] = channel.id
        poll_json["message_ids"] = [m.id for m in poll_messages]
        save_json(POLL_FILE, poll_json)

        await interaction.followup.send(
            f"Skickade poll och lade upp alla character sheets i tråden {thread.mention}!",
            ephemeral=True
        )

    @app_commands.command(name="close", description="Stäng pollen")
    async def close(self, interaction: discord.Interaction):
        poll_json = load_json(POLL_FILE)
        if not poll_json["poll_channel_id"]: 
            return await interaction.followup.send("Finns ingen poll att stänga", ephemeral=True)
        poll_channel = await self.bot.fetch_channel(poll_json["poll_channel_id"])
        poll_message = await poll_channel.fetch_message(poll_id)
        if poll_message:
            poll_message.end_poll()
        else:
            return await interaction.followup.send("Finns ingen poll att stänga", ephemeral=True)
        
        await interaction.followup.send("Poll stängdes", ephemeral=True)

    @app_commands.command(name="winner", description="Annoncera script efter pollen")
    async def winner(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        
        poll_json = load_json(POLL_FILE)
        poll_ids = poll_json["message_ids"]
        poll_channel = await self.bot.fetch_channel(poll_json["poll_channel_id"])
        
        if not poll_channel or not poll_ids:
            return await interaction.followup.send("Hittade ingen aktiv poll att räkna röster från.", ephemeral=True)

        highest_votes = 0
        winners: list[str] = []
        for poll_id in poll_ids:
            try:
                poll_message = await poll_channel.fetch_message(poll_id)
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

            scripts_json = load_json(SCRIPTS_FILE)
            scripts = scripts_json["scripts"]

            if not scripts:
                return await interaction.followup.send("Finns inga script längre?", ephemeral=True)

            script_data = next(
                (data for data in scripts.values() if data["name"] == winner_name),
                None
            )

            if script_data:
                image_path = script_data["image"]
            else:
                return await interaction.followup.send(f"Vinnande scriptet, {winner_name}, är borta", ephemeral=True)

            text = f"Veckans vinnande script med **{highest_votes}** röst{'er' if highest_votes > 1 else ''} är: **{winner_name}**!"

            if image_path and os.path.exists(image_path):
                await channel.send(content=text, file=discord.File(image_path))
            else:
                await channel.send(content=text)
        else:
            if len(winners) == 2:
                formatted = f"**{winners[0]}** och **{winners[1]}**"
            else:
                formatted = ", ".join(f"**{w}**" for w in winners[:-1]) + f" och **{winners[-1]}**"

            await channel.send(
                f"Oavgjort med **{highest_votes}** röst{'er' if highest_votes > 1 else ''} mellan {formatted}!"
            )

        await poll_message.end_poll()
        await interaction.followup.send("Vinnaren har annonserats!", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(WeeklyPoll(bot))