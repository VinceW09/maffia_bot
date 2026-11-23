import os
import discord
from pathlib import Path
from dotenv import load_dotenv
from discord.ext import commands


load_dotenv() 
token = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MaffiaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="/", intents=intents)

    async def setup_hook(self):
        commands_dir = Path(__file__).parent / "commands"
        for file in commands_dir.glob("*.py"):
            await self.load_extension(f"commands.{file.stem}")

        synced = await self.tree.sync()
        print(f"Synced {len(synced)} command(s)")

client = MaffiaBot()

@client.event
async def on_ready():
    print(f"Maffia Bot has successfully logged in as: {client.user}")
    print("Bot is now online!")

@client.tree.error
async def on_app_command_error(interaction, error):
    if isinstance(error, commands.MissingPermissions):
        await interaction.response.send_message(error, ephemeral=True)
    else: raise error

client.run(token)