import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import json
import os
from datetime import datetime, timedelta
import random

# --- STAŁE ---
GIVEAWAY_FILE = "giveaways.json"


# --- FUNKCJE POMOCNICZE ---

def load_giveaways():
    if os.path.exists(GIVEAWAY_FILE):
        try:
            with open(GIVEAWAY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def save_giveaways(data):
    with open(GIVEAWAY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# --- KLASA WIDOKU ---

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
            return await interaction.response.send_message("⚠️ Już bierzesz udział w tym giveawayu!", ephemeral=True)

        g["participants"].append(str(interaction.user.id))
        save_giveaways(giveaways)
        await interaction.response.send_message("✅ Dołączyłeś do giveaway’a!", ephemeral=True)


# --- FUNKCJE GIVEAWAY ---

async def start_giveaway(bot, interaction: discord.Interaction, czas_minuty: int, nagroda: str):
    end_time = datetime.utcnow() + timedelta(minutes=czas_minuty)

    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Nagroda:** {nagroda}\nKliknij przycisk poniżej, aby dołączyć!",
        color=discord.Color.gold()
    )
    embed.add_field(name="⏰ Czas trwania", value=f"{czas_minuty} minut", inline=False)
    embed.set_footer(text=f"Zakończenie: {end_time:%Y-%m-%d %H:%M UTC}")

    message = await interaction.channel.send(embed=embed, view=GiveawayView(message_id=0))
    await interaction.response.send_message(f"🎁 Giveaway wystartował! Nagroda: **{nagroda}**", ephemeral=True)

    giveaways = load_giveaways()
    giveaways[str(message.id)] = {
        "channel_id": message.channel.id,
        "end_time": end_time.isoformat(),
        "reward": nagroda,
        "participants": [],
    }
    save_giveaways(giveaways)

    bot.add_view(GiveawayView(message_id=message.id))

    # Odliczanie czasu
    await asyncio.sleep(czas_minuty * 60)
    await end_giveaway(bot, message.id)


async def end_giveaway(bot, message_id: int, manual=False):
    giveaways = load_giveaways()
    g = giveaways.pop(str(message_id), None)
    if not g:
        return False

    save_giveaways(giveaways)

    channel = bot.get_channel(g["channel_id"])
    if not channel:
        return False

    try:
        message = await channel.fetch_message(message_id)
    except Exception:
        return False

    if not g["participants"]:
        await channel.send("😢 Giveaway zakończony — nikt nie wziął udziału.")
        return True

    winner_id = int(random.choice(g["participants"]))
    winner = await bot.fetch_user(winner_id)
    await channel.send(f"🎉 Gratulacje {winner.mention}! Wygrałeś **{g['reward']}** 🥳")

    embed = message.embeds[0]
    embed.title = "✅ GIVEAWAY ZAKOŃCZONY ✅"
    embed.color = discord.Color.green()
    await message.edit(embed=embed, view=None)
    return True


async def reroll_giveaway(bot, message_id: int):
    giveaways = load_giveaways()
    g = giveaways.get(str(message_id))
    if not g or not g["participants"]:
        return None

    winner_id = int(random.choice(g["participants"]))
    winner = await bot.fetch_user(winner_id)
    return winner


# --- GŁÓWNA FUNKCJA SETUP ---

def setup_giveaway(bot: commands.Bot):
    @bot.tree.command(name="giveaway", description="🎁 Utwórz nowy giveaway (tylko admin)")
    @app_commands.describe(czas_minuty="Czas trwania w minutach", nagroda="Nagroda giveaway’a")
    async def giveaway(interaction: discord.Interaction, czas_minuty: int, nagroda: str):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("⛔ Tylko administrator może uruchomić giveaway.", ephemeral=True)
        await start_giveaway(bot, interaction, czas_minuty, nagroda)

    @bot.tree.command(name="endgiveaway", description="🛑 Ręcznie zakończ giveaway (tylko admin)")
    @app_commands.describe(message_id="ID wiadomości giveawayu do zakończenia")
    async def end_giveaway_command(interaction: discord.Interaction, message_id: str):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("⛔ Tylko administrator może zakończyć giveaway.", ephemeral=True)
        result = await end_giveaway(bot, int(message_id), manual=True)
        if result:
            await interaction.response.send_message(f"✅ Giveaway `{message_id}` został zakończony.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Nie znaleziono giveawayu o podanym ID.", ephemeral=True)

    @bot.tree.command(name="rerollgiveaway", description="🔁 Wylosuj nowego zwycięzcę (tylko admin)")
    @app_commands.describe(message_id="ID wiadomości giveawayu do ponownego losowania")
    async def reroll_giveaway_command(interaction: discord.Interaction, message_id: str):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("⛔ Tylko administrator może losować ponownie.", ephemeral=True)
        winner = await reroll_giveaway(bot, int(message_id))
        if winner:
            await interaction.response.send_message(f"🎉 Nowy zwycięzca: {winner.mention}", ephemeral=False)
        else:
            await interaction.response.send_message("⚠️ Nie można było wylosować nowego zwycięzcy.", ephemeral=True)

    # Przywracanie aktywnych giveawayów po restarcie
    @bot.event
    async def on_ready():
        giveaways = load_giveaways()
        for message_id in giveaways.keys():
            bot.add_view(GiveawayView(message_id=int(message_id)))
        print(f"✅ Przywrócono {len(giveaways)} aktywnych giveaway’ów.")

