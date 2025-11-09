import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import json
import os
import time
import re
import random
from datetime import datetime
from discord.ui import View, Button, Modal, TextInput

DATA_FILE = "giveaways.json"
EMBED_COLOR = discord.Color.from_str("#CC0000")  # czerwony pasek
BUTTON_STYLE_JOIN = discord.ButtonStyle.secondary  # szary przycisk

def load_giveaways():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_giveaways(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def parse_time_to_seconds(s: str):
    s = s.strip().lower()
    m = re.match(r"^(\d+)([mhd])$", s)
    if not m:
        return None
    value = int(m.group(1))
    unit = m.group(2)
    if unit == "m":
        return value * 60
    if unit == "h":
        return value * 3600
    if unit == "d":
        return value * 86400
    return None

def human_time_from_seconds(sec: int):
    sec = int(sec)
    d, rem = divmod(sec, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    if d > 0:
        return f"{d}d {h}h {m}m"
    if h > 0:
        return f"{h}h {m}m"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"

class GiveawayView(View):
    def __init__(self, message_id: int):
        super().__init__(timeout=None)
        self.message_id = message_id

    @discord.ui.button(label="🎟️ Weź udział", style=BUTTON_STYLE_JOIN)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_giveaways()
        g = data.get(str(self.message_id))
        if not g or g.get("ended"):
            await interaction.response.send_message("⚠️ Ten giveaway już się zakończył.", ephemeral=True)
            return

        uid = str(interaction.user.id)
        if uid in g["participants"]:
            await interaction.response.send_message("❌ Już bierzesz udział!", ephemeral=True)
            return

        g["participants"].append(uid)
        save_giveaways(data)

        # aktualizuj licznik uczestników
        try:
            bot = interaction.client
            channel = bot.get_channel(g["channel_id"])
            msg = await channel.fetch_message(self.message_id)
            embed = msg.embeds[0]
            desc_lines = embed.description.split("\n")
            for i, line in enumerate(desc_lines):
                if line.startswith("📊"):
                    desc_lines[i] = f"📊 **Uczestnicy:** {len(g['participants'])}"
            embed.description = "\n".join(desc_lines)
            await msg.edit(embed=embed, view=self)
        except Exception:
            pass

        await interaction.response.send_message("✅ Dołączyłeś do giveawayu!", ephemeral=True)

class GiveawayModal(Modal, title="🎉 Utwórz Giveaway"):
    def __init__(self):
        super().__init__(timeout=None)
        self.title_input = TextInput(label="🏷️ Tytuł", placeholder="Np. Discord Nitro!", max_length=100)
        self.description_input = TextInput(label="📝 Opis", style=discord.TextStyle.paragraph, required=True)
        self.duration_input = TextInput(label="⏱️ Czas (np. 10m, 2h, 1d)", max_length=10)
        self.winners_input = TextInput(label="🎉 Liczba zwycięzców", placeholder="1", max_length=2)
        for i in [self.title_input, self.description_input, self.duration_input, self.winners_input]:
            self.add_item(i)

    async def on_submit(self, interaction: discord.Interaction):
        if not (interaction.user.id == interaction.guild.owner_id or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("⛔ Brak uprawnień.", ephemeral=True)
            return

        seconds = parse_time_to_seconds(self.duration_input.value)
        if not seconds:
            await interaction.response.send_message("❌ Zły format czasu.", ephemeral=True)
            return

        try:
            winners_count = int(self.winners_input.value)
            if winners_count < 1:
                raise ValueError()
        except Exception:
            await interaction.response.send_message("❌ Nieprawidłowa liczba zwycięzców.", ephemeral=True)
            return

        end_ts = int(time.time()) + seconds
        embed = discord.Embed(
            title=f"🎉 {self.title_input.value}",
            description=(
                f"{self.description_input.value}\n\n"
                f"🎁 **Liczba wygranych:** {winners_count}\n"
                f"📊 **Uczestnicy:** 0\n"
                f"🕒 **Koniec:** <t:{end_ts}:R>"
            ),
            color=EMBED_COLOR
        )
        embed.set_footer(text="Kliknij przycisk, aby wziąć udział!")

        message = await interaction.channel.send(embed=embed, view=GiveawayView(0))
        data = load_giveaways()
        data[str(message.id)] = {
            "guild_id": interaction.guild.id,
            "channel_id": interaction.channel.id,
            "title": self.title_input.value,
            "description": self.description_input.value,
            "end_ts": end_ts,
            "winners_count": winners_count,
            "participants": [],
            "winners": [],
            "ended": False
        }
        save_giveaways(data)
        await message.edit(view=GiveawayView(message.id))
        asyncio.create_task(_schedule_end(interaction.client, message.id, seconds))
        await interaction.response.send_message("✅ Giveaway utworzony!", ephemeral=True)

async def _end_giveaway_by_id(bot, message_id: int):
    data = load_giveaways()
    g = data.get(str(message_id))
    if not g or g.get("ended"):
        return

    g["ended"] = True
    participants = g["participants"]
    winners_count = g["winners_count"]
    winners = random.sample(participants, min(len(participants), winners_count)) if participants else []
    g["winners"] = winners
    save_giveaways(data)

    channel = bot.get_channel(g["channel_id"])
    if not channel:
        return
    msg = await channel.fetch_message(message_id)
    embed = msg.embeds[0]
    mentions = ", ".join(f"<@{int(w)}>" for w in winners) if winners else "Brak zwycięzców"
    embed.title = "🏆 Giveaway zakończony!"
    embed.description = embed.description.replace("📊 **Uczestnicy:**", f"🏅 **Zwycięzcy:** {mentions}")
    embed.color = discord.Color.dark_gray()
    await msg.edit(embed=embed, view=None)
    if winners:
        await channel.send(f"🎊 Gratulacje {mentions}! Wygrałeś(a) **{g['title']}** 🎉")
    else:
        await channel.send("😢 Giveaway zakończony — nikt nie wziął udziału.")

async def _schedule_end(bot, message_id, delay):
    await asyncio.sleep(delay)
    await _end_giveaway_by_id(bot, message_id)

def setup_giveaway(bot: commands.Bot):
    async def setup_hook():
        bot.tree.add_command(giveaway)
        bot.tree.add_command(giveawayend)
        bot.tree.add_command(giveawayreroll)
        bot.add_view(GiveawayView(0))
        asyncio.create_task(_restore_giveaways(bot))

    async def _restore_giveaways(bot):
        await bot.wait_until_ready()
        data = load_giveaways()
        now = int(time.time())
        for mid, g in data.items():
            if g.get("ended"):
                continue
            mid_int = int(mid)
            bot.add_view(GiveawayView(mid_int))
            remain = g["end_ts"] - now
            if remain > 0:
                asyncio.create_task(_schedule_end(bot, mid_int, remain))
            else:
                asyncio.create_task(_end_giveaway_by_id(bot, mid_int))
        print(f"✅ Przywrócono {len([g for g in data.values() if not g.get('ended')])} giveawayów.")

    @app_commands.command(name="giveaway", description="🎉 Utwórz giveaway")
    async def giveaway(interaction: discord.Interaction):
        await interaction.response.send_modal(GiveawayModal())

    @app_commands.command(name="giveawayend", description="⏹️ Zakończ giveaway")
    async def giveawayend(interaction: discord.Interaction, message_id: str):
        await _end_giveaway_by_id(bot, int(message_id))
        await interaction.response.send_message("✅ Giveaway zakończony!", ephemeral=True)

    @app_commands.command(name="giveawayreroll", description="🔁 Reroll giveaway")
    async def giveawayreroll(interaction: discord.Interaction, message_id: str):
        data = load_giveaways()
        g = data.get(message_id)
        if not g or not g.get("winners"):
            await interaction.response.send_message("❌ Brak zwycięzców do rerollu.", ephemeral=True)
            return
        new_winner = random.choice(g["participants"])
        await interaction.response.send_message(f"🎉 Nowy zwycięzca: <@{new_winner}>", ephemeral=False)

    bot.setup_hook = setup_hook
    print("✅ Giveaway module ready.")

__all__ = ["setup_giveaway", "load_giveaways", "GiveawayView"]
