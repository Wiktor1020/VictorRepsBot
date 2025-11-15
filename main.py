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

# =======================
#  PING & UPTIME COMMANDS
# =======================

import time
import datetime
import discord
from discord import app_commands

# ---- zapis czasu startu bota ----
bot_start_time = time.time()


# ---------- /ping ----------
@bot.tree.command(name="ping", description="Sprawdź opóźnienie bota.")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(
        f"🏓 Pong! Opóźnienie: **{latency}ms**",
        ephemeral=True
    )


# ---------- /uptime ----------
@bot.tree.command(name="uptime", description="Zobacz od jak dawna bot jest włączony.")
async def uptime(interaction: discord.Interaction):

    elapsed = int(time.time() - bot_start_time)

    # Formatowanie czasu
    days = elapsed // 86400
    hours = (elapsed % 86400) // 3600
    minutes = (elapsed % 3600) // 60
    seconds = elapsed % 60

    uptime_text = f"{days}d {hours}h {minutes}m {seconds}s"

    await interaction.response.send_message(
        f"⏳ Bot działa od: **{uptime_text}**",
        ephemeral=True
    )


# ------------------ ŁADOWANIE COGÓW ------------------
async def load_extensions():
    extensions = ["giveaway", "ticketpanel", "stylizacja"]
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

