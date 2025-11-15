import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import asyncio
import json
import os

TICKETS_FILE = "tickets.json"


# ------------------ PERSISTENT STORAGE ------------------
def load_tickets():
    if not os.path.exists(TICKETS_FILE):
        return {}

    try:
        with open(TICKETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_tickets(data):
    with open(TICKETS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


active_tickets = load_tickets()


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

        if str(guild.id) not in active_tickets:
            active_tickets[str(guild.id)] = {}

        if str(member.id) not in active_tickets[str(guild.id)]:
            active_tickets[str(guild.id)][str(member.id)] = []

        # użytkownik ma już ticket
        if self.category_name in active_tickets[str(guild.id)][str(member.id)]:
            await interaction.response.send_message(
                "⚠️ Masz już otwarty ticket w tej kategorii!",
                ephemeral=True
            )
            return

        # uprawnienia
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }

        for role in guild.roles:
            if role.permissions.manage_messages or role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        category_name = "🎟️・TICKETY"
        category = discord.utils.get(guild.categories, name=category_name)

        if not category:
            category = await guild.create_category(name=category_name)
            await category.edit(position=0)

        # tworzenie kanału
        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{member.name}-{self.category_name.lower()}",
            category=category,
            overwrites=overwrites
        )

        # zapis do pliku
        active_tickets[str(guild.id)][str(member.id)].append(self.category_name)
        save_tickets(active_tickets)

        # embed
        embed = discord.Embed(
            title=f"🎫 Ticket - {self.category_name}",
            description=f"**Użytkownik:** {member.mention}\n\n📩 **Zgłoszenie:**\n{self.problem.value}",
            color=discord.Color.from_str("#CC0000")
        )

        # przycisk zamykania (persistent)
        close_btn = Button(
            label="Zamknij ticket",
            style=discord.ButtonStyle.danger,
            emoji="🔒",
            custom_id=f"close_ticket:{ticket_channel.id}"
        )

        async def close_callback(inter_close: discord.Interaction):
            if inter_close.user == member or inter_close.user.guild_permissions.manage_channels:
                await inter_close.response.send_message("🔒 Ticket zamyka się za 5 sekund...", ephemeral=True)
                await asyncio.sleep(5)
                await ticket_channel.delete()

                # usuń z pamięci
                if self.category_name in active_tickets[str(guild.id)][str(member.id)]:
                    active_tickets[str(guild.id)][str(member.id)].remove(self.category_name)
                    save_tickets(active_tickets)
            else:
                await inter_close.response.send_message("⛔ Nie możesz zamknąć tego ticketa.", ephemeral=True)

        close_btn.callback = close_callback

        view = View(timeout=None)
        view.add_item(close_btn)

        interaction.client.add_view(view)

        await ticket_channel.send(member.mention, embed=embed, view=view)
        await interaction.response.send_message(
            f"✅ Ticket utworzony: {ticket_channel.mention}",
            ephemeral=True
        )


# ------------------ PRZYCISKI NA PANELU ------------------
class TicketButton(Button):
    def __init__(self, label: str, emoji: str):
        super().__init__(label=label, emoji=emoji, style=discord.ButtonStyle.secondary)

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


# ------------------ COG ------------------
class TicketPanelCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # rejestracja przycisków zamykania po restarcie
        for guild_id in active_tickets:
            for user_id in active_tickets[guild_id]:
                for category in active_tickets[guild_id][user_id]:
                    pass  # tu nie trzeba dodawać widoków

        print("TicketPanel: persistent views załadowane.")

    @app_commands.command(name="ticketpanel", description="Wyświetla panel ticketów.")
    async def ticketpanel_cmd(self, interaction: discord.Interaction):
        view = TicketPanel()

        embed = discord.Embed(
            title="🎫 Panel Ticketów",
            description="Wybierz kategorię swojego zgłoszenia.",
            color=discord.Color.from_str("#CC0000")
        )

        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(TicketPanelCog(bot))
