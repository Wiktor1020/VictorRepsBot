import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import asyncio

active_tickets = {}  # {guild_id: {user_id: [kategorie]}}


# ------------------------- MODAL TWORZENIA TICKETA -------------------------
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

        if self.category_name in active_tickets[guild.id][member.id]:
            await interaction.response.send_message(
                "⚠️ Masz już otwarty ticket w tej kategorii! Zamknij go, zanim utworzysz nowy.",
                ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
        }

        for role in guild.roles:
            if role.permissions.manage_messages or role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True
                )

        main_category_name = "🎟️・TICKETY"
        category = discord.utils.get(guild.categories, name=main_category_name)

        if not category:
            category = await guild.create_category(
                name=main_category_name,
                overwrites=overwrites
            )
            await category.edit(position=0)
        else:
            await category.edit(overwrites=overwrites, position=0)

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

        close_button = Button(
            label="Zamknij ticket",
            style=discord.ButtonStyle.danger,
            emoji="🔒",
            custom_id="close_ticket"
        )

        async def close_callback(inter_close: discord.Interaction):
            if inter_close.user == member or inter_close.user.guild_permissions.manage_channels:
                await inter_close.response.send_message(
                    "🔒 Ticket zostanie zamknięty za 5 sekund...", ephemeral=True
                )
                await asyncio.sleep(5)
                await ticket_channel.delete()

                if guild.id in active_tickets and member.id in active_tickets[guild.id]:
                    if self.category_name in active_tickets[guild.id][member.id]:
                        active_tickets[guild.id][member.id].remove(self.category_name)
            else:
                await inter_close.response.send_message(
                    "⛔ Nie możesz zamknąć tego ticketa.", ephemeral=True
                )

        close_button.callback = close_callback

        view = View(timeout=None)
        view.add_item(close_button)

        await ticket_channel.send(
            content=f"{member.mention}",
            embed=embed,
            view=view
        )

        await interaction.response.send_message(
            f"✅ Ticket został utworzony: {ticket_channel.mention}",
            ephemeral=True
        )


# ------------------------- PRZYCISKI NA PANELU -------------------------
class TicketButton(Button):
    def __init__(self, label: str, emoji: str):
        super().__init__(
            label=label,
            emoji=emoji,
            style=discord.ButtonStyle.secondary,
            custom_id=f"ticket_btn_{label}"
        )

    async def callback(self, interaction: discord.Interaction):
        modal = TicketModal(self.label)
        await interaction.response.send_modal(modal)


# ------------------------- PANEL TICKETÓW -------------------------
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


# ------------------------- /ticketpanel2 -------------------------
async def setup(bot: commands.Bot):
    @bot.tree.command(
        name="ticketpanel2",
        description="Wyświetla panel ticketów (tylko właściciel lub admin)."
    )
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
                "Kliknij odpowiedni przycisk poniżej, aby utworzyć ticket.\n\n"
                "Wybierz kategorię swojego problemu:"
            ),
            color=discord.Color.from_str("#CC0000")
        )
        embed.set_footer(text="VictorReps | System Ticketów")

        await interaction.response.send_message(
            embed=embed,
            view=TicketPanel()
        )

    # 🔥 PERSISTENT VIEW — działa po restarcie
    bot.add_view(TicketPanel())
