import os
import discord
from dotenv import load_dotenv
from discord.ext import commands


load_dotenv() 
token = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = commands.Bot(command_prefix="/", intents=intents)

@client.event
async def on_ready():
    print(f'Maffia Bot has successfully logged in as: {client.user}')
    try:
        synced = await client.tree.sync()
        print(f"Synced {len(synced)} command(s)")
        print("Bot is now online!")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# - ↓ - ALL COMMANDS ↓ ↓ ALL COMMANDS ↓ ↓ ALL COMMANDS - ↓ - #

# /ping
@client.tree.command(name="ping", description="Checks the bot's ping!")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! I reacted in: {round((round(client.latency, 3))*1000)} milliseconds!", ephemeral=True)

# -  - END OF ALL COMMANDS  - || -  END OF ALL COMMANDS -  - #

@client.tree.error
async def on_app_command_error(interaction, error):
    if isinstance(error, commands.MissingPermissions):
        await interaction.response.send_message(error, ephemeral=True)
    else: raise error

client.run(token)