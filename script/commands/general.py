import discord
from discord import app_commands
from discord.ext import commands

import random


class Commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Checks the bot's ping!")
    async def ping(self, interaction: discord.Interaction):
        latency_ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! I reacted in: {latency_ms} milliseconds!", ephemeral=True)

    @app_commands.command(name="whisper", description="Får botten att säga något anonymt i kanalen")
    async def whisper(self, interaction: discord.Interaction, message: str):
        await interaction.response.send_message("Skickat! :ebbe:", ephemeral=True)
        await interaction.channel.send(message)

    @app_commands.command(name="sus-o-meter", description="Kollar hur stor chans det är att någon är Demonen")
    async def sus(self, interaction: discord.Interaction, member: discord.Member):
        if member.id == self.bot.user.id:
            await interaction.response.send_message(f"{member.mention} är Townsfolk, vad trodde du ens?")
            return

        percent = random.randint(0, 100)
        verdict = "nOMinErA hOnOM!!" if percent >= 80 else "Ganska sus..." if percent >= 50 else "Bara en lunatic, trust"
        await interaction.response.send_message(f"{member.mention} är **{percent}% Demon** — {verdict}")

    @app_commands.command(name="coinflip", description="Singlar slant (perfekt för oavgjort!)")
    async def coinflip(self, interaction: discord.Interaction):
        result = random.choice(["krona", "klave"])
        await interaction.response.send_message(f"Det blev **{result}**!")


async def setup(bot: commands.Bot):
    await bot.add_cog(Commands(bot))