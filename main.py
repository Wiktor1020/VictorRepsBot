import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
from flask import Flask
from threading import Thread

# 🔹 Import giveaway logic
from giveaway import setup_giveaway, load_giveaways, GiveawayView


# --------------------------------------------------------------
# ➤ MINI SERWER KEEP-ALIVE (Render / UptimeRobot)
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot VictorReps is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()


# --------------------------------------------------------------
# ➤ INTENTY I KONSTRUKTOR BOTA
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


# --------------------------------------------------------------
# ➤ ŁADOWANIE ROZSZERZEŃ (ticketpanel)
@bot.event
async def setup_hook():
    # 🔥 TicketPanel jako extension
    await bot.load_extension("ticketpanel")


# --------------------------------------------------------------
# ➤ SETUP GIVEAWAY SYSTEMU
setup_giveaway(bot)


# --------------------------------------------------------------
# ➤ EVENT ON_READY
@bot.event
async def on_ready():
    print(f"✅ Zalogowano jako {bot.user}")

    # 🔥 Rejestrujemy persistent view (TicketPanel z ticketpanel.py)
    try:
        from ticketpanel import TicketPanel
        bot.add_view(TicketPanel())
        print("✅ Persistent TicketPanel view załadowany.")
    except Exception as e:
        print(f"⚠️ Błąd dodawania TicketPanel: {e}")

    # 🔥 Przywracamy aktywne giveaway'e
    try:
        giveaways = load_giveaways()
        for message_id in giveaways.keys():
            bot.add_view(GiveawayView(message_id=int(message_id)))
        print(f"✅ Przywrócono {len(giveaways)} giveaway'ów.")
    except Exception as e:
        print(f"⚠️ Błąd przywracania giveaway'ów: {e}")

    # 🔥 Synchronizacja slash-komend
    try:
        synced = await bot.tree.sync()
        print(f"Slash-komendy zsynchronizowane: {len(synced)}")
    except Exception as e:
        print(f"Błąd synchronizacji komend: {e}")

    print("🚀 Bot w pełni gotowy!")


# --------------------------------------------------------------
# ➤ UPRAWNIENIA: tylko owner/admin
def is_owner(interaction: discord.Interaction) -> bool:
    if not interaction.guild:
        return False
    return (
        interaction.user.id == interaction.guild.owner_id
        or interaction.user.guild_permissions.administrator
    )


# --------------------------------------------------------------
# ➤ STYLIZACJA KANAŁÓW
channel_emojis = {
    "czat": "💬",
    "pytania": "❓",
    "findsy": "💯",
    "wasze": "💯",
    "zaproszenia": "👋",
    "best": "🥇",
    "zasady": "📝",
    "qc": "📷",
    "yupoo": "👥",
    "głos": "🔊"
}

def stylize_text(text):
    normal = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    fancy = "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return text.translate(str.maketrans(normal, fancy))

def save_backup(guild):
    data = {str(channel.id): channel.name for channel in guild.channels}
    with open("kanaly_backup.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_backup():
    if not os.path.exists("kanaly_backup.json"):
        return {}
    with open("kanaly_backup.json", "r", encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------
# ➤ KOMENDY /stylizujkanaly /stylizujkategorie /przywroc_kanaly

@bot.tree.command(name="stylizujkanaly", description="Stylizuje wszystkie kanały serwera.")
async def stylizujkanaly(interaction: discord.Interaction):
    if not is_owner(interaction):
        await interaction.response.send_message("⛔ Nie masz uprawnień.", ephemeral=True)
        return

    await interaction.response.send_message("✨ Stylizowanie...", ephemeral=True)
    save_backup(interaction.guild)

    for channel in interaction.guild.channels:
        if isinstance(channel, discord.CategoryChannel):
            continue

        name_lower = channel.name.lower()
        emoji = next((val for key, val in channel_emojis.items() if key in name_lower), "💠")
        new_name = f"「{emoji}」{stylize_text(channel.name)}"

        try:
            await channel.edit(name=new_name)
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Błąd przy {channel.name}: {e}")

    await interaction.followup.send("✅ Kanały wystylizowane!", ephemeral=True)


@bot.tree.command(name="stylizujkategorie", description="Stylizuje wszystkie kategorie.")
async def stylizujkategorie(interaction: discord.Interaction):
    if not is_owner(interaction):
        await interaction.response.send_message("⛔ Brak uprawnień.", ephemeral=True)
        return

    await interaction.response.send_message("✨ Stylizowanie kategorii...", ephemeral=True)
    save_backup(interaction.guild)

    for category in interaction.guild.categories:
        new_name = f"┏╍╍╍╍╼⪼ {stylize_text(category.name)} ⪻╾╍╍╍╍┓"
        try:
            await category.edit(name=new_name)
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Błąd kategorii {category.name}: {e}")

    await interaction.followup.send("✅ Kategorie wystylizowane!", ephemeral=True)


@bot.tree.command(name="przywroc_kanaly", description="Przywraca pierwotne nazwy kanałów.")
async def przywroc_kanaly(interaction: discord.Interaction):
    if not is_owner(interaction):
        await interaction.response.send_message("⛔ Brak uprawnień.", ephemeral=True)
        return

    backup = load_backup()
    if not backup:
        await interaction.response.send_message("⚠️ Brak backupu.", ephemeral=True)
        return

    await interaction.response.send_message("♻️ Przywracanie...", ephemeral=True)

    for channel in interaction.guild.channels:
        if str(channel.id) in backup:
            try:
                await channel.edit(name=backup[str(channel.id)])
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Błąd przywracania {channel.name}: {e}")

    await interaction.followup.send("✅ Przywrócono!", ephemeral=True)


# --------------------------------------------------------------
# ➤ STATUS / PING

@bot.tree.command(name="status", description="Sprawdź, czy bot działa.")
async def status(interaction: discord.Interaction):
    if not is_owner(interaction):
        await interaction.response.send_message("⛔ Brak uprawnień.", ephemeral=True)
        return

    owner = interaction.guild.get_member(interaction.guild.owner_id)
    owner_display = owner.mention if owner else "Nieznany"

    embed = discord.Embed(
        title="✅ VictorReps działa!",
        description="Bot jest aktywny.",
        color=discord.Color.green()
    )
    embed.add_field(name="Serwer", value=interaction.guild.name)
    embed.add_field(name="Owner", value=owner_display)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="ping", description="Sprawdza ping bota.")
async def ping(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Ping: `{round(bot.latency * 1000)}ms`",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=embed, ephemeral=True)


# --------------------------------------------------------------
# ➤ KEEP ALIVE + START
keep_alive()
bot.run(os.environ.get("DISCORD_TOKEN") or os.environ.get("TOKEN"))

