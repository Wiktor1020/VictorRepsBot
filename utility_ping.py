import discord
from discord.ext import commands
import time
import datetime

class UtilityPing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @discord.app_commands.command(name="ping", description="Sprawdź opóźnienie bota.")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(
            f"🏓 **Ping:** `{latency}ms`",
            ephemeral=True
        )

    @discord.app_commands.command(name="uptime", description="Sprawdź jak długo bot jest online.")
    async def uptime(self, interaction: discord.Interaction):
        now = time.time()
        delta = int(now - self.start_time)

        days, remainder = divmod(delta, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

        await interaction.response.send_message(
            f"⏳ **Uptime bota:** `{uptime_str}`",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(UtilityPing(bot))
