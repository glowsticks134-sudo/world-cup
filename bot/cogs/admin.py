import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import COLOR_GOLD, COLOR_GREEN, COLOR_RED, ACHIEVEMENTS
from database import (
    ensure_user, get_user, update_coins, update_points,
    get_connection, set_server_config, get_server_config, grant_achievement
)


class EventGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="event", description="Admin event management")

    @app_commands.command(name="start", description="Start a hype train event")
    @app_commands.default_permissions(administrator=True)
    async def start(self, interaction: discord.Interaction, prize_coins: int = 100):
        event_types = [
            ("⚽ Score Prediction Rush", "First 10 members to predict today's score win coins!"),
            ("🔥 Trivia Blitz", "A rapid-fire trivia challenge — fastest correct answer wins!"),
            ("🎯 Lucky Kick", "Click the button for a chance to win coins!"),
            ("🏆 Fan Loyalty Check", "Show your World Cup spirit and grab coins!"),
        ]
        event_type, desc = random.choice(event_types)

        end_time = datetime.utcnow() + timedelta(minutes=5)

        embed = discord.Embed(
            title=f"🔥 HYPE TRAIN EVENT: {event_type}",
            description=f"{desc}\n\n💰 **Prize:** {prize_coins} Fan Coins for participants!\n⏰ **Ends:** <t:{int(end_time.timestamp())}:R>\n\nClick below to participate!",
            color=COLOR_GOLD,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="Hype Train • World Cup Festival")

        view = HypeEventView(prize_coins)
        msg = await interaction.channel.send(embed=embed, view=view)

        await interaction.response.send_message(
            f"✅ Hype event started! Ends in 5 minutes.", ephemeral=True
        )

        await asyncio.sleep(300)
        view.stop()

        participants = view.participants
        if participants:
            winners_text = "\n".join(f"<@{uid}>" for uid in list(participants)[:10])
            result_embed = discord.Embed(
                title="🎉 Hype Event Ended!",
                description=f"**{len(participants)} participants** joined!\n\n🏆 Coins awarded to:\n{winners_text}",
                color=COLOR_GREEN,
                timestamp=datetime.utcnow()
            )
            await msg.reply(embed=result_embed)
        else:
            result_embed = discord.Embed(
                title="Hype Event Ended",
                description="No one participated this time. Better luck next event!",
                color=COLOR_RED
            )
            await msg.reply(embed=result_embed)

    @app_commands.command(name="announcement", description="Post a styled World Cup announcement")
    @app_commands.default_permissions(administrator=True)
    async def announcement(self, interaction: discord.Interaction, title: str, message: str, channel: discord.TextChannel = None):
        target = channel or interaction.channel
        embed = discord.Embed(
            title=f"📢 {title}",
            description=message,
            color=COLOR_GOLD,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="World Cup Festival • Official Announcement")
        await target.send("@everyone", embed=embed)
        await interaction.response.send_message(f"✅ Announcement posted in {target.mention}.", ephemeral=True)


