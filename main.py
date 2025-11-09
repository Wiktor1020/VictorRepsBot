import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio
from flask import Flask
from threading import Thread

# 🔹 Import giveaway logic (osobny plik)
from giveaway import setup_giveaway

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

    print("✅ Bot w pełni gotowy do pracy.")
# --------------------------------------------------------------

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
