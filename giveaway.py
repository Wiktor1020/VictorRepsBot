import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import json
import os
from datetime import datetime, timedelta
import random

GIVEAWAYS_FILE = "giveaways.json"


# ----------------- Pomocnicze funkcje -----------------
def load_giveaways():
    if not os.path.exists(GIVEAWAYS_FILE):
        return {}
    with open(GIVEAWAYS_FILE, "r") as f:
        return json.load(f)


def save_giveaways(data):
    with open(GIVEAWAYS_FILE, "w") as f:
        json.dump(data, f, indent=4)


def parse_time(time_str):
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    try:
        return int(time_str[:-1]) * units[time_str[-1]]
    except Exception:
        return None


# ---------------- Giveaway View -----------------
class GiveawayView(discord.ui.View):
    def __init__(self, message_id: int):
        super().__init__(timeout=None)  # persistent view
        self.message_id = message_id

    @discord.ui.button(
        label="🎟️ Dołącz do konkursu",
        style=discord.ButtonStyle.grey,
        custom_id="persistent_giveaway_join"
    )
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_giveaways()
        giveaway = data.get(str(self.message_id))

        if not giveaway:
            await interaction.response.send_message("❌ Ten konkurs już się zakończył.", ephemeral=True)
            return

        participants = giveaway["participants"]

        if interaction.user.id in participants:
            await interaction.response.send_message("⚠️ Już bierzesz udział w tym konkursie!", ephemeral=True)
            return

        participants.append(interaction.user.id)
        giveaway["participants"] = participants
        save_giveaways(data)

        await interaction.response.send_message("✅ Zgłoszono Twój udział w konkursie!", ephemeral=True)


# ---------------- Giveaway Cog -----------------
class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_giveaways.start()

    @commands.Cog.listener()
    async def on_ready(self):
        data = load_giveaways()
        for message_id in data.keys():
            self.bot.add_view(GiveawayView(int(message_id)))
        print("✅ Giveaway module ready.")

    # ---------------- Komenda: /giveaway -----------------
    @app_commands.command(name="giveaway", description="🎉 Rozpocznij nowy konkurs")
    @app_commands.describe(
        czas="Czas trwania (np. 10m, 1h, 1d)",
        nagroda="Nagroda w konkursie",
        liczba_wygranych="Ilość zwycięzców (domyślnie 1)"
    )
    async def giveaway(self, interaction: discord.Interaction, czas: str, nagroda: str, liczba_wygranych: int = 1):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Nie masz uprawnień do tworzenia konkursów.", ephemeral=True)
            return

        seconds = parse_time(czas)
        if not seconds:
            await interaction.response.send_message("❌ Niepoprawny format czasu. Użyj np. `10m`, `1h`, `2d`.", ephemeral=True)
            return

        end_time = datetime.utcnow() + timedelta(seconds=seconds)

        embed = discord.Embed(
            title="🎉 Konkurs!",
            description=f"**Nagroda:** {nagroda}\n"
                        f"**Zakończenie:** <t:{int(end_time.timestamp())}:R>\n"
                        f"**Liczba zwycięzców:** {liczba_wygranych}",
            color=discord.Color.red()
        )
        embed.set_footer(text="Kliknij przycisk, aby dołączyć 🎟️")

        view = GiveawayView(0)
        message = await interaction.channel.send(embed=embed, view=view)
        view.message_id = message.id

        data = load_giveaways()
        data[str(message.id)] = {
            "guild_id": interaction.guild_id,
            "channel_id": interaction.channel_id,
            "message_id": message.id,
            "end_time": end_time.timestamp(),
            "prize": nagroda,
            "winners_count": liczba_wygranych,
            "participants": []
        }
        save_giveaways(data)

        await interaction.response.send_message("✅ Konkurs został utworzony!", ephemeral=True)

    # ---------------- Komenda: /giveawayend -----------------
    @app_commands.command(name="giveawayend", description="⏹️ Zakończ trwający konkurs")
    async def giveawayend(self, interaction: discord.Interaction, message_id: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Brak uprawnień.", ephemeral=True)
            return

        data = load_giveaways()
        giveaway = data.get(str(message_id))
        if not giveaway:
            await interaction.response.send_message("❌ Nie znaleziono konkursu.", ephemeral=True)
            return

        await self.end_giveaway(giveaway)
        del data[str(message_id)]
        save_giveaways(data)

        await interaction.response.send_message("✅ Konkurs zakończony!", ephemeral=True)

    # ---------------- Komenda: /giveawayreroll -----------------
    @app_commands.command(name="giveawayreroll", description="🔁 Wylosuj ponownie zwycięzców konkursu")
    async def giveawayreroll(self, interaction: discord.Interaction, message_id: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Brak uprawnień.", ephemeral=True)
            return

        data = load_giveaways()
        giveaway = data.get(str(message_id))
        if not giveaway:
            await interaction.response.send_message("❌ Nie znaleziono konkursu.", ephemeral=True)
            return

        await self.end_giveaway(giveaway, reroll=True)
        await interaction.response.send_message("✅ Wylosowano nowych zwycięzców!", ephemeral=True)

    # ---------------- Automatyczne sprawdzanie giveawayów -----------------
    @tasks.loop(seconds=30)
    async def check_giveaways(self):
        data = load_giveaways()
        ended = []

        for message_id, giveaway in data.items():
            if datetime.utcnow().timestamp() >= giveaway["end_time"]:
                await self.end_giveaway(giveaway)
                ended.append(message_id)

        for mid in ended:
            del data[mid]

        if ended:
            save_giveaways(data)

    # ---------------- Funkcja kończąca giveaway -----------------
    async def end_giveaway(self, giveaway, reroll=False):
        guild = self.bot.get_guild(giveaway["guild_id"])
        channel = guild.get_channel(giveaway["channel_id"])
        message = await channel.fetch_message(giveaway["message_id"])

        participants = giveaway["participants"]
        prize = giveaway["prize"]
        winners_count = giveaway["winners_count"]

        if not participants:
            await channel.send("❌ Brak uczestników w konkursie.")
            return

        if len(participants) < winners_count:
            winners_count = len(participants)

        winners = random.sample(participants, winners_count)
        winner_mentions = " ".join([f"<@{uid}>" for uid in winners])

        embed = discord.Embed(
            title="🎉 Konkurs zakończony!",
            description=f"**Nagroda:** {prize}\n"
                        f"**Zwycięzcy:** {winner_mentions}",
            color=discord.Color.red()
        )
        await message.edit(embed=embed, view=None)
        await channel.send(f"🎉 Gratulacje dla {winner_mentions}! Wygrali **{prize}**!")


# ---------------- Setup -----------------
async def setup(bot):
    await bot.add_cog(Giveaway(bot))
