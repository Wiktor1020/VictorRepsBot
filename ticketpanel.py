# ticketpanel.py
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import asyncio
import json
import os

ACTIVE_FILE = "active_tickets.json"

def load_active():
    if not os.path.exists(ACTIVE_FILE):
        return {}
    try:
        with open(ACTIVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_active(data):
    try:
        with open(ACTIVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

# structure: {guild_id: {user_id: [categories]}}
active_tickets = load_active()

# ------------------ MODAL OTWIERANIA TICKETA ------------------
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
        gid = str(guild.id)
        uid = str(member.id)

        if gid not in active_tickets:
            active_tickets[gid] = {}
        if uid not in active_tickets[gid]:
            active_tickets[gid][uid] = []

        # --- użytkownik ma już ticket ---
        if self.category_name in active_tickets[gid][uid]:
            await interaction.response.send_message(
                "⚠️ Masz już otwarty ticket w tej kategorii! Zamknij go, zanim utworzysz nowy.",
                ephemeral=True
            )
            return

        # --- uprawnienia ---
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }

        # admini/moderacja widzą tickety
        for role in guild.roles:
            if role.permissions.manage_messages or role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        # --- główna kategoria ---
        category_name = "🎟️・TICKETY"
        category = discord.utils.get(guild.categories, name=category_name)

        if not category:
            category = await guild.create_category(name=category_name, overwrites=overwrites)
            await category.edit(position=0)
        else:
            await category.edit(overwrites=overwrites, position=0)

        # --- utworzenie kanału ---
        safe_label = self.category_name.lower().replace(" ", "-")
        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{member.name}-{safe_label}",
            category=category,
            topic=f"Ticket użytkownika {member} ({self.category_name})",
            overwrites=overwrites
        )

        # zapisz aktywny ticket
        active_tickets[gid][uid].append(self.category_name)
        save_active(active_tickets)

        # --- embed w ticketcie ---
        embed = discord.Embed(
            title=f"🎫 Ticket - {self.category_name}",
            description=f"**Użytkownik:** {member.mention}\n\n📩 **Zgłoszenie:**\n{self.problem.value}",
            color=discord.Color.from_str("#CC0000")
        )
        embed.set_footer(text="VictorReps | System Ticketów")

        # --- przycisk zamknięcia (nie-persistent, tylko lokalny do danego kanału) ---
        close_btn = Button(label="Zamknij ticket", style=discord.ButtonStyle.danger, emoji="🔒")

        async def close_callback(inter_close: discord.Interaction):
            if inter_close.user == member or inter_close.user.guild_permissions.manage_channels:
                await inter_close.response.send_message("🔒 Ticket zostanie zamknięty za 5 sekund...", ephemeral=True)
                await asyncio.sleep(5)
                try:
                    await ticket_channel.delete()
                except Exception:
                    pass

                # usuń z listy aktywnych
                gid2 = str(guild.id)
                uid2 = str(member.id)
                if gid2 in active_tickets and uid2 in active_tickets[gid2]:
                    if self.category_name in active_tickets[gid2][uid2]:
                        active_tickets[gid2][uid2].remove(self.category_name)
                        save_active(active_tickets)
            else:
                await inter_close.response.send_message("⛔ Nie możesz zamknąć tego ticketa.", ephemeral=True)

        close_btn.callback = close_callback

        view = View(timeout=None)
        view.add_item(close_btn)

        await ticket_channel.send(content=f"{member.mention}", embed=embed, view=view)
        await interaction.response.send_message(
            f"✅ Ticket został utworzony: {ticket_channel.mention}", ephemeral=True
        )

# ------------------ PRZYCISKI NA PANELU ------------------
class TicketButton(Button):
    def __init__(self, label: str, emoji: str):
        # ustaw stały custom_id aby view był persistent i działał po restarcie
        custom = f"ticket_btn:{label}"
        super().__init__(label=label, emoji=emoji, style=discord.ButtonStyle.secondary, custom_id=custom)

    async def callback(self, interaction: discord.Interaction):
        modal = TicketModal(self.label)
        await interaction.response.send_modal(modal)

# ------------------ PANEL TICKETÓW ------------------
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

# ------------------ COG z komendą /ticketpanel ------------------
class TicketPanelCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ticketpanel", description="Wyświetla panel ticketów (dla właściciela lub admina).")
    async def ticketpanel_cmd(self, interaction: discord.Interaction):

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
        # wysyłamy i również rejestrujemy persistent view (jeśli nie zarejestrowana)
        try:
            # wysyłamy
            await interaction.response.send_message(embed=embed, view=view)
            # zarejestruj globalnie (bot.add_view działa też gdy wywołane wielokrotnie)
            self.bot.add_view(TicketPanel())
        except Exception as e:
            await interaction.response.send_message("❌ Błąd podczas wysyłania panelu.", ephemeral=True)
            print("ticketpanel send error:", e)

async def setup(bot):
    cog = TicketPanelCog(bot)
    await bot.add_cog(cog)
    # przy ładowaniu rozszerzenia rejestruj persistent view (ważne do działania po restarcie)
    bot.add_view(TicketPanel())
