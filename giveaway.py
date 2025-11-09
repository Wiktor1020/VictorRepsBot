import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import json
import os
from datetime import datetime, timedelta
import re
import random

# 🔹 Plik zapisu aktywnych giveawayów
GIVEAWAY_FILE = "giveaways.json"


# ---------------------- FUNKCJE POMOCNICZE -----------------------
def load_giveaways():
    if os.path.exists(GIVEAWAY_FILE):
        with open(GIVEAWAY_FILE, "r") as f:
            return json.load(f)
    return {}


def save_giveaways(data):
    with open(GIVEAWAY_FILE, "w") as f:
        json.dump(data, f, indent=4)


def parse_time(time_str: str):
    """Konwertuje '2d', '5h', '30m' → sekundy"""
    match = re.match(r"^(\d+)([dhm])$", time_str.lower())
    if not match:
        return None
    value, unit = match.groups()
    value = int(value)
    if unit == "d":
        return value * 86400
    if unit == "h":
        return value * 3600
    if unit == "m":
        return value * 60
    return None


# ---------------------- WIDOK (PRZYCISK) -----------------------
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
            return await interaction.response.send_message("Już jesteś zapisany na ten giveaway! 🎁", ephemeral=True)

        g["participants"].append(str(interaction.user.id))
        save_giveaways(giveaways)
        await interaction.response.send_message("✅ Dołączyłeś do giveaway’a!", ephemeral=True)


# ---------------------- LOGIKA GIVEAWAY -----------------------
async def start_giveaway(bot, interaction, czas: str, nagroda: str, opis: str, naglowek: str):
    seconds = parse_time(czas)
    if not seconds:
        return await interaction.response.send_message("❌ Nieprawidłowy format czasu! Użyj np. `2d`, `5h`, `30m`.", ephemeral=True)

    end_time = datetime.utcnow() + timedelta(seconds=seconds)

    embed = discord.Embed(
        title=f"🎉 {naglowek} 🎉",
        description=f"**Nagroda:** {nagroda}\n\n{opis}\n\n🕒 **Koniec:** <t:{int(end_time.timestamp())}:R>",
        color=discord.Color.from_rgb(46, 204, 113),  # zielony jak panel ticketów
    )
    embed.set_footer(text=f"Giveaway zakończy się {end_time:%Y-%m-%d %H:%M UTC}")

    message = await interaction.channel.send(embed=embed, view=GiveawayView(message_id=0))
    await interaction.response.send_message(f"✅ Giveaway wystartował: **{nagroda}**", ephemeral=True)

    giveaways = load_giveaways()
    giveaways[str(message.id)] = {
        "channel_id": message.channel.id,
        "end_time": end_time.isoformat(),
        "reward": nagroda,
        "participants": [],
        "naglowek": naglowek,
        "opis": opis
    }
    save_giveaways(giveaways)

    bot.add_view(GiveawayView(message_id=message.id))
    await asyncio.sleep(seconds)
    await end_giveaway(bot, message.id)


async def end_giveaway(bot, message_id: int, manual=False):
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

    winner_id = int(random.choice(g["participants"]))
    winner = await bot.fetch_user(winner_id)

    embed = message.embeds[0]
    embed.title = f"✅ GIVEAWAY ZAKOŃCZONY ✅"
    embed.description += f"\n\n🎉 **Zwycięzca:** {winner.mention}"
    await message.edit(embed=embed, view=None)

    await channel.send(f"🎊 Gratulacje {winner.mention}! Wygrałeś **{g['reward']}**! 🥳")


# ---------------------- REJESTRACJA KOMEND -----------------------
def setup_giveaway(bot: commands.Bot):
    @bot.tree.command(name="giveaway", description="🎉 Utwórz giveaway")
    @app_commands.describe(
        czas="Czas trwania (np. 2d = 2 dni, 5h = 5 godzin, 30m = 30 minut)",
        nagroda="Nagroda giveaway’a",
        naglowek="Tytuł / temat giveaway’a",
        opis="Opis, np. zasady, wymagania itd."
    )
    async def giveaway(interaction: discord.Interaction, czas: str, nagroda: str, naglowek: str, opis: str):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("⛔ Tylko właściciel lub administrator serwera może to zrobić.", ephemeral=True)

        await start_giveaway(bot, interaction, czas, nagroda, opis, naglowek)

    @bot.tree.command(name="giveawayend", description="⏹️ Ręcznie zakończ giveaway")
    @app_commands.describe(message_id="ID wiadomości giveaway’a do zakończenia")
    async def giveawayend(interaction: discord.Interaction, message_id: str):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("⛔ Brak uprawnień.", ephemeral=True)

        await end_giveaway(bot, int(message_id), manual=True)
        await interaction.response.send_message("✅ Giveaway został zakończony ręcznie.", ephemeral=True)

    @bot.tree.command(name="giveawayreroll", description="🔁 Wylosuj nowego zwycięzcę")
    @app_commands.describe(message_id="ID wiadomości giveaway’a do rerollu")
    async def giveawayreroll(interaction: discord.Interaction, message_id: str):
        giveaways = load_giveaways()
        g = giveaways.get(str(message_id))
        if not g:
            return await interaction.response.send_message("❌ Giveaway nie został znaleziony lub już zakończony.", ephemeral=True)

        if not g["participants"]:
            return await interaction.response.send_message("😢 Nikt nie brał udziału w giveawayu.", ephemeral=True)

        winner_id = int(random.choice(g["participants"]))
        winner = await bot.fetch_user(winner_id)
        await interaction.response.send_message(f"🎉 Nowy zwycięzca: {winner.mention} (Nagroda: **{g['reward']}**)", ephemeral=False)

    # Przywrócenie widoków po restarcie
    @bot.event
    async def on_ready():
        giveaways = load_giveaways()
        for message_id in giveaways.keys():
            bot.add_view(GiveawayView(message_id=int(message_id)))
        print(f"✅ Przywrócono {len(giveaways)} aktywnych giveaway’ów.")
