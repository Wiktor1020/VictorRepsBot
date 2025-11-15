import discord
from discord.ext import commands
from discord import app_commands
import json
import os

TICKETS_FILE = "tickets.json"

def load_tickets():
    if not os.path.exists(TICKETS_FILE):
        return {}
    with open(TICKETS_FILE, "r") as f:
        return json.load(f)

def save_tickets(data):
    with open(TICKETS_FILE, "w") as f:
        json.dump(data, f, indent=4)


# --------------------- MODAL ---------------------
class TicketModal(discord.ui.Modal, title="Utwórz ticket"):
    def __init__(self, category_name, bot):
        super().__init__()
        self.category_name = category_name
        self.bot = bot

        self.problem = discord.ui.TextInput(
            label="Opisz problem",
            style=discord.TextStyle.long,
            required=True,
            max_length=400
        )
        self.add_item(self.problem)

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        tickets = load_tickets()

        # --- Czy użytkownik ma już ticket w tej kategorii? ---
        if str(interaction.guild_id) in tickets:
            if str(user.id) in tickets[str(interaction.guild_id)].get(self.category_name, {}):
                try:
                    existing_channel_id = tickets[str(interaction.guild_id)][self.category_name][str(user.id)]
                    existing_channel = interaction.guild.get_channel(existing_channel_id)
                    if existing_channel:
                        await interaction.response.send_message(
                            f"❗ Masz już ticket: {existing_channel.mention}", ephemeral=True
                        )
                        return
                    else:
                        # kanał nie istnieje — usuwamy wpis
                        del tickets[str(interaction.guild_id)][self.category_name][str(user.id)]
                        save_tickets(tickets)
                except KeyError:
                    pass

        # --- Sprawdzamy kategorię, tworzymy jeśli brak ---
        category = discord.utils.get(interaction.guild.categories, name=self.category_name)
        if not category:
            category = await interaction.guild.create_category(self.category_name)

        # --- Tworzenie kanału ticketu ---
        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{user.name}-{self.category_name.lower()}",
            category=category,
            topic=f"Ticket użytkownika {user}",
            overwrites={
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
        )

        # --- Rejestracja ticketu w bazie ---
        guild_id = str(interaction.guild_id)
        if guild_id not in tickets:
            tickets[guild_id] = {}
        if self.category_name not in tickets[guild_id]:
            tickets[guild_id][self.category_name] = {}

        tickets[guild_id][self.category_name][str(user.id)] = channel.id
        save_tickets(tickets)

        await interaction.response.send_message(
            f"🎫 Ticket został utworzony: {channel.mention}", ephemeral=True
        )

        await channel.send(
            f"👋 Witaj {user.mention}!\n"
            f"Opisałeś problem:\n```\n{self.problem.value}\n```"
        )

        # Dodaj przycisk zamknięcia
        await channel.send(view=CloseTicketView(self.category_name, self.bot, user.id))


# --------------------- ZAMKNIĘCIE TICKETU ---------------------
class CloseTicketView(discord.ui.View):
    def __init__(self, category_name, bot, owner_id):
        super().__init__(timeout=None)
        self.category_name = category_name
        self.bot = bot
        self.owner_id = owner_id

    @discord.ui.button(label="Zamknij ticket", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        tickets = load_tickets()
        guild_id = str(interaction.guild_id)

        if guild_id not in tickets:
            return await interaction.response.send_message("❌ Ten ticket nie istnieje w bazie.", ephemeral=True)

        if self.category_name not in tickets[guild_id]:
            return await interaction.response.send_message("❌ Ticket nie jest powiązany z kategorią.", ephemeral=True)

        if str(self.owner_id) not in tickets[guild_id][self.category_name]:
            return await interaction.response.send_message("❌ Ticket nie jest zarejestrowany.", ephemeral=True)

        # Sprawdzamy czy user ma prawo zamknąć ticketa
        if interaction.user.id != self.owner_id and not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("❌ Nie masz permisji do zamknięcia tego ticketu.", ephemeral=True)

        channel = interaction.channel

        # Usuwamy z bazy
        del tickets[guild_id][self.category_name][str(self.owner_id)]
        save_tickets(tickets)

        await interaction.response.send_message("🗑️ Ticket zostanie zamknięty za 5 sekund...", ephemeral=True)

        try:
            await channel.delete(reason="Zamknięcie ticketu")
        except:
            pass


# --------------------- PRZYCISK PANELU ---------------------
class TicketButtonView(discord.ui.View):
    def __init__(self, category_name, bot):
        super().__init__(timeout=None)
        self.category_name = category_name
        self.bot = bot

    @discord.ui.button(label="🎫 Utwórz ticket", style=discord.ButtonStyle.green)
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal(self.category_name, self.bot))


# --------------------- KOG ---------------------
class TicketPanel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ticketpanel2", description="Utwórz panel ticketów")
    async def ticketpanel2(self, interaction: discord.Interaction, kategoria: str):
        embed = discord.Embed(
            title="🎫 Panel Ticketów",
            description="Kliknij przycisk, aby utworzyć ticket.",
            color=discord.Color.blue()
        )

        view = TicketButtonView(kategoria, self.bot)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✔ Panel ticketów został utworzony!", ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        print("TicketPanel załadowany — odtwarzam persistent views...")

        data = load_tickets()
        for guild_id, categories in data.items():
            for category_name in categories.keys():
                self.bot.add_view(TicketButtonView(category_name, self.bot))


async def setup(bot):
    await bot.add_cog(TicketPanel(bot))

