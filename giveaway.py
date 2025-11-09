import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import json
import asyncio
import os
from datetime import datetime, timedelta

GIVEAWAY_FILE = "giveaways.json"
BUTTON_STYLE_JOIN = discord.ButtonStyle.grey
EMBED_COLOR = discord.Color.red()

def load_giveaways():
    if not os.path.exists(GIVEAWAY_FILE):
        return {}
    with open(GIVEAWAY_FILE, "r") as f:
        return json.load(f)

def save_giveaways(data):
    with open(GIVEAWAY_FILE, "w") as f:
        json.dump(data, f, indent=4)

class GiveawayView(View):
    def __init__(self, message_id: int):
        super().__init__(timeout=None)
        self.message_id = message_id

    @discord.ui.button(
        label="🎟️ Weź udział",
        style=BUTTON_STYLE_JOIN,
        custom_id="persistent_giveaway_join"  # ważne: persistent view
    )
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

        try:
            bot = interaction.client
            channel = bot.get_channel(g["channel_id"])
            msg = await channel.fetch_message(self.message_id)
            embed = msg.embeds[0]
            desc_lines = embed.description.split("\n")
            for i, line in enumerate(desc_lines):
                if line.startswith("📊"):
                    desc_lines[i] = f"📊 **Uczestnicy:** {len(g['participants'])}**"
            embed.description = "\n".join(desc_lines)
            await msg.edit(embed=embed, view=self)
        except Exception:
            pass

        await interaction.response.send_message("✅ Dołączyłeś do giveawayu!", ephemeral=True)

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_giveaways.start()

    def cog_unload(self):
        self.check_giveaways.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ Giveaway module ready.")
        data = load_giveaways()
        for message_id in data.keys():
            self.bot.add_view(GiveawayView(int(message_id)))

    @tasks.loop(seconds=30)
    async def check_giveaways(self):
        data = load_giveaways()
        updated = False
        for message_id, g in data.items():
            if g.get("ended"):
                continue

            end_time = datetime.fromisoformat(g["end_time"])
            if datetime.utcnow() >= end_time:
                g["ended"] = True
                updated = True
                await self.end_giveaway(g, int(message_id))
        if updated:
            save_giveaways(data)

    async def end_giveaway(self, g, message_id):
        channel = self.bot.get_channel(g["channel_id"])
        if not channel:
            return
        try:
            msg = await channel.fetch_message(message_id)
        except:
            return

        participants = g["participants"]
        winners_count = g.get("winners", 1)

        if not participants:
            result = "Brak uczestników 😢"
        else:
            winners = []
            for _ in range(min(winners_count, len(participants))):
                winner_id = participants.pop(participants.index(asyncio.random.choice(participants)))
                winners.append(winner_id)

            mentions = ", ".join(f"<@{w}>" for w in winners)
            result = f"🎉 Gratulacje {mentions}! Wygrywacie **{g['prize']}**!"

        embed = discord.Embed(
            title=f"🎉 Giveaway zakończony!",
            description=f"🎁 **Nagroda:** {g['prize']}\n{result}",
            color=discord.Color.red()
        )
        embed.set_footer(text="Giveaway zakończony!")

        await msg.edit(embed=embed, view=None)
        await channel.send(result)

    @commands.hybrid_command(name="giveaway")
    @commands.has_permissions(manage_messages=True)
    async def giveaway(self, ctx, czas: str, liczba_wygranych: int, *, nagroda: str):
        """Tworzy nowy giveaway (np. /giveaway 2m 1 Discord Nitro)"""
        time_map = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        unit = czas[-1]
        if unit not in time_map:
            await ctx.send("❌ Niepoprawny format czasu! Użyj s/m/h/d.")
            return

        try:
            seconds = int(czas[:-1]) * time_map[unit]
        except:
            await ctx.send("❌ Niepoprawny format czasu!")
            return

        end_time = datetime.utcnow() + timedelta(seconds=seconds)
        embed = discord.Embed(
            title="🎉 Nowy Giveaway!",
            description=(
                f"🎁 **Nagroda:** {nagroda}\n"
                f"🏆 **Zwycięzcy:** {liczba_wygranych}\n"
                f"⏰ **Koniec:** <t:{int(end_time.timestamp())}:R>\n"
                f"📊 **Uczestnicy:** 0"
            ),
            color=EMBED_COLOR
        )
        embed.set_footer(text=f"Rozpoczęty przez {ctx.author}")

        view = GiveawayView(0)
        msg = await ctx.send(embed=embed, view=view)
        view.message_id = msg.id

        data = load_giveaways()
        data[str(msg.id)] = {
            "prize": nagroda,
            "winners": liczba_wygranych,
            "channel_id": ctx.channel.id,
            "end_time": end_time.isoformat(),
            "participants": [],
            "ended": False
        }
        save_giveaways(data)
        self.bot.add_view(GiveawayView(msg.id))
        await ctx.send("✅ Giveaway został utworzony!")

    @commands.hybrid_command(name="giveawayreroll")
    @commands.has_permissions(manage_messages=True)
    async def giveaway_reroll(self, ctx, message_id: int):
        """Losuje nowych zwycięzców"""
        data = load_giveaways()
        g = data.get(str(message_id))
        if not g or not g.get("ended"):
            await ctx.send("❌ Ten giveaway jeszcze trwa lub nie istnieje.")
            return
        await self.end_giveaway(g, message_id)
        await ctx.send("🔁 Giveaway został ponownie wylosowany!")

    @commands.hybrid_command(name="giveawayend")
    @commands.has_permissions(manage_messages=True)
    async def giveaway_end(self, ctx, message_id: int):
        """Zakończ giveaway wcześniej"""
        data = load_giveaways()
        g = data.get(str(message_id))
        if not g or g.get("ended"):
            await ctx.send("❌ Ten giveaway już się zakończył lub nie istnieje.")
            return
        g["ended"] = True
        save_giveaways(data)
        await self.end_giveaway(g, message_id)
        await ctx.send("🛑 Giveaway został zakończony ręcznie.")

async def setup(bot):
    await bot.add_cog(Giveaway(bot))
