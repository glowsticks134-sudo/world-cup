import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import random
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import COLOR_GOLD, COLOR_GREEN, COLOR_RED, GIVEAWAY_ENTRY_COINS
from database import get_connection, ensure_user, get_user, update_coins


def parse_duration(duration: str) -> int:
    """Parse duration string like '1h', '30m', '2d' into seconds."""
    unit = duration[-1].lower()
    try:
        value = int(duration[:-1])
    except ValueError:
        return 3600
    if unit == 'm':
        return value * 60
    elif unit == 'h':
        return value * 3600
    elif unit == 'd':
        return value * 86400
    return 3600


class GiveawayEntryButton(discord.ui.View):
    def __init__(self, giveaway_id: int):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @discord.ui.button(label="🎉 Enter Giveaway", style=discord.ButtonStyle.success, custom_id="giveaway_enter")
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):
        ensure_user(interaction.user.id, interaction.user.display_name)

        conn = get_connection()
        giveaway = conn.execute(
            "SELECT * FROM giveaways WHERE id=? AND active=1", (self.giveaway_id,)
        ).fetchone()

        if not giveaway:
            conn.close()
            await interaction.response.send_message("This giveaway has ended!", ephemeral=True)
            return

        existing = conn.execute(
            "SELECT entries FROM giveaway_entries WHERE giveaway_id=? AND user_id=?",
            (self.giveaway_id, interaction.user.id)
        ).fetchone()

        if existing:
            conn.close()
            await interaction.response.send_message(
                f"You're already entered with **{existing['entries']} entries**! Good luck! 🍀", ephemeral=True
            )
            return

        # Bonus entries for active users
        user = get_user(interaction.user.id)
        bonus_entries = 1
        if user and user.get("points", 0) >= 500:
            bonus_entries = 2
        if user and user.get("streak", 0) >= 7:
            bonus_entries += 1

        conn.execute(
            "INSERT INTO giveaway_entries (giveaway_id, user_id, entries) VALUES (?,?,?)",
            (self.giveaway_id, interaction.user.id, bonus_entries)
        )
        conn.commit()

        entry_count = conn.execute(
            "SELECT SUM(entries) FROM giveaway_entries WHERE giveaway_id=?", (self.giveaway_id,)
        ).fetchone()[0] or 0
        conn.close()

        await interaction.response.send_message(
            f"✅ You entered with **{bonus_entries} ticket(s)**! {'(Bonus for your activity!)' if bonus_entries > 1 else ''}\n"
            f"Total entries in this giveaway: **{entry_count}**\n\nGood luck! 🍀",
            ephemeral=True
        )


class Giveaway(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_giveaways.start()

    def cog_unload(self):
        self.check_giveaways.cancel()

    @tasks.loop(seconds=30)
    async def check_giveaways(self):
        await self.bot.wait_until_ready()
        conn = get_connection()
        now = datetime.utcnow().isoformat()
        expired = conn.execute(
            "SELECT * FROM giveaways WHERE active=1 AND end_time <= ?", (now,)
        ).fetchall()
        conn.close()

        for giveaway in expired:
            await self.end_giveaway(dict(giveaway))

    @check_giveaways.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    async def end_giveaway(self, giveaway: dict):
        conn = get_connection()
        conn.execute("UPDATE giveaways SET active=0 WHERE id=?", (giveaway["id"],))
        conn.commit()

        entries = conn.execute(
            "SELECT user_id, entries FROM giveaway_entries WHERE giveaway_id=?",
            (giveaway["id"],)
        ).fetchall()
        conn.close()

        if not entries:
            return

        pool = []
        for e in entries:
            pool.extend([e["user_id"]] * e["entries"])

        winner_id = random.choice(pool)

        channel = self.bot.get_channel(giveaway["channel_id"])
        if not channel:
            return

        winner = await self.bot.fetch_user(winner_id)
        if winner:
            embed = discord.Embed(
                title="🎉 GIVEAWAY ENDED!",
                description=f"**Prize:** {giveaway['prize']}\n\n"
                            f"🏆 **Winner:** {winner.mention} ({winner.display_name})\n\n"
                            f"Congratulations! Contact an admin to claim your prize.",
                color=COLOR_GREEN,
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text=f"{len(pool)} total entries • {len(entries)} participants")
            await channel.send(f"🎊 Congratulations {winner.mention}!", embed=embed)

            conn = get_connection()
            conn.execute("UPDATE giveaways SET winner_id=? WHERE id=?", (winner_id, giveaway["id"]))
            conn.commit()
            conn.close()

    @app_commands.command(name="giveaway", description="[Admin] Start a giveaway")
    @app_commands.default_permissions(administrator=True)
    async def start_giveaway(
        self, interaction: discord.Interaction,
        prize: str, duration: str, channel: discord.TextChannel = None
    ):
        target = channel or interaction.channel
        seconds = parse_duration(duration)
        end_time = (datetime.utcnow() + timedelta(seconds=seconds)).isoformat()

        conn = get_connection()
        cursor = conn.execute(
            "INSERT INTO giveaways (channel_id, prize, end_time, created_by) VALUES (?,?,?,?)",
            (target.id, prize, end_time, interaction.user.id)
        )
        giveaway_id = cursor.lastrowid
        conn.commit()
        conn.close()

        end_dt = datetime.utcnow() + timedelta(seconds=seconds)
        embed = discord.Embed(
            title="🎁 WORLD CUP GIVEAWAY!",
            description=f"**Prize:** {prize}\n\n"
                        f"⏰ **Ends:** <t:{int(end_dt.timestamp())}:R>\n"
                        f"🎫 **Bonus entries** for active members (7+ day streak, 500+ points)!\n\n"
                        f"Click below to enter!",
            color=COLOR_GOLD,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Giveaway #{giveaway_id} • Hosted by {interaction.user.display_name}")

        view = GiveawayEntryButton(giveaway_id)
        msg = await target.send(embed=embed, view=view)

        conn = get_connection()
        conn.execute("UPDATE giveaways SET message_id=? WHERE id=?", (msg.id, giveaway_id))
        conn.commit()
        conn.close()

        await interaction.response.send_message(
            f"✅ Giveaway started in {target.mention}! Ends in {duration}.", ephemeral=True
        )

    @app_commands.command(name="giveaway_end", description="[Admin] End a giveaway early")
    @app_commands.default_permissions(administrator=True)
    async def end_giveaway_cmd(self, interaction: discord.Interaction, giveaway_id: int):
        conn = get_connection()
        g = conn.execute("SELECT * FROM giveaways WHERE id=? AND active=1", (giveaway_id,)).fetchone()
        conn.close()

        if not g:
            await interaction.response.send_message("Giveaway not found or already ended.", ephemeral=True)
            return

        await self.end_giveaway(dict(g))
        await interaction.response.send_message(f"✅ Giveaway #{giveaway_id} ended early.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Giveaway(bot))
