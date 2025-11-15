# stylizowanie.py
import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio

BACKUP_FILE = "kanaly_backup.json"

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
    "głos": "🔊",
    "ogłoszenia": "📢",
    "event": "🎉",
    "giveaway": "🎁",
    "muzyka": "🎵"
}

def stylize_text(text: str) -> str:
    normal = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    fancy = "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢABCDEFGHIJKLMNOPQRSTUVWXYZ"
    table = str.maketrans(normal, fancy)
    return text.translate(table)

def save_backup_obj(guild: discord.Guild):
    """
    Zapisuje backup nazw kanałów i kategorii do pliku JSON.
    Struktura:
    {
      "channels": { "<channel_id>": "<name>", ... },
      "categories": { "<category_id>": "<name>", ... }
    }
    """
    data = {
        "channels": {str(c.id): c.name for c in guild.channels if isinstance(c, discord.abc.GuildChannel)},
        "categories": {str(cat.id): cat.name for cat in guild.categories}
    }
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_backup_obj():
    if not os.path.exists(BACKUP_FILE):
        return {"channels": {}, "categories": {}}
    with open(BACKUP_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {"channels": {}, "categories": {}}

def is_owner_or_admin(interaction: discord.Interaction) -> bool:
    if not interaction.guild:
        return False
    return interaction.user.id == interaction.guild.owner_id or interaction.user.guild_permissions.administrator

class Stylizowanie(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Stylizuj kanały
    @app_commands.command(name="stylizujkanaly", description="Stylizuje wszystkie nazwy kanałów (owner/admin).")
    async def stylizujkanaly(self, interaction: discord.Interaction):
        if not is_owner_or_admin(interaction):
            await interaction.response.send_message("⛔ Nie masz uprawnień do tej komendy.", ephemeral=True)
            return

        await interaction.response.send_message("✨ Stylizowanie kanałów... (zapisuję backup)", ephemeral=True)
        # Zapis backupu
        save_backup_obj(interaction.guild)

        changed = 0
        for channel in interaction.guild.channels:
            # pomiń kategorie; stylizujemy tylko kanały tekstowe/voice itd.
            if isinstance(channel, discord.CategoryChannel):
                continue

            try:
                name_lower = channel.name.lower()
                emoji = next((val for key, val in channel_emojis.items() if key in name_lower), "💠")
                new_name = f"「{emoji}」{stylize_text(channel.name)}"
                # jeżeli nazwa już taka sama — pominąć
                if channel.name != new_name:
                    await channel.edit(name=new_name)
                    changed += 1
                await asyncio.sleep(0.8)  # delikatne opóźnienie, żeby nie przekroczyć ratelimit
            except Exception as e:
                # logujemy, ale nie przerywamy działania
                print(f"[stylizujkanaly] Błąd przy {channel.name}: {e}")

        await interaction.followup.send(f"✅ Kanały zostały wystylizowane! Zmieniono: **{changed}**.", ephemeral=True)

    # Stylizuj kategorie
    @app_commands.command(name="stylizujkategorie", description="Stylizuje wszystkie kategorie (owner/admin).")
    async def stylizujkategorie(self, interaction: discord.Interaction):
        if not is_owner_or_admin(interaction):
            await interaction.response.send_message("⛔ Nie masz uprawnień do tej komendy.", ephemeral=True)
            return

        await interaction.response.send_message("✨ Stylizowanie kategorii... (zapisuję backup)", ephemeral=True)
        save_backup_obj(interaction.guild)

        changed = 0
        for category in interaction.guild.categories:
            try:
                base = stylize_text(category.name)
                new_name = f"┏╍╍╍╍╼⪼ {base} ⪻╾╍╍╍╍┓"
                if category.name != new_name:
                    await category.edit(name=new_name)
                    changed += 1
                await asyncio.sleep(0.8)
            except Exception as e:
                print(f"[stylizujkategorie] Błąd przy {category.name}: {e}")

        await interaction.followup.send(f"✅ Kategorie zostały wystylizowane! Zmieniono: **{changed}**.", ephemeral=True)

    # Przywróć nazwy
    @app_commands.command(name="przywroc_kanaly", description="Przywraca pierwotne nazwy kanałów i kategorii z backupu (owner/admin).")
    async def przywroc_kanaly(self, interaction: discord.Interaction):
        if not is_owner_or_admin(interaction):
            await interaction.response.send_message("⛔ Nie masz uprawnień do tej komendy.", ephemeral=True)
            return

        backup = load_backup_obj()
        channels_b = backup.get("channels", {})
        categories_b = backup.get("categories", {})

        if not channels_b and not categories_b:
            await interaction.response.send_message("⚠️ Brak backupu do przywrócenia.", ephemeral=True)
            return

        await interaction.response.send_message("♻️ Przywracanie nazw...", ephemeral=True)

        # Przywracaj kategorie (najpierw kategorie, żeby nazwy kanałów mogły być poprawnie ustawione)
        restored_cats = 0
        for cat_id, name in categories_b.items():
            try:
                cat = interaction.guild.get_channel(int(cat_id))
                if isinstance(cat, discord.CategoryChannel) and cat.name != name:
                    await cat.edit(name=name)
                    restored_cats += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[przywroc_kanaly] Błąd przy kategorii {cat_id}: {e}")

        restored_channels = 0
        for ch_id, name in channels_b.items():
            try:
                ch = interaction.guild.get_channel(int(ch_id))
                # Jeśli kanał już nie istnieje — pomijamy
                if ch and ch.name != name:
                    await ch.edit(name=name)
                    restored_channels += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[przywroc_kanaly] Błąd przy kanale {ch_id}: {e}")

        await interaction.followup.send(f"✅ Przywrócono: **{restored_channels}** kanałów i **{restored_cats}** kategorii.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Stylizowanie(bot))
