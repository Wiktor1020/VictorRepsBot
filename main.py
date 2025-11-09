import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "✅ Bot VictorReps is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)
def keep_alive():
 t = Thread(target=run)
 t.start()
# -------------------------------------------------------------------

# ---------------- INTENTY I BOT -----------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
# -------------------------------------------------------------------

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

# ------------------ EVENT READY (sync komend) ----------------------
@bot.event
async def on_ready():
    print(f"✅ Zalogowano jako {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Slash-komendy zsynchronizowane: {len(synced)}")
    except Exception as e:
        print(f"Błąd synchronizacji komend: {e}")
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
    await interaction.response.defer(ephemeral=True)  # "thinking..." — daje ci więcej czasu

    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Opóźnienie: `{round(bot.latency * 1000)}ms`",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=embed, ephemeral=True)

# -------------------------------------------------------------------
# --- KOMENDA /ticketpanel2 (FINALNA, WSZYSTKO W JEDNEJ KATEGORII) ---
from discord.ui import View, Button, Modal, TextInput
import asyncio

active_tickets = {}  # {guild_id: {user_id: [kategorie]}}

class TicketModal(Modal, title="🎫 Utwórz ticket"):
    def __init__(self, category_name: str):
        super().__init__(timeout=None)
        self.category_name = category_name
        self.problem = TextInput(
            label="Opisz co od nas potrzebujesz:",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500
        )
        self.add_item(self.problem)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user

        if guild.id not in active_tickets:
            active_tickets[guild.id] = {}
        if member.id not in active_tickets[guild.id]:
            active_tickets[guild.id][member.id] = []

        # Sprawdź, czy użytkownik ma już ticket w tej kategorii
        if self.category_name in active_tickets[guild.id][member.id]:
            await interaction.response.send_message(
                "⚠️ Masz już otwarty ticket w tej kategorii! Zamknij go, zanim utworzysz nowy.",
                ephemeral=True
            )
            return

        # 🔒 Ustawienia uprawnień kategorii i kanału
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }

        # 🔧 Moderatorzy i administratorzy też widzą tickety
        for role in guild.roles:
            if role.permissions.manage_messages or role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        # ✅ Utwórz / pobierz JEDNĄ kategorię "🎟️・TICKETY"
        main_category_name = "🎟️・TICKETY"
        category = discord.utils.get(guild.categories, name=main_category_name)
        if not category:
            category = await guild.create_category(name=main_category_name, overwrites=overwrites)
            await category.edit(position=0)  # ustaw na samej górze
        else:
            # Uaktualnij jej uprawnienia (żeby była zawsze prywatna)
            await category.edit(overwrites=overwrites, position=0)

        # 🔴 Utwórz prywatny kanał ticketa w tej kategorii
        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{member.name}-{self.category_name.lower()}",
            category=category,
            topic=f"Ticket użytkownika {member} ({self.category_name})",
            overwrites=overwrites
        )

        active_tickets[guild.id][member.id].append(self.category_name)

        embed = discord.Embed(
            title=f"🎫 Ticket - {self.category_name}",
            description=f"**Użytkownik:** {member.mention}\n\n📩 **Zgłoszenie:**\n{self.problem.value}",
            color=discord.Color.from_str("#CC0000")
        )
        embed.set_footer(text="VictorReps | System Ticketów")

        close_button = Button(label="Zamknij ticket", style=discord.ButtonStyle.danger, emoji="🔒")

        async def close_callback(inter_close: discord.Interaction):
            if inter_close.user == member or inter_close.user.guild_permissions.manage_channels:
                await inter_close.response.send_message("🔒 Ticket zostanie zamknięty za 5 sekund...", ephemeral=True)
                await asyncio.sleep(5)
                await ticket_channel.delete()
                if guild.id in active_tickets and member.id in active_tickets[guild.id]:
                    if self.category_name in active_tickets[guild.id][member.id]:
                        active_tickets[guild.id][member.id].remove(self.category_name)
            else:
                await inter_close.response.send_message("⛔ Nie możesz zamknąć tego ticketa.", ephemeral=True)

        close_button.callback = close_callback
        view = View()
        view.add_item(close_button)

        await ticket_channel.send(content=f"{member.mention}", embed=embed, view=view)
        await interaction.response.send_message(f"✅ Ticket został utworzony: {ticket_channel.mention}", ephemeral=True)


