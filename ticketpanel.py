import discord
from discord import app_commands
from discord.ext import commands
import json
import os

TICKET_FILE = "active_tickets.json"


def load_tickets():
    if not os.path.exists(TICKET_FILE):
        with open(TICKET_FILE, "w") as f:
            json.dump({}, f)
    with open(TICKET_FILE, "r") as f:
        return json.load(f)


def save_tickets(data):
    with open(TICKET_FILE, "w") as f:
        json.dump(data, f, indent=4)


active_tickets = load_tickets()


class TicketModal(discord.ui.Modal, title="Nowy ticket"):
    def __init__(self, bot, category_name):
        super().__init__()
        self.bot = bot
        self.category_name = category_name

        self.add_item(discord.ui.TextInput(
            label="Treść zgłoszenia:",
            placeholder="Opisz swój problem...",
            style=discord.TextStyle.long,
            required=True
        ))

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user

        category = discord.utils.get(
            guild.categories,
            name=f"🎟️・TICKETY・{self.category_name.upper()}"
        )

        if category is None:
            try:
                category = await guild.create_category(f"🎟️・TICKETY・{self.category_name.upper()}")
            except Exception as e:
                return await interaction.response.send_message(
                    f"Wystąpił błąd przy tworzeniu kategorii: {e}",
                    ephemeral=True
                )

        ticket_number = len(active_tickets) + 1
        channel_name = f"ticket-{member.name}-{self.category_name.lower()}-{ticket_number}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        try:
            channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
        except Exception as e:
            return await interaction.response.send_message(
                f"Nie udało się utworzyć kanału ticketu: {e}",
                ephemeral=True
            )

        active_tickets[str(channel.id)] = {
            "user": member.id,
            "category": self.category_name,
            "content": interaction.text_values[0]
        }
        save_tickets(active_tickets)

        await interaction.response.send_message(f"Ticket utworzony: {channel.mention}", ephemeral=True)

        await channel.send(
            f"🎟️ **Nowy ticket od {member.mention}**\n"
            f"**Kategoria:** {self.category_name}\n"
            f"**Treść zgłoszenia:**\n```{interaction.text_values[0]}```",
            view=CloseTicketView(self.bot)
        )


class CloseTicketView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Zamknij ticket", style=discord.ButtonStyle.red, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel

        if str(channel.id) not in active_tickets:
            return await interaction.response.send_message("Ten ticket już jest zamknięty.", ephemeral=True)

        try:
            del active_tickets[str(channel.id)]
            save_tickets(active_tickets)
            await interaction.response.send_message("Ticket zamknięty. Kanał usuwany...", ephemeral=True)
            await channel.delete()
        except Exception as e:
            await interaction.response.send_message(f"Nie udało się usunąć kanału: {e}", ephemeral=True)


class TicketPanelView(discord.ui.View):
    def __init__(self, bot, categories):
        super().__init__(timeout=None)
        self.bot = bot
        self.categories = categories

        for category in categories:
            self.add_item(TicketButton(bot, category))


class TicketButton(discord.ui.Button):
    def __init__(self, bot, category):
        super().__init__(label=category, style=discord.ButtonStyle.green,
                         custom_id=f"ticket_btn_{category.lower()}")
        self.bot = bot
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(self.bot, self.category))


async def setup(bot):
    @bot.tree.command(name="ticketpanel2", description="Tworzy panel ticketów z kategoriami.")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticketpanel2(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)

        categories = ["Pomoc", "Skarga", "Odwołanie", "Partnerstwa"]

        embed = discord.Embed(
            title="🎟️ Panel ticketów",
            description="Wybierz kategorię, aby utworzyć ticket.",
            color=discord.Color.blue()
        )

        await interaction.followup.send(embed=embed, view=TicketPanelView(bot, categories))

    await bot.add_cog(commands.Cog())
