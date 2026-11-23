

# /ping
@client.tree.command(name="ping", description="Checks the bot's ping!")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! I reacted in: {round((round(client.latency, 3))*1000)} milliseconds!", ephemeral=True)