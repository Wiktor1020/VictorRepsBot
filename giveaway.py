import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import json
import os
from datetime import datetime, timedelta


GIVEAWAY_FILE = "giveaways.json"


def load_giveaways():
    if os.path.exists(GIVEAWAY_FILE):
        with open(GIVEAWAY_FILE, "r") as f:
            return json.load(f)
    return {}


def save_giveaways(data):
    with open(GIVEAWAY_FILE, "w") as f:
        json.dump(data, f, indent=4)


class GiveawayView(discord.ui.View):
    def __init__(self, message_id: int):
        super().__init__(timeout=None)
        self.message_id = message_id

    @discord.ui.button(label="🎉 Dołącz do giveaway!", style=discord.ButtonStyle.green)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        giveaways = load_giveaways()
        g = giveaways.get(str(self.message_id))

        if not g:
            return await interaction.response.send_message("❌ Ten giveaway już się zakończył!", ephemeral=True)

        if str(interaction.user.id) in g["participants"]:
            await interaction.response.send_message("Już jesteś zapisany na ten giveaway! 🎁", ephemeral=True)
            return

        g["participants"].append(str(interaction.user.id))
        save_giveaways(giveaways)
        await interaction.response.send_message("✅ Dołączyłeś do giveaway’a!", ephemeral=True)


async def start_giveaway(bot, interaction: discord.Interaction, czas_minuty: int, nagroda: str):
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Nagroda:** {nagroda}\nKliknij przycisk poniżej, aby dołączyć!",
        color=discord.Color.gold(),
    )
    embed.add_field(name="⏰ Czas trwania", value=f"{czas_minuty} minut", inline=False)
    embed.set_footer(text=f"Zakończenie: {datetime.utcnow() + timedelta(minutes=czas_minuty):%Y-%m-%d %H:%M UTC}")

    message = await interaction.channel.send(embed=embed, view=GiveawayView(message_id=0))
    await interaction.response.send_message(f"Giveaway wystartował! 🎁 {nagroda}", ephemeral=True)

    giveaways = load_giveaways()
    giveaways[str(message.id)] = {
        "channel_id": message.channel.id,
        "end_time": (datetime.utcnow() + timedelta(minutes=czas_minuty)).isoformat(),
        "reward": nagroda,
        "participants": [],
    }
    save_giveaways(giveaways)

    bot.add_view(GiveawayView(message_id=message.id))

    await asyncio.sleep(czas_minuty * 60)
    await end_giveaway(bot, message.id)


async def end_giveaway(bot, message_id: int):
    giveaways = load_giveaways()
    g = giveaways.pop(str(message_id), None)
    if not g:
        return

    save_giveaways(giveaways)

    channel = bot.get_channel(g["channel_id"])
    message = await channel.fetch_message(message_id)

    if not g["participants"]:
        await channel.send("😢 Giveaway zakończony, ale nikt nie wziął udziału.")
        return

    winner_id = int(g["participants"][0]) if len(g["participants"]) == 1 else int(
        __import__("random").choice(g["participants"])
    )

    winner = await bot.fetch_user(winner_id)
    await channel.send(f"🎉 Gratulacje {winner.mention}! Wygrałeś **{g['reward']}**! 🥳")

    embed = message.embeds[0]
    embed.title = "✅ GIVEAWAY ZAKOŃCZONY ✅"
    await message.edit(embed=embed, view=None)


def setup_giveaway(bot: commands.Bot):
    @bot.tree.command(name="giveaway", description="Stwórz giveaway")
    @app_commands.describe(czas_minuty="Czas trwania w minutach", nagroda="Nagroda giveaway’a")
    async def giveaway(interaction: discord.Interaction, czas_minuty: int, nagroda: str):
        await start_giveaway(bot, interaction, czas_minuty, nagroda)

    @bot.event
    async def on_ready():
        giveaways = load_giveaways()
        for message_id, g in giveaways.items():
            bot.add_view(GiveawayView(message_id=int(message_id)))
        print(f"✅ Przywrócono {len(giveaways)} aktywnych giveaway’ów.")
