import discord
from discord import app_commands
from discord.ext import commands


class Commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Checks the bot's ping!")
    async def ping(self, interaction: discord.Interaction):
        latency_ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! I reacted in: {latency_ms} milliseconds!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Commands(bot))