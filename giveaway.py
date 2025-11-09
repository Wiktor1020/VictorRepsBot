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

# ---------------- CONFIG ----------------
DATA_FILE = "giveaways.json"
EMBED_COLOR = discord.Color.from_str("#CC0000")  # czerwony taki jak w ticketach
BUTTON_STYLE_JOIN = discord.ButtonStyle.secondary  # szary przycisk
# ----------------------------------------

# ---------------- HELPERS ----------------
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
    """
    Parsuje '10m', '2h', '3d' -> sekundy.
    Obsługuje m (minuty), h (godziny), d (dni).
    """
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
    # Prosty format czasu jak w Twoim wcześniejszym kodzie
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

# -----------------------------------------

# ---------- VIEW (przycisk dołączenia) ----------
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
            await interaction.response.send_message("❌ Już bierzesz udział w tym giveawayu!", ephemeral=True)
            return

        g["participants"].append(uid)
        save_giveaways(data)

        # Aktualizuj embed uczestników ( jeśli wiadomość nadal istnieje )
        try:
            bot = interaction.client
            channel = bot.get_channel(g["channel_id"])
            msg = await channel.fetch_message(self.message_id)
            embed = msg.embeds[0]
            # zaktualizuj linię z uczestnikami: znajdź "📊 **Uczestnicy:**"
            desc_lines = embed.description.split("\n")
            for i, line in enumerate(desc_lines):
                if line.startswith("📊"):
                    desc_lines[i] = f"📊 **Uczestnicy:** {len(g['participants'])}"
            embed.description = "\n".join(desc_lines)
            await msg.edit(embed=embed, view=self)
        except Exception:
            pass

        await interaction.response.send_message("✅ Dołączyłeś do giveawayu!", ephemeral=True)

# ------------------------------------------------

# --------- MODAL do tworzenia giveaway (formularz) ----------
class GiveawayModal(Modal, title="🎉 Utwórz Giveaway"):
    def __init__(self):
        super().__init__(timeout=None)
        self.title_input = TextInput(label="🏷️ Nagłówek giveawayu (tytuł)", placeholder="Np. Wygraj Discord Nitro!", max_length=100, required=True)
        self.description_input = TextInput(label="📝 Opis (wiadomość pod nagłówkiem)", style=discord.TextStyle.paragraph, placeholder="Np. Zasady i informacje", max_length=600, required=True)
        self.duration_input = TextInput(label="⏱️ Czas (np. 10m, 2h, 1d)", placeholder="10m = 10 minut, 2h = 2 godziny, 1d = 1 dzień", max_length=10, required=True)
        self.winners_input = TextInput(label="🎉 Liczba zwycięzców", placeholder="Np. 1", max_length=2, required=True)

        self.add_item(self.title_input)
        self.add_item(self.description_input)
        self.add_item(self.duration_input)
        self.add_item(self.winners_input)

    async def on_submit(self, interaction: discord.Interaction):
        # uprawnienia: tylko owner lub admin
        if not (interaction.user.id == interaction.guild.owner_id or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("⛔ Tylko właściciel serwera lub administrator może tworzyć giveaway.", ephemeral=True)
            return

        time_str = self.duration_input.value.strip().lower()
        seconds = parse_time_to_seconds(time_str)
        if seconds is None:
            await interaction.response.send_message("❌ Niepoprawny format czasu — użyj np. `10m`, `2h`, `1d`.", ephemeral=True)
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
                f"{self.description_input.value}\n\n"
                f"🎁 **Liczba wygranych:** {winners_count}\n"
                f"📊 **Uczestnicy:** 0\n"
                f"🕒 **Koniec:** <t:{end_ts}:R>"
            ),
            color=EMBED_COLOR
        )
        embed.set_footer(text="Kliknij przycisk poniżej, aby wziąć udział!")

        # wyślij wiadomość
        message = await interaction.channel.send(embed=embed, view=GiveawayView(message_id=0))
        # zapisz do pliku
        data = load_giveaways()
        data[str(message.id)] = {
            "guild_id": interaction.guild.id,
            "channel_id": interaction.channel.id,
            "title": self.title_input.value,
            "description": self.description_input.value,
            "end_ts": end_ts,
            "winners_count": winners_count,
            "participants": [],      # lista user id (string)
            "winners": [],           # zapis zwycięzców po zakończeniu
            "ended": False
        }
        save_giveaways(data)

        # zaktualizuj view z prawidłowym message_id
        view = GiveawayView(message_id=message.id)
        await message.edit(view=view)

        # uruchom zadanie które zakończy giveaway po czasie
        asyncio.create_task(_schedule_end(message.id, seconds))

        await interaction.response.send_message("✅ Giveaway został utworzony i zapisany!", ephemeral=True)