class HypeEventView(discord.ui.View):
    def __init__(self, prize_coins: int):
        super().__init__(timeout=300)
        self.prize_coins = prize_coins
        self.participants: set = set()

    @discord.ui.button(label="🎉 Join Hype Train!", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        ensure_user(interaction.user.id, interaction.user.display_name)
        if interaction.user.id in self.participants:
            await interaction.response.send_message("You're already in! 🎉", ephemeral=True)
            return

        self.participants.add(interaction.user.id)
        update_coins(interaction.user.id, self.prize_coins)

        await interaction.response.send_message(
            f"✅ You joined! +**{self.prize_coins} 🪙 Fan Coins** added!\n"
            f"Total participants: **{len(self.participants)}**", ephemeral=True
        )


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.tree.add_command(EventGroup())

    @app_commands.command(name="admin_coins", description="[Admin] Add or remove coins from a user")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(action="add or remove", member="Target member", amount="Amount of coins")
    @app_commands.choices(action=[
        app_commands.Choice(name="add", value="add"),
        app_commands.Choice(name="remove", value="remove"),
    ])
    async def admin_coins(self, interaction: discord.Interaction, action: str, member: discord.Member, amount: int):
        ensure_user(member.id, member.display_name)
        if action == "add":
            update_coins(member.id, amount)
            msg = f"✅ Added **{amount} 🪙** to {member.mention}"
        else:
            update_coins(member.id, -amount)
            msg = f"✅ Removed **{amount} 🪙** from {member.mention}"

        embed = discord.Embed(description=msg, color=COLOR_GREEN, timestamp=datetime.utcnow())
        embed.set_footer(text=f"Admin action by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="admin_points", description="[Admin] Add or remove points from a user")
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(action=[
        app_commands.Choice(name="add", value="add"),
        app_commands.Choice(name="remove", value="remove"),
    ])
    async def admin_points(self, interaction: discord.Interaction, action: str, member: discord.Member, amount: int):
        ensure_user(member.id, member.display_name)
        update_points(member.id, amount if action == "add" else -amount)
        msg = f"✅ {'Added' if action == 'add' else 'Removed'} **{amount} points** {'to' if action == 'add' else 'from'} {member.mention}"
        embed = discord.Embed(description=msg, color=COLOR_GREEN, timestamp=datetime.utcnow())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="reset_leaderboard", description="[Admin] Reset all prediction points")
    @app_commands.default_permissions(administrator=True)
    async def reset_leaderboard(self, interaction: discord.Interaction, confirm: str):
        if confirm.lower() != "yes i am sure":
            await interaction.response.send_message(
                "To confirm, run this command with `confirm: yes i am sure`", ephemeral=True
            )
            return
        conn = get_connection()
        conn.execute("UPDATE users SET points=0")
        conn.execute("DELETE FROM predictions")
        conn.commit()
        conn.close()
        await interaction.response.send_message("✅ Leaderboard has been reset.", ephemeral=True)

    @app_commands.command(name="award_achievement", description="[Admin] Manually award an achievement")
    @app_commands.default_permissions(administrator=True)
    async def award_achievement(self, interaction: discord.Interaction, member: discord.Member, achievement: str):
        ensure_user(member.id, member.display_name)
        if achievement not in ACHIEVEMENTS:
            keys = ", ".join(ACHIEVEMENTS.keys())
            await interaction.response.send_message(f"Invalid achievement. Options: {keys}", ephemeral=True)
            return
        earned = grant_achievement(member.id, achievement)
        ach = ACHIEVEMENTS[achievement]
        if earned:
            update_coins(member.id, ach["coins"])
            await interaction.response.send_message(
                f"✅ Awarded **{ach['icon']} {ach['name']}** to {member.mention} (+{ach['coins']} coins)", ephemeral=True
            )
        else:
            await interaction.response.send_message(f"{member.mention} already has this achievement.", ephemeral=True)

    @app_commands.command(name="setup_all", description="[Admin] Quick setup all bot channels at once")
    @app_commands.default_permissions(administrator=True)
    async def setup_all(
        self, interaction: discord.Interaction,
        live: discord.TextChannel,
        leaderboard: discord.TextChannel,
        stats: discord.TextChannel,
        bracket: discord.TextChannel,
        notifications: discord.TextChannel
    ):
        set_server_config(
            interaction.guild_id,
            live_channel_id=live.id,
            leaderboard_channel_id=leaderboard.id,
            stats_channel_id=stats.id,
            bracket_channel_id=bracket.id,
            notify_channel_id=notifications.id,
        )
        embed = discord.Embed(
            title="✅ World Cup Festival Setup Complete!",
            description=(
                f"All channels configured:\n\n"
                f"⚽ Live Scores: {live.mention}\n"
                f"🏆 Leaderboard: {leaderboard.mention}\n"
                f"📈 Statistics: {stats.mention}\n"
                f"🏅 Tournament Tracker: {bracket.mention}\n"
                f"🔔 Notifications: {notifications.mention}\n\n"
                f"The bot will begin updating all channels automatically!"
            ),
            color=COLOR_GREEN,
            timestamp=datetime.utcnow()
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
