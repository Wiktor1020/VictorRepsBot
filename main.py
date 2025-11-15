import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
from flask import Flask
from threading import Thread
from datetime import datetime

# ------------------ CONFIG ------------------
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")
INTENTS = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=INTENTS)
start_time = datetime.utcnow()

# ------------------ FLASK KEEP-ALIVE ------------------
app = Flask('')

@app.route('/')
def home():
    return "VictorRepsBot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

keep_alive()

# ------------------ EVENT: on_ready ------------------
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ Zsynchronizowano {len(synced)} komend.")
    except Exception as e:
        print("Błąd synchronizacji:", e)

    await bot.change_presence(
        activity=discord.Game(name="VictorReps | system premium")
    )

    print(f"Bot zalogowany jako {bot.user}")

# ------------------ KOMENDA: /ping ------------------
@bot.tree.command(name="ping", description="Sprawdza ping bota.")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 **Ping:** `{latency}ms`")

# ------------------ KOMENDA: /stylizujkanaly ------------------
@bot.tree.command(name="stylizujkanaly", description="Stylizuje kanały serwera.")
async def stylizujkanaly(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("⛔ Brak uprawnień.", ephemeral=True)
        return

    guild = interaction.guild

    STYLE = {
        "📢・OGŁOSZENIA": ["ogłoszenia", "updates", "info"],
        "💬・CZAT": ["chat", "główny", "general"],
        "❓・POMOC": ["help", "support"],
        "🎉・EVENTY": ["eventy", "giveaway"],
        "🎵・MUZYKA": ["music", "muzyka"],
    }

    renamed = 0

    for channel in guild.channels:
        old = channel.name.lower()

        for new_name, keywords in STYLE.items():
            for k in keywords:
                if k in old:
                    try:
                        await channel.edit(name=new_name)
                        renamed += 1
                    except:
                        pass

    await interaction.response.send_message(f"✨ Zmieniono nazwy **{renamed}** kanałów!")

# ------------------ KOMENDA: /uptime ------------------
@bot.tree.command(name="uptime", description="Pokazuje czas działania bota.")
async def uptime(interaction: discord.Interaction):
    now = datetime.utcnow()
    delta = now - start_time

    h, r = divmod(delta.seconds, 3600)
    m, s = divmod(r, 60)

    await interaction.response.send_message(
        f"⏳ Bot działa od **{delta.days}d {h}h {m}m {s}s**."
    )

# ------------------ ŁADOWANIE COGÓW (giveaway + ticketpanel) ------------------
async def load_extensions():
    extensions = ["giveaway", "ticketpanel"]
    for ext in extensions:
        try:
            await bot.load_extension(ext)
            print(f"Załadowano: {ext}")
        except Exception as e:
            print(f"❌ Błąd ładowania {ext}: {e}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

# ------------------ START BOTA ------------------
asyncio.run(main())
