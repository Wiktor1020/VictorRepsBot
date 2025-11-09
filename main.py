import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio
from flask import Flask
from threading import Thread

# 🔹 Import giveaway logic (osobny plik)
from giveaway import setup_giveaway, load_giveaways, GiveawayView

# --------------------------------------------------------------
# MINI SERWER DLA RENDER / KEEP-ALIVE
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
# INTENTY I INICJALIZACJA BOTA
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 🔹 Inicjalizujemy giveaway system (komendy + restore po restarcie)
setup_giveaway(bot)

# --------------------------------------------------------------
# EVENT: BOT GOTOWY
@bot.event
async def on_ready():
    print(f"✅ Zalogowano jako {bot.user}")

    # Synchronizacja slash-komend
    try:
        synced = await bot.tree.sync()
        print(f"Slash-komendy zsynchronizowane: {len(synced)}")
    except Exception as e:
        print(f"Błąd synchronizacji komend: {e}")

    # 🔹 Rejestracja persistent view dla panelu ticketów
    try:
        from main import TicketPanel  # jeśli TicketPanel jest niżej w pliku
        bot.add_view(TicketPanel())
        print("✅ Persistent TicketPanel view dodany (działa po restarcie).")
    except Exception as e:
        print(f"⚠️ Nie udało się dodać TicketPanel: {e}")

    # 🔹 Przywracanie aktywnych giveaway’ów po restarcie
    try:
        giveaways = load_giveaways()
        for message_id in giveaways.keys():
            bot.add_view(GiveawayView(message_id=int(message_id)))
        print(f"✅ Przywrócono {len(giveaways)} aktywnych giveaway’ów.")
    except Exception as e:
        print(f"⚠️ Błąd przywracania giveaway’ów: {e}")

    print("✅ Bot w pełni gotowy do pracy.")
# --------------------------------------------------------------

# ----------------- NARZĘDZIA UŻYTKOWE ------------------------------
def is_owner(interaction: discord.Interaction) -> bool:
    """Zwraca True, jeśli użytkownik to właściciel serwera lub administrator."""
    if not interaction.guild:
        return False
    return (
        interaction.user.id == interaction.guild.owner_id
        or interaction.user.guild_permissions.administrator
    )

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
    table = str.maketrans(normal, fancy)
    return text.translate(table)

def save_backup(guild):
    data = {str(channel.id): channel.name for channel in guild.channels}
    with open("kanaly_backup.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_backup():
    if not os.path.exists("kanaly_backup.json"):
        return {}
    with open("kanaly_backup.json", "r", encoding="utf-8") as f:
        return json.load(f)
# -------------------------------------------------------------------

# ------------------ KOMENDY STYLIZACJI ------------------------------
@bot.tree.command(name="stylizujkanaly", description="Stylizuje wszystkie kanały serwera.")
async def stylizujkanaly(interaction: discord.Interaction):
    if not is_owner(interaction):
        await interaction.response.send_message("⛔ Nie masz uprawnień do tej komendy.", ephemeral=True)
        return

    await interaction.response.send_message("✨ Stylizowanie kanałów...", ephemeral=True)
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

    await interaction.followup.send("✅ Kanały zostały wystylizowane!", ephemeral=True)

@bot.tree.command(name="stylizujkategorie", description="Stylizuje wszystkie kategorie.")
async def stylizujkategorie(interaction: discord.Interaction):
    if not is_owner(interaction):
        await interaction.response.send_message("⛔ Nie masz uprawnień do tej komendy.", ephemeral=True)
        return

    await interaction.response.send_message("✨ Stylizowanie kategorii...", ephemeral=True)
    save_backup(interaction.guild)

    for category in interaction.guild.categories:
        new_name = f"┏╍╍╍╍╼⪼ {stylize_text(category.name)} ⪻╾╍╍╍╍┓"
        try:
            await category.edit(name=new_name)
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Błąd przy kategorii {category.name}: {e}")

    await interaction.followup.send("✅ Kategorie zostały wystylizowane!", ephemeral=True)

@bot.tree.command(name="przywroc_kanaly", description="Przywraca pierwotne nazwy kanałów z backupu.")
async def przywroc_kanaly(interaction: discord.Interaction):
    if not is_owner(interaction):
        await interaction.response.send_message("⛔ Nie masz uprawnień do tej komendy.", ephemeral=True)
        return

    backup = load_backup()
    if not backup:
        await interaction.response.send_message("⚠️ Brak zapisanych nazw do przywrócenia.", ephemeral=True)
        return

    await interaction.response.send_message("♻️ Przywracanie nazw kanałów...", ephemeral=True)
    for channel in interaction.guild.channels:
        if str(channel.id) in backup:
            try:
                await channel.edit(name=backup[str(channel.id)])
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Błąd przywracania {channel.name}: {e}")

    await interaction.followup.send("✅ Kanały zostały przywrócone!", ephemeral=True)
# -------------------------------------------------------------------

# ------------------ KOMENDY STATUS / PING ---------------------------
@bot.tree.command(name="status", description="Sprawdź, czy bot działa.")
async def status(interaction: discord.Interaction):
    if not is_owner(interaction):
        await interaction.response.send_message("⛔ Brak uprawnień.", ephemeral=True)
        return

    owner = interaction.guild.get_member(interaction.guild.owner_id)
    owner_display = owner.mention if owner else "👑 Właściciel nieznany"

    embed = discord.Embed(
        title="✅ VictorReps działa poprawnie!",
        description="Bot jest aktywny i gotowy do działania.",
        color=discord.Color.green()
    )
    embed.add_field(name="🖥️ Serwer", value=interaction.guild.name, inline=True)
    embed.add_field(name="👑 Właściciel", value=owner_display, inline=True)
    embed.set_footer(text="VictorReps Bot | Status")

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ping", description="Sprawdź ping bota")
async def ping(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Opóźnienie: `{round(bot.latency * 1000)}ms`",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=embed, ephemeral=True)
# -------------------------------------------------------------------

# --- RESZTA KODU (ticketpanel2, powitania itd.) zostaje bez zmian ---
# --------------------------------------------------------------

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

# ------------------ URUCHOMIENIE BOTA -------------------------------
bot.run(os.environ.get("DISCORD_TOKEN") or os.environ.get("TOKEN"))
# -------------------------------------------------------------------
