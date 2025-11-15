import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
from flask import Flask
from threading import Thread
from datetime import datetime

from giveaway import GiveawayView  # <<< NAJWAŻNIEJSZE
import json

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


# ------------------ PRZYWRACANIE PERSISTENT VIEW ------------------
def restore_giveaway_views():
    if not os.path.exists("giveaways.json"):
        return

    try:
        with open("giveaways.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        return

    restored = 0
    for msg_id, g in data.items():
        if g.get("ended"):
            continue

        bot.add_view(GiveawayView(int(msg_id)))
        restored += 1

    print(f"🔁 Przywrócono {restored} persistent view dla giveawayów.")


# ------------------ EVENT: on_ready ------------------
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ Zsynchronizowano {len(synced)} komend.")
    except Exception as e:
        print("Błąd synchronizacji:", e)

    bot.loop.create_task(asyncio.to_thread(restore_giveaway_views))

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
