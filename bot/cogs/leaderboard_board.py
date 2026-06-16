import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import COLOR_GOLD, LEADERBOARD_UPDATE_INTERVAL, STATS_UPDATE_INTERVAL
from database import get_server_config, set_server_config, get_leaderboard, get_server_stats, ensure_user


def build_leaderboard_embed(top: list) -> discord.Embed:
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    embed = discord.Embed(
        title="🏆 World Cup Prediction Leaderboard",
        color=COLOR_GOLD,
        timestamp=datetime.utcnow()
    )
    if not top:
        embed.description = "No predictions yet! Use `/predict` to get started."
    else:
        desc = ""
        for i, u in enumerate(top[:10]):
            m = medals[i] if i < len(medals) else "  "
            desc += f"{m} **{u['username']}**\n   `{u['points']:,} pts` • `{u['coins']:,} 🪙`\n"
        embed.description = desc
    embed.set_footer(text="Updated every 5 minutes • Use /predict to earn points!")
    return embed


def build_stats_embed(stats: dict) -> discord.Embed:
    embed = discord.Embed(
        title="📈 World Cup Server Statistics",
        color=COLOR_GOLD,
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="🎯 Total Predictions", value=f"`{stats['total_predictions']:,}`", inline=True)
    embed.add_field(name="👥 Total Participants", value=f"`{stats['total_users']:,}`", inline=True)
    embed.add_field(name="🪙 Fan Coins Earned", value=f"`{stats['total_coins']:,}`", inline=True)
    embed.add_field(name="📅 Active Today", value=f"`{stats['active_today']:,}`", inline=True)
    embed.add_field(name="✅ Completion Rate", value=f"`{stats['completion_rate']}%`", inline=True)
    embed.set_footer(text="Updates every 5 minutes")
    return embed


class LeaderboardBoard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.lb_task.start()
        self.stats_task.start()

    def cog_unload(self):
        self.lb_task.cancel()
        self.stats_task.cancel()

    @tasks.loop(seconds=LEADERBOARD_UPDATE_INTERVAL)
    async def lb_task(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            await self._update_leaderboard(guild)

    @tasks.loop(seconds=STATS_UPDATE_INTERVAL)
    async def stats_task(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            await self._update_stats(guild)

    @lb_task.before_loop
    async def before_lb(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)

    @stats_task.before_loop
    async def before_stats(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(15)

    async def _update_leaderboard(self, guild: discord.Guild):
        config = get_server_config(guild.id)
        if not config or not config.get("leaderboard_channel_id"):
            return
        channel = guild.get_channel(config["leaderboard_channel_id"])
        if not channel:
            return
        try:
            top = get_leaderboard(10)
            embed = build_leaderboard_embed(top)
            msg_id = config.get("leaderboard_message_id")
            if msg_id:
                try:
                    msg = await channel.fetch_message(msg_id)
                    await msg.edit(embed=embed)
                    return
                except discord.NotFound:
                    pass
            msg = await channel.send(embed=embed)
            set_server_config(guild.id, leaderboard_message_id=msg.id)
        except Exception as e:
            print(f"Leaderboard update error: {e}")

    async def _update_stats(self, guild: discord.Guild):
        config = get_server_config(guild.id)
        if not config or not config.get("stats_channel_id"):
            return
        channel = guild.get_channel(config["stats_channel_id"])
        if not channel:
            return
        try:
            stats = get_server_stats()
            embed = build_stats_embed(stats)
            msg_id = config.get("stats_message_id")
            if msg_id:
                try:
                    msg = await channel.fetch_message(msg_id)
                    await msg.edit(embed=embed)
                    return
                except discord.NotFound:
                    pass
            msg = await channel.send(embed=embed)
            set_server_config(guild.id, stats_message_id=msg.id)
        except Exception as e:
            print(f"Stats update error: {e}")

    @app_commands.command(name="setup_leaderboard", description="[Admin] Set the leaderboard channel")
    @app_commands.default_permissions(administrator=True)
    async def setup_leaderboard(self, interaction: discord.Interaction, channel: discord.TextChannel):
        set_server_config(interaction.guild_id, leaderboard_channel_id=channel.id)
        await interaction.response.send_message(f"✅ Leaderboard will auto-update in {channel.mention}.", ephemeral=True)
        await self._update_leaderboard(interaction.guild)

    @app_commands.command(name="setup_stats", description="[Admin] Set the server statistics channel")
    @app_commands.default_permissions(administrator=True)
    async def setup_stats(self, interaction: discord.Interaction, channel: discord.TextChannel):
        set_server_config(interaction.guild_id, stats_channel_id=channel.id)
        await interaction.response.send_message(f"✅ Stats will auto-update in {channel.mention}.", ephemeral=True)
        await self._update_stats(interaction.guild)


async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardBoard(bot))
