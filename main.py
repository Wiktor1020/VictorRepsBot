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


# ------------------ ŁADOWANIE COGÓW ------------------
async def load_extensions():
    extensions = ["giveaway", "ticketpanel", "stylizacja", "utility_ping"]
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