class TicketButton(Button):
    def __init__(self, label: str, emoji: str):
        super().__init__(label=label, emoji=emoji, style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        modal = TicketModal(self.label)
        await interaction.response.send_modal(modal)


class TicketPanel(View):
    def __init__(self):
        super().__init__(timeout=None)
        categories = [
            ("Paczka", "📦"),
            ("Pomoc", "🧰"),
            ("Współpraca", "🤝"),
            ("Inne", "💬")
        ]
        for name, emoji in categories:
            self.add_item(TicketButton(label=name, emoji=emoji))


@bot.tree.command(name="ticketpanel2", description="Wyświetla nowy panel ticketów (dla właściciela lub admina).")
async def ticketpanel2(interaction: discord.Interaction):
    if not (
        interaction.user.id == interaction.guild.owner_id
        or interaction.user.guild_permissions.administrator
    ):
        await interaction.response.send_message(
            "⛔ Tylko właściciel serwera lub administrator może użyć tej komendy.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎫 Panel Ticketów",
        description=(
            "Kliknij odpowiedni przycisk poniżej, a pomożemy Ci tak szybko, jak to możliwe.\n\n"
            "Wybierz kategorię swojego problemu:"
        ),
        color=discord.Color.from_str("#CC0000")
    )
    embed.set_footer(text="VictorReps | System Ticketów")

    view = TicketPanel()
    await interaction.response.send_message(embed=embed, view=view)

# --- GIVEAWAY SYSTEM (z zapisem do pliku i rerollem po zakończeniu) ---
import asyncio, random, datetime, re, json, os

DATA_FILE = "giveaways.json"

# --- FUNKCJE POMOCNICZE ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def is_owner(interaction: discord.Interaction):
    return (
        interaction.user == interaction.guild.owner
        or interaction.user.guild_permissions.administrator
    )

active_giveaways = {}
giveaway_data = load_data()

# --- MODAL TWORZENIA GIVEAWAYU ---
class GiveawayModal(discord.ui.Modal, title="🎉 Utwórz Giveaway"):
    giveaway_title = discord.ui.TextInput(label="🏷️ Nagłówek giveawayu", placeholder="Np. Wygraj Discord Nitro!", max_length=100)
    giveaway_description = discord.ui.TextInput(label="📝 Opis giveawayu", style=discord.TextStyle.paragraph, placeholder="Opisz zasady lub nagrodę", max_length=500)
    giveaway_duration = discord.ui.TextInput(label="⏱️ Czas trwania (np. 10m, 2h, 1d)", placeholder="Np. 10m = 10 minut", max_length=10)
    giveaway_winners = discord.ui.TextInput(label="🎉 Liczba zwycięzców", placeholder="Np. 1", max_length=2)

    async def on_submit(self, interaction: discord.Interaction):
        # --- Parsowanie czasu ---
        time_str = self.giveaway_duration.value.lower()
        if time_str.endswith("m"):
            duration = int(time_str[:-1]) * 60
        elif time_str.endswith("h"):
            duration = int(time_str[:-1]) * 3600
        elif time_str.endswith("d"):
            duration = int(time_str[:-1]) * 86400
        else:
            await interaction.response.send_message("❌ Niepoprawny format czasu! Użyj np. `10m`, `2h`, `1d`.", ephemeral=True)
            return

        try:
            winners_count = int(self.giveaway_winners.value)
        except ValueError:
            await interaction.response.send_message("❌ Liczba zwycięzców musi być liczbą całkowitą.", ephemeral=True)
            return

        end_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=duration)

        embed = discord.Embed(
            title=f"🎉 {self.giveaway_title.value}",
            description=(
                f"{self.giveaway_description.value}\n\n"
                f"🕒 **Koniec:** <t:{int(end_time.timestamp())}:R>\n"
                f"⏳ **Pozostało:** {self.format_time(duration)}\n"
                f"👥 **Liczba wygranych:** {winners_count}\n"
                f"📊 **Uczestnicy:** 0"
            ),
            color=discord.Color.from_str("#CC0000")
        )
        embed.set_footer(text="Kliknij przycisk poniżej, aby wziąć udział!")

        view = GiveawayView(end_time, winners_count)
        message = await interaction.channel.send(embed=embed, view=view)
        view.message = message
        active_giveaways[message.id] = view

        giveaway_data[str(message.id)] = {
            "guild_id": interaction.guild.id,
            "channel_id": interaction.channel.id,
            "title": self.giveaway_title.value,
            "description": self.giveaway_description.value,
            "end_time": end_time.timestamp(),
            "winners_count": winners_count,
            "participants": [],
            "ended": False,
            "winners": []
        }
        save_data(giveaway_data)

        await interaction.response.send_message("✅ Giveaway został utworzony!", ephemeral=True)
        asyncio.create_task(view.update_countdown())

    @staticmethod
    def format_time(seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        if d > 0:
            return f"{d}d {h}h {m}m"
        elif h > 0:
            return f"{h}h {m}m"
        elif m > 0:
            return f"{m}m {s}s"
        else:
            return f"{s}s"

# --- VIEW DLA GIVEAWAYU ---
class GiveawayView(discord.ui.View):
    def __init__(self, end_time, winners_count):
        super().__init__(timeout=None)
        self.participants = set()
        self.end_time = end_time
        self.winners_count = winners_count
        self.message = None
        self.running = True

    @discord.ui.button(label="🎟️ Weź udział", style=discord.ButtonStyle.secondary)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        if user.id in self.participants:
            await interaction.response.send_message("❌ Już bierzesz udział w tym giveawayu!", ephemeral=True)
            return

        self.participants.add(user.id)
        await self.update_embed()

        # zapisanie uczestnika do pliku
        data = giveaway_data.get(str(self.message.id))
        if data:
            if user.id not in data["participants"]:
                data["participants"].append(user.id)
                save_data(giveaway_data)

        await interaction.response.send_message("✅ Dołączyłeś do giveawayu!", ephemeral=True)

    async def update_embed(self):
        if not self.message or not self.message.embeds:
            return
        embed = self.message.embeds[0]
        lines = embed.description.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("📊"):
                lines[i] = f"📊 **Uczestnicy:** {len(self.participants)}"
        embed.description = "\n".join(lines)
        await self.message.edit(embed=embed, view=self)

    async def update_countdown(self):
        while self.running:
            now = datetime.datetime.utcnow()
            remaining = (self.end_time - now).total_seconds()
            if remaining <= 0:
                await self.end_giveaway(animated=True)
                return

            embed = self.message.embeds[0]
            lines = embed.description.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("⏳"):
                    lines[i] = f"⏳ **Pozostało:** {GiveawayModal.format_time(int(remaining))}"
            embed.description = "\n".join(lines)
            await self.message.edit(embed=embed, view=self)
            await asyncio.sleep(60)

    async def end_giveaway(self, animated=False):
        if not self.running:
            return
        self.running = False

        if not self.participants:
            await self.message.reply("😢 Giveaway zakończony — nikt nie wziął udziału.")
            giveaway_data[str(self.message.id)]["ended"] = True
            save_data(giveaway_data)
            return

        if animated:
            loading_embed = discord.Embed(
                title="🎲 Losowanie zwycięzców...",
                description="Bot wybiera zwycięzców spośród uczestników...",
                color=discord.Color.from_str("#CC0000")
            )
            await self.message.edit(embed=loading_embed, view=None)
            await asyncio.sleep(3)

        winners = random.sample(list(self.participants), min(self.winners_count, len(self.participants)))
        winner_mentions = ", ".join(f"<@{w}>" for w in winners)

        embed = discord.Embed(
            title="🏆 Giveaway zakończony!",
            description=f"🎉 **Zwycięzcy:** {winner_mentions}\n\nDziękujemy wszystkim za udział!",
            color=discord.Color.dark_gray()
        )
        embed.set_footer(text="Koniec giveawayu 🎁")

        for child in self.children:
            child.disabled = True

        await self.message.edit(embed=embed, view=self)
        await self.message.reply(f"🎉 Gratulacje dla: {winner_mentions}! 🥳")

        # zapisanie do pliku
        data = giveaway_data.get(str(self.message.id))
        if data:
            data["ended"] = True
            data["winners"] = winners
            save_data(giveaway_data)

        active_giveaways.pop(self.message.id, None)

# --- KOMENDA /GIVEAWAY ---
@bot.tree.command(name="giveaway", description="Utwórz nowy giveaway (tylko właściciel lub admin).")
async def giveaway(interaction: discord.Interaction):
    if not is_owner(interaction):
        await interaction.response.send_message("⛔ Tylko właściciel serwera lub administrator może użyć tej komendy.", ephemeral=True)
        return
    await interaction.response.send_modal(GiveawayModal())

# --- KOMENDA /ENDGIVEAWAY ---
@bot.tree.command(name="endgiveaway", description="Ręcznie zakończ giveaway (tylko właściciel lub admin).")
async def end_giveaway(interaction: discord.Interaction, message_id: str):
    if not is_owner(interaction):
        await interaction.response.send_message("⛔ Tylko właściciel serwera lub administrator może użyć tej komendy.", ephemeral=True)
        return

    if message_id in giveaway_data:
        data = giveaway_data[message_id]
        if data["ended"]:
            await interaction.response.send_message("⚠️ Ten giveaway już został zakończony.", ephemeral=True)
            return

    view = active_giveaways.get(int(message_id))
    if view:
        await view.end_giveaway(animated=True)
        await interaction.response.send_message(f"✅ Giveaway `{message_id}` zakończony ręcznie.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Giveaway nie jest aktywny lub ID jest błędne.", ephemeral=True)

# --- KOMENDA /GIVEAWAYREROLL ---
@bot.tree.command(name="giveawayreroll", description="Ponownie wylosuj zwycięzcę z zakończonego giveawayu.")
async def giveawayreroll(interaction: discord.Interaction, message_id: str, old_winner: str):
    if not is_owner(interaction):
        await interaction.response.send_message("⛔ Tylko właściciel serwera lub administrator może użyć tej komendy.", ephemeral=True)
        return

    if message_id not in giveaway_data:
        await interaction.response.send_message("❌ Nie znaleziono giveawayu o tym ID.", ephemeral=True)
        return

    data = giveaway_data[message_id]
    participants = data.get("participants", [])
    winners = data.get("winners", [])

    if not participants or not winners:
        await interaction.response.send_message("⚠️ Brak danych uczestników lub zwycięzców do rerollu.", ephemeral=True)
        return

    old_name = old_winner.replace("@", "").lower()
    member_to_remove = None
    guild = bot.get_guild(data["guild_id"])
    if guild:
        for uid in winners:
            member = guild.get_member(uid)
            if member and (member.name.lower() == old_name or member.display_name.lower() == old_name or str(member.id) == old_name):
                member_to_remove = uid
                break

    if not member_to_remove:
        await interaction.response.send_message("❌ Nie znaleziono takiego zwycięzcy w tym giveawayu.", ephemeral=True)
        return

    possible_new = [p for p in participants if p not in winners]
    if not possible_new:
        await interaction.response.send_message("⚠️ Brak nowych osób do wylosowania.", ephemeral=True)
        return

    new_winner_id = random.choice(possible_new)
    data["winners"].remove(member_to_remove)
    data["winners"].append(new_winner_id)
    save_data(giveaway_data)

    new_mention = f"<@{new_winner_id}>"
    old_mention = f"<@{member_to_remove}>"
    await interaction.channel.send(f"🔁 Ponownie wylosowano zwycięzcę: {new_mention} (zamiast {old_mention}) 🎉")
    await interaction.response.send_message("✅ Reroll zakończony pomyślnie!", ephemeral=True)
# --- SYSTEM POWITAŃ Z KOMENDAMI KONFIGURACJI ---
import json

CONFIG_FILE = "welcome_config.json"

# Funkcja pomocnicza – odczyt konfiguracji
def load_welcome_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# Funkcja pomocnicza – zapis konfiguracji
def save_welcome_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- KOMENDA /kanałpowitań ---
@bot.tree.command(name="kanałpowitań", description="Ustaw kanał, w którym bot będzie witał nowych członków.")
async def set_welcome_channel(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("⛔ Tylko administrator może ustawić kanał powitań.", ephemeral=True)
        return

    config = load_welcome_config()
    config[str(interaction.guild.id)] = interaction.channel.id
    save_welcome_config(config)

    await interaction.response.send_message(
        f"✅ Kanał powitań został ustawiony na: {interaction.channel.mention}",
        ephemeral=True
    )

# --- KOMENDA /usuńkanałpowitań ---
@bot.tree.command(name="usuńkanałpowitań", description="Wyłącza system powitań na tym serwerze.")
async def remove_welcome_channel(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("⛔ Tylko administrator może usunąć kanał powitań.", ephemeral=True)
        return

    config = load_welcome_config()
    if str(interaction.guild.id) in config:
        del config[str(interaction.guild.id)]
        save_welcome_config(config)
        await interaction.response.send_message("🗑️ Kanał powitań został usunięty.", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ Nie ma ustawionego kanału powitań.", ephemeral=True)

# --- EVENT POWITAŃ ---
@bot.event
async def on_member_join(member: discord.Member):
    config = load_welcome_config()
    guild_id = str(member.guild.id)
    if guild_id not in config:
        return  # Brak ustawionego kanału, nic nie robimy

    channel_id = config[guild_id]
    channel = bot.get_channel(channel_id)
    if not channel:
        return

    guild = member.guild
    members_count = len([m for m in guild.members if not m.bot])

    embed = discord.Embed(
        title="🎉 Nowy członek na serwerze!",
        description=(
            f"{member.mention} miło Cię widzieć na serwerze **{guild.name}**!\n\n"
            f"👥 **Jest nas już:** {members_count}"
        ),
        color=discord.Color.from_str("#CC0000")
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Witaj w {guild.name}! 💫")

    await channel.send(embed=embed)
# --- URUCHOMIENIE MINI SERWERA ---
def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

# ------------------ URUCHOMIENIE BOTA -------------------------------
bot.run(os.environ.get("DISCORD_TOKEN") or os.environ.get("TOKEN"))
# -------------------------------------------------------------------
