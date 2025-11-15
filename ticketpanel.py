import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import asyncio
import json
import os

ACTIVE_FILE = "active_tickets.json"
active_tickets = {}  # {guild_id: {user_id: [kategorie]}}

# ---- helpers (save/load) ----
def load_active():
    global active_tickets
    if os.path.exists(ACTIVE_FILE):
        try:
            with open(ACTIVE_FILE, "r", encoding="utf-8") as f:
                active_tickets = json.load(f)
                # keys in JSON are strings, convert nested lists as needed
        except Exception:
            active_tickets = {}
    else:
        active_tickets = {}

def save_active():
    try:
        with open(ACTIVE_FILE, "w", encoding="utf-8") as f:
            json.dump(active_tickets, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

load_active()

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

        # ensure shapes (JSON stores keys as strings)
        g_id = str(guild.id)
        m_id = str(member.id)

        if g_id not in active_tickets:
            active_tickets[g_id] = {}
        if m_id not in active_tickets[g_id]:
            active_tickets[g_id][m_id] = []

        # --- użytkownik ma już ticket ---
        if self.category_name in active_tickets[g_id][m_id]:
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

        # admini widzą tickety
        for role in guild.roles:
            if role.permissions.manage_messages or role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        # --- główna kategoria ---
        category_name = "🎟️・TICKETY"
        category = discord.utils.get(guild.categories, name=category_name)

        if not category:
            category = await guild.create_category(name=category_name, overwrites=overwrites)
            try:
                await category.edit(position=0)
            except Exception:
                pass
        else:
            try:
                await category.edit(overwrites=overwrites, position=0)
            except Exception:
                pass

        # sanitize channel name
        safe_name = discord.utils.remove_markdown(member.name).lower()[:20]

        # --- utworzenie kanału ---
        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{safe_name}-{self.category_name.lower()}",
            category=category,
            topic=f"Ticket użytkownika {member} ({self.category_name})",
            overwrites=overwrites
        )

        # zapisz aktywny ticket (store as strings)
        active_tickets[g_id][m_id].append(self.category_name)
        save_active()

        # --- embed w ticketcie ---
        embed = discord.Embed(
            title=f"🎫 Ticket - {self.category_name}",
            description=f"**Użytkownik:** {member.mention}\n\n📩 **Zgłoszenie:**\n{self.problem.value}",
            color=discord.Color.from_str("#CC0000")
        )
        embed.set_footer(text="VictorReps | System Ticketów")

        # --- przycisk zamknięcia ---
        close_btn = Button(label="Zamknij ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id=f"close_ticket:{ticket_channel.id}")

        async def close_callback(inter_close: discord.Interaction):
            # allow requester or manage_channels
            if inter_close.user == member or inter_close.user.guild_permissions.manage_channels:
                await inter_close.response.send_message("🔒 Ticket zostanie zamknięty za 5 sekund...", ephemeral=True)
                await asyncio.sleep(5)
                try:
                    await ticket_channel.delete()
                except Exception:
                    pass

                # usuń z listy aktywnych
                g_id_local = str(guild.id)
                m_id_local = str(member.id)
                if g_id_local in active_tickets and m_id_local in active_tickets[g_id_local]:
                    if self.category_name in active_tickets[g_id_local][m_id_local]:
                        active_tickets[g_id_local][m_id_local].remove(self.category_name)
                        save_active()
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
        # persistent button -> custom_id required
        super().__init__(label=label, emoji=emoji, style=discord.ButtonStyle.secondary, custom_id=f"ticket_btn:{label}")

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


# ------------------ KOMENDA /ticketpanel (cog) ------------------
class TicketPanelCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # ensure persistent view registered when cog is loaded
        # bot.add_view requires View with persistent children (custom_id) and timeout=None
        bot.add_view(TicketPanel())

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
        await interaction.response.send_message(embed=embed, view=view)

# ---- setup ----
async def setup(bot):
    # ensure active tickets loaded
    load_active()
    await bot.add_cog(TicketPanelCog(bot))
    # register persistent view (redundant-safe)
    bot.add_view(TicketPanel())