# ---------------------------------------------------------------

# ---------- funkcje kończenia / reroll / end scheduling ----------
async def _end_giveaway_by_id(bot: commands.Bot, message_id: int, animated: bool = True):
    data = load_giveaways()
    g = data.get(str(message_id))
    if not g or g.get("ended"):
        return False

    # oznacz jako zakończony
    g["ended"] = True

    participants = g.get("participants", [])
    winners_count = g.get("winners_count", 1)
    if not isinstance(winners_count, int):
        winners_count = int(winners_count)

    winners = []
    if participants:
        winners = random.sample(participants, min(len(participants), winners_count))
        # zapewnij że są inty i unikalne:
        winners = list(dict.fromkeys(winners))
    g["winners"] = winners
    save_giveaways(data)

    # postaraj się edytować wiadomość i oznaczyć zwycięzców
    try:
        bot_obj = bot
        channel = bot_obj.get_channel(g["channel_id"])
        if channel is None:
            return True
        message = await channel.fetch_message(message_id)
        # przygotuj listę mentionów
        if winners:
            mentions = ", ".join(f"<@{int(w)}>" for w in winners)
            result_text = f"🎉 **Zwycięzcy:** {mentions}\n\nDziękujemy wszystkim za udział!"
        else:
            result_text = "😢 Giveaway zakończony — nikt nie wziął udziału."

        # edytuj embed: zmień tytuł + podmień uczestników na zwycięzców
        embed = message.embeds[0] if message.embeds else discord.Embed(title="✅ GIVEAWAY ZAKOŃCZONY")
        embed.title = "🏆 Giveaway zakończony!"
        # spróbuj zamienić linię z "📊 **Uczestnicy:**" na zwycięzców
        if embed.description:
            lines = embed.description.split("\n")
            new_lines = []
            for line in lines:
                if line.startswith("📊"):
                    if winners:
                        new_lines.append(f"🏅 **Zwycięzcy:** {mentions}")
                    else:
                        new_lines.append("🏅 **Zwycięzcy:** Brak")
                else:
                    new_lines.append(line)
            embed.description = "\n".join(new_lines)
        else:
            embed.description = result_text

        embed.color = discord.Color.dark_gray()
        # zdezaktywuj przyciski -> ustaw view None (buttony przestaną działać)
        await message.edit(embed=embed, view=None)

        # wyślij wiadomość z gratulacjami i oznacz zwycięzców
        if winners:
            await channel.send(f"🎊 Gratulacje {', '.join(f'<@{int(w)}>' for w in winners)}! Wygrałeś(a) **{g.get('title', '') or g.get('reward','nagroda')}** 🎉")
        else:
            await channel.send("😢 Giveaway zakończony — nikt nie wziął udziału.")
    except Exception:
        # nawet jeśli edycja/wywołanie się nie uda, i tak usuń z listy aktywnych
        pass

    return True

async def _schedule_end(message_id: int, seconds_from_now: int):
    # Prostota: czekaj, potem wywołaj _end_giveaway_by_id używając globalnego bota
    await asyncio.sleep(seconds_from_now)
    # znaleźć globalnego bota z discord.client (discord.py zapewnia clienty w tej przestrzeni)
    # importuj dynamicznie, żeby nie robić cyklicznych importów
    try:
        from discord.ext import commands as _commands_mod
        # zakładamy że skrypt używa "bot" globalnie (gdy jest importowany przez main, main ma bot)
        # Najpewniejsze: znajdź bieżący client przez discord.utils (interaction.client) — jednak tutaj
        # po prostu pobierz pierwszą aktywną instancję z discord clients:
        for client in discord.Client.__subclasses__():
            pass
    except Exception:
        pass
    # W praktyce wywołaj funkcję _end_giveaway_by_id używając globalnego "BOT" ustawionego poniżej
    global _GLOBAL_BOT_FOR_SCHEDULER
    if _GLOBAL_BOT_FOR_SCHEDULER is None:
        # jeśli bot jeszcze nie ustawiony, spróbuj ponowić później
        await asyncio.sleep(5)
    if _GLOBAL_BOT_FOR_SCHEDULER:
        await _end_giveaway_by_id(_GLOBAL_BOT_FOR_SCHEDULER, message_id, animated=True)

# -----------------------------------------

