# giveaway.py
import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import json
import os
import time
from datetime import datetime, timedelta
import random
import re

GIVEAWAYS_FILE = "giveaways.json"
EMBED_COLOR = discord.Color.from_str("#CC0000")
CHECK_INTERVAL = 15  # co ile sekund sprawdzać giveaway'e

# ---------------- helpers ----------------
def load_giveaways():
    if not os.path.exists(GIVEAWAYS_FILE):
        return {}
    try:
        with open(GIVEAWAYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_giveaways(data):
    with open(GIVEAWAYS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def parse_duration(s: str):
    """Parsuje np. 10m, 2h, 1d -> liczba sekund lub None."""
    if not s:
        return None
    s = s.strip().lower()
    m = re.match(r"^(\d+)([mhd])$", s)
    if not m:
        return None
    val = int(m.group(1))
    unit = m.group(2)
    if unit == "m":
        return val * 60
    if unit == "h":
        return val * 3600
    if unit == "d":
        return val * 86400
    return None

def human_time(seconds: int):
    seconds = int(seconds)
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    if d:
        return f"{d}d {h}h {m}m"
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"

# ---------------- persistent view for a single giveaway message ----------------
class GiveawayView(discord.ui.View):
    def __init__(self, message_id: int):
        # timeout=None -> persistent
        super().__init__(timeout=None)
        self.message_id = int(message_id)

        # create a persistent button with custom_id including message id
        custom = f"giveaway_join:{self.message_id}"
        btn = discord.ui.Button(label="🎟️ Weź udział", style=discord.ButtonStyle.secondary, custom_id=custom)
        # bind callback
        async def _callback(interaction: discord.Interaction):
            await self._on_join(interaction)
        btn.callback = _callback
        self.add_item(btn)

    async def _on_join(self, interaction: discord.Interaction):
        data = load_giveaways()
        g = data.get(str(self.message_id))
        if not g or g.get("ended"):
            await interaction.response.send_message("⚠️ Ten giveaway już się zakończył.", ephemeral=True)
            return

        uid = str(interaction.user.id)
        if uid in g["participants"]:
            await interaction.response.send_message("❌ Już bierzesz udział w tym giveawayu!", ephemeral=True)
            return

        g["participants"].append(uid)
        save_giveaways(data)

        # update embed participants count if message exists
        try:
            bot = interaction.client
            channel = bot.get_channel(g["channel_id"])
            if channel:
                msg = await channel.fetch_message(self.message_id)
                if msg and msg.embeds:
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


# ---------------- Cog ----------------
class GiveawayCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_loop.start()

    def cog_unload(self):
        self.check_loop.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        # zarejestruj persistent views dla aktywnych giveawayów
        data = load_giveaways()
        restored = 0
        for mid, g in data.items():
            try:
                if not g.get("ended"):
                    self.bot.add_view(GiveawayView(int(mid)))
                    restored += 1
            except Exception:
                pass
        print(f"✅ Giveaway: przywrócono persistent views dla {restored} konkursów.")

    # ---------------- modal do tworzenia giveaway ----------------
    class _CreateModal(discord.ui.Modal, title="🎉 Utwórz Giveaway"):
        def __init__(self, parent: "GiveawayCog"):
            super().__init__(timeout=None)
            self.parent = parent
            self.title_input = discord.ui.TextInput(label="🏷️ Nazwa/tytuł giveawayu", placeholder="Np. Wygraj Discord Nitro!", max_length=100, required=True)
            self.desc_input = discord.ui.TextInput(label="📝 Opis (zasady)", style=discord.TextStyle.paragraph, placeholder="Opis nagrody i zasad", max_length=600, required=True)
            self.reward_input = discord.ui.TextInput(label="🎁 Nagroda", placeholder="Np. Discord Nitro", max_length=100, required=True)
            self.duration_input = discord.ui.TextInput(label="⏱️ Czas (np. 10m, 2h, 1d)", placeholder="10m = 10 minut", max_length=6, required=True)
            self.winners_input = discord.ui.TextInput(label="🎉 Liczba zwycięzców", placeholder="Np. 1", max_length=2, required=True)

            self.add_item(self.title_input)
            self.add_item(self.desc_input)
            self.add_item(self.reward_input)
            self.add_item(self.duration_input)
            self.add_item(self.winners_input)

        async def on_submit(self, interaction: discord.Interaction):
            # uprawnienia: administrator / owner
            if not (interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id):
                await interaction.response.send_message("⛔ Nie masz uprawnień do tworzenia giveawayów.", ephemeral=True)
                return

            dur_str = self.duration_input.value.strip().lower()
            seconds = parse_duration(dur_str)
            if seconds is None:
                await interaction.response.send_message("❌ Niepoprawny format czasu. Użyj np. `10m`, `2h`, `1d`.", ephemeral=True)
                return

            try:
                winners_count = int(self.winners_input.value.strip())
                if winners_count < 1:
                    raise ValueError()
            except Exception:
                await interaction.response.send_message("❌ Liczba zwycięzców musi być liczbą całkowitą >= 1.", ephemeral=True)
                return

            end_ts = int(time.time()) + seconds
            end_dt = datetime.utcfromtimestamp(end_ts)

            embed = discord.Embed(
                title=f"🎉 {self.title_input.value}",
                description=(
                    f"{self.desc_input.value}\n\n"
                    f"🎁 **Nagroda:** {self.reward_input.value}\n"
                    f"🎉 **Liczba wygranych:** {winners_count}\n"
                    f"📊 **Uczestnicy:** 0\n"
                    f"🕒 **Koniec:** <t:{end_ts}:R>\n"
                ),
                color=EMBED_COLOR
            )
            embed.set_footer(text="Kliknij przycisk poniżej, aby wziąć udział!")

            # wyślij wiadomość + persistent view (z custom_id zawierającym message id)
            view = GiveawayView(0)  # tymczasowo 0, zaktualizujemy po wysłaniu
            msg = await interaction.channel.send(embed=embed, view=view)
            # teraz przypisz prawdziwe id do view i zarejestruj
            view.message_id = msg.id
            # zarejestruj persistent view (ważne, żeby przy restarcie Bot.add_view było wywołane dla tej custom_id)
            self.parent.bot.add_view(GiveawayView(msg.id))

            # zapisz do pliku
            data = load_giveaways()
            data[str(msg.id)] = {
                "guild_id": interaction.guild_id,
                "channel_id": interaction.channel_id,
                "message_id": msg.id,
                "title": self.title_input.value,
                "description": self.desc_input.value,
                "reward": self.reward_input.value,
                "end_time": end_ts,
                "winners_count": winners_count,
                "participants": [],
                "winners": [],
                "ended": False
            }
            save_giveaways(data)

            await interaction.response.send_message("✅ Giveaway został utworzony i zapisany!", ephemeral=True)

    # ---------------- komendy slash ----------------
    @app_commands.command(name="giveaway", description="🎉 Utwórz nowy giveaway (tylko admin).")
    async def giveaway(self, interaction: discord.Interaction):
        modal = GiveawayCog._CreateModal(self)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="giveawayend", description="⏹️ Zakończ giveaway ręcznie (admin).")
    @app_commands.describe(message_id="ID wiadomości giveaway")
    async def giveawayend(self, interaction: discord.Interaction, message_id: str):
        if not (interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id):
            await interaction.response.send_message("⛔ Brak uprawnień.", ephemeral=True)
            return
        data = load_giveaways()
        g = data.get(message_id)
        if not g:
            await interaction.response.send_message("❌ Nie znaleziono giveawayu o takim ID.", ephemeral=True)
            return
        if g.get("ended"):
            await interaction.response.send_message("⚠️ Ten giveaway już został zakończony.", ephemeral=True)
            return
        # zakończ natychmiast
        await self._finish_giveaway(int(message_id))
        await interaction.response.send_message("✅ Giveaway zakończony manualnie.", ephemeral=True)

    @app_commands.command(name="reroll", description="🔁 Wylosuj nowego zwycięzcę (admin).")
    @app_commands.describe(message_id="ID wiadomości giveaway")
    async def reroll(self, interaction: discord.Interaction, message_id: str):
        if not (interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id):
            await interaction.response.send_message("⛔ Brak uprawnień.", ephemeral=True)
            return
        data = load_giveaways()
        g = data.get(message_id)
        if not g:
            await interaction.response.send_message("❌ Nie znaleziono giveawayu o takim ID.", ephemeral=True)
            return
        if not g.get("winners"):
            await interaction.response.send_message("⚠️ Najpierw musi być wylosowany zwycięzca (giveaway zakończony).", ephemeral=True)
            return
        participants = g.get("participants", [])
        previous = g.get("winners", [])
        possible = [p for p in participants if p not in previous]
        if not possible:
            await interaction.response.send_message("⚠️ Brak dostępnych uczestników do ponownego losowania.", ephemeral=True)
            return
        new = random.choice(possible)
        # zastąp pierwszego poprzedniego (albo dopisz)
        replaced = previous[0] if previous else None
        if replaced:
            g["winners"].remove(replaced)
        g["winners"].append(new)
        save_giveaways(data)

        # edytuj wiadomość z wynikiem (jeśli możliwe)
        try:
            guild = self.bot.get_guild(g["guild_id"])
            channel = guild.get_channel(g["channel_id"])
            msg = await channel.fetch_message(g["message_id"])
            mention_list = ", ".join(f"<@{int(x)}>" for x in g["winners"])
            embed = discord.Embed(
                title="🏆 Giveaway - reroll!",
                description=f"🎉 **Zwycięzcy:** {mention_list}\n\nDziękujemy wszystkim za udział!",
                color=discord.Color.dark_gray()
            )
            await msg.edit(embed=embed, view=None)
            await channel.send(f"🔁 Nowy zwycięzca: <@{int(new)}> (zamiast <@{int(replaced)}>).")
        except Exception:
            pass

        await interaction.response.send_message("✅ Reroll zakończony.", ephemeral=True)

    # ---------------- background checker ----------------
    @tasks.loop(seconds=CHECK_INTERVAL)
    async def check_loop(self):
        data = load_giveaways()
        now_ts = int(time.time())
        to_finish = []
        for mid, g in data.items():
            if g.get("ended"):
                continue
            if int(g.get("end_time", 0)) <= now_ts:
                to_finish.append(int(mid))
        for mid in to_finish:
            await self._finish_giveaway(mid)
            # mark finished in file inside _finish_giveaway

    @check_loop.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    # ---------------- finish giveaway helper ----------------
    async def _finish_giveaway(self, message_id: int):
        data = load_giveaways()
        g = data.get(str(message_id))
        if not g or g.get("ended"):
            return
        participants = g.get("participants", [])
        winners_count = int(g.get("winners_count", 1))
        winners = []
        if participants:
            winners = random.sample(participants, min(len(participants), winners_count))
        g["winners"] = winners
        g["ended"] = True
        save_giveaways(data)

        # try edit message and announce
        try:
            guild = self.bot.get_guild(g["guild_id"])
            if not guild:
                return
            channel = guild.get_channel(g["channel_id"])
            if not channel:
                return
            message = await channel.fetch_message(g["message_id"])
            if winners:
                mentions = ", ".join(f"<@{int(w)}>" for w in winners)
                embed = discord.Embed(
                    title="🏆 Giveaway zakończony!",
                    description=f"🎉 **Zwycięzcy:** {mentions}\n\nDziękujemy wszystkim za udział!",
                    color=discord.Color.dark_gray()
                )
                await message.edit(embed=embed, view=None)
                await channel.send(f"🎉 Gratulacje dla: {mentions}! Wygrałeś(a) **{g.get('reward','nagroda')}** 🎊")
            else:
                embed = discord.Embed(
                    title="🏆 Giveaway zakończony!",
                    description="😢 Giveaway zakończony — nikt nie wziął udziału.",
                    color=discord.Color.dark_gray()
                )
                await message.edit(embed=embed, view=None)
                await channel.send("😢 Giveaway zakończony — nikt nie wziął udziału.")
        except Exception:
            pass

# ---------------- setup extension ----------------
async def setup(bot: commands.Bot):
    cog = GiveawayCog(bot)
    await bot.add_cog(cog)