# ---------- KOMENDY I SETUP (eksportuj setup_giveaway) ----------
_GLOBAL_BOT_FOR_SCHEDULER = None

def setup_giveaway(bot: commands.Bot):
    """
    Rejestruje komendy i uruchamia przywracanie giveawayów w tle.
    Wywołaj setup_giveaway(bot) z main.py.
    """
    global _GLOBAL_BOT_FOR_SCHEDULER
    _GLOBAL_BOT_FOR_SCHEDULER = bot

    # Przywróć widoki i zaplanuj kończenia po starcie bota
    async def _restore_and_schedule():
        await bot.wait_until_ready()
        data = load_giveaways()
        now_ts = int(time.time())
        for mid, g in list(data.items()):
            try:
                mid_int = int(mid)
            except Exception:
                continue
            # jeśli zakończony już to nie przywracamy widoku
            if g.get("ended"):
                continue
            # dodaj view (przycisk) żeby interakcje działały po restarcie
            try:
                bot.add_view(GiveawayView(message_id=mid_int))
            except Exception:
                pass
            # oblicz ile sekund do końca
            end_ts = int(g.get("end_ts", 0))
            remaining = end_ts - now_ts
            if remaining <= 0:
                # zakończ natychmiast (asynchronicznie)
                asyncio.create_task(_end_giveaway_by_id(bot, mid_int, animated=False))
            else:
                # zaplanuj zakończenie
                asyncio.create_task(_schedule_end(mid_int, remaining))
        print(f"✅ Przywrócono i zaplanowano {len([g for g in data.values() if not g.get('ended')])} aktywnych giveaway’ów.")

    # Rejestracja komend
    @bot.tree.command(name="giveaway", description="🎉 Utwórz nowy giveaway (tylko właściciel lub admin).")
    async def giveaway(interaction: discord.Interaction):
        # otwórz modal
        modal = GiveawayModal()
        await interaction.response.send_modal(modal)

    @bot.tree.command(name="giveawayend", description="⏹️ Ręcznie zakończ giveaway (tylko owner/admin).")
    @app_commands.describe(message_id="ID wiadomości giveaway (numer wiadomości Discord)")
    async def giveawayend(interaction: discord.Interaction, message_id: str):
        # sprawdź uprawnienia
        if not (interaction.user.id == interaction.guild.owner_id or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("⛔ Brak uprawnień.", ephemeral=True)
            return
        try:
            mid = int(message_id)
        except:
            await interaction.response.send_message("❌ Nieprawidłowy message_id.", ephemeral=True)
            return
        res = await _end_giveaway_by_id(bot, mid, animated=True)
        if res:
            await interaction.response.send_message(f"✅ Giveaway `{message_id}` został zakończony.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Nie znaleziono lub nie można zakończyć giveawayu.", ephemeral=True)

    @bot.tree.command(name="giveawayreroll", description="🔁 Wylosuj nowego zwycięzcę (tylko owner/admin).")
    @app_commands.describe(message_id="ID wiadomości giveaway (numer wiadomości Discord)")
    async def giveawayreroll(interaction: discord.Interaction, message_id: str):
        if not (interaction.user.id == interaction.guild.owner_id or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("⛔ Brak uprawnień.", ephemeral=True)
            return
        try:
            mid = int(message_id)
        except:
            await interaction.response.send_message("❌ Nieprawidłowy message_id.", ephemeral=True)
            return
        data = load_giveaways()
        g = data.get(str(mid))
        if not g:
            await interaction.response.send_message("❌ Nie znaleziono giveawayu.", ephemeral=True)
            return
        participants = g.get("participants", [])
        if not participants:
            await interaction.response.send_message("⚠️ Brak uczestników.", ephemeral=True)
            return
        winners_count = int(g.get("winners_count", 1))
        # losuj nowego zwycięzcę
        new_winner = random.choice(participants)
        # zapis do winners (dorzucamy)
        g_winners = g.get("winners", [])
        if str(new_winner) not in g_winners:
            g_winners.append(str(new_winner))
        g["winners"] = g_winners
        save_giveaways(data)
        winner_user = await bot.fetch_user(int(new_winner))
        await interaction.response.send_message(f"🎉 Nowy zwycięzca: {winner_user.mention}", ephemeral=False)

    # Uruchom restore task
    bot.loop.create_task(_restore_and_schedule())

    print("✅ Giveaway module loaded (komendy: /giveaway, /giveawayend, /giveawayreroll).")

# Exporty (przydatne jeśli main.py chce dodać widoki ręcznie)
__all__ = ["setup_giveaway", "load_giveaways", "GiveawayView"]

