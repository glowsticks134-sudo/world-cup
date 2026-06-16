import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
from collections import defaultdict
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import COLOR_RED, COLOR_GREEN, COLOR_GOLD
from database import get_server_config, set_server_config, ensure_user


# Simple in-memory spam tracker
_message_times: dict = defaultdict(list)
_join_times: list = []
SPAM_THRESHOLD = 5      # messages
SPAM_WINDOW = 5         # seconds
RAID_THRESHOLD = 10     # joins
RAID_WINDOW = 30        # seconds


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.warned: set = set()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # Welcome message
        config = get_server_config(member.guild.id)

        # Anti-raid check
        now = datetime.utcnow()
        _join_times.append(now)
        recent = [t for t in _join_times if (now - t).total_seconds() < RAID_WINDOW]
        _join_times.clear()
        _join_times.extend(recent)

        if len(recent) >= RAID_THRESHOLD:
            # Enable verification level if not already
            if config and config.get("log_channel_id"):
                log_ch = member.guild.get_channel(config["log_channel_id"])
                if log_ch:
                    embed = discord.Embed(
                        title="⚠️ RAID ALERT",
                        description=f"`{len(recent)}` members joined in the last `{RAID_WINDOW}s`. Possible raid in progress!",
                        color=COLOR_RED,
                        timestamp=datetime.utcnow()
                    )
                    await log_ch.send(embed=embed)

        # Auto-assign Fan role
        fan_role = discord.utils.get(member.guild.roles, name="Fan")
        if fan_role:
            try:
                await member.add_roles(fan_role)
            except discord.Forbidden:
                pass

        # Welcome embed
        ensure_user(member.id, member.display_name)
        welcome_ch = discord.utils.get(member.guild.text_channels, name="welcome")
        if not welcome_ch:
            welcome_ch = discord.utils.get(member.guild.text_channels, name="general")
        if welcome_ch:
            embed = discord.Embed(
                title=f"⚽ Welcome to World Cup Festival!",
                description=(
                    f"Welcome {member.mention} to the server! 🎉\n\n"
                    f"You've received the **Fan** role and **100 🪙 Fan Coins** to start!\n\n"
                    f"Get started:\n"
                    f"• `/worldcup` — Open the tournament hub\n"
                    f"• `/predict` — Predict match results for points\n"
                    f"• `/daily` — Claim daily coins\n"
                    f"• `/trivia` — Win coins with football trivia\n\n"
                    f"You are member **#{member.guild.member_count}** — let the games begin! ⚽"
                ),
                color=COLOR_GOLD,
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            from database import update_coins
            update_coins(member.id, 100)
            await welcome_ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Anti-spam
        user_id = message.author.id
        now = datetime.utcnow()
        _message_times[user_id].append(now)
        recent = [t for t in _message_times[user_id] if (now - t).total_seconds() < SPAM_WINDOW]
        _message_times[user_id] = recent

        if len(recent) >= SPAM_THRESHOLD:
            if user_id not in self.warned:
                self.warned.add(user_id)
                try:
                    await message.channel.send(
                        f"{message.author.mention} ⚠️ Slow down! You're sending messages too fast.",
                        delete_after=5
                    )
                    await message.delete()
                except (discord.Forbidden, discord.NotFound):
                    pass

                # Auto-timeout (10 min) if persistent
                if len(recent) >= SPAM_THRESHOLD * 2:
                    try:
                        await message.author.timeout(
                            timedelta(minutes=10),
                            reason="Auto-muted for spam"
                        )
                        config = get_server_config(message.guild.id)
                        if config and config.get("log_channel_id"):
                            log_ch = message.guild.get_channel(config["log_channel_id"])
                            if log_ch:
                                embed = discord.Embed(
                                    title="🔇 Auto-Timeout",
                                    description=f"{message.author.mention} was timed out for 10 minutes due to spam.",
                                    color=COLOR_RED,
                                    timestamp=datetime.utcnow()
                                )
                                await log_ch.send(embed=embed)
                    except discord.Forbidden:
                        pass
            return

        self.warned.discard(user_id)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        config = get_server_config(member.guild.id)
        if config and config.get("log_channel_id"):
            log_ch = member.guild.get_channel(config["log_channel_id"])
            if log_ch:
                embed = discord.Embed(
                    title="👋 Member Left",
                    description=f"**{member.display_name}** has left the server.",
                    color=COLOR_RED,
                    timestamp=datetime.utcnow()
                )
                await log_ch.send(embed=embed)

    @app_commands.command(name="setup_log", description="[Admin] Set the mod log channel")
    @app_commands.default_permissions(administrator=True)
    async def setup_log(self, interaction: discord.Interaction, channel: discord.TextChannel):
        set_server_config(interaction.guild_id, log_channel_id=channel.id)
        await interaction.response.send_message(f"✅ Mod logs will post in {channel.mention}.", ephemeral=True)

    @app_commands.command(name="kick", description="[Mod] Kick a member")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        try:
            await member.kick(reason=reason)
            await interaction.response.send_message(f"✅ Kicked **{member.display_name}** — {reason}", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to kick this member.", ephemeral=True)

    @app_commands.command(name="ban", description="[Mod] Ban a member")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        try:
            await member.ban(reason=reason)
            await interaction.response.send_message(f"✅ Banned **{member.display_name}** — {reason}", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to ban this member.", ephemeral=True)

    @app_commands.command(name="timeout", description="[Mod] Timeout a member")
    @app_commands.default_permissions(moderate_members=True)
    async def timeout_member(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason"):
        try:
            await member.timeout(timedelta(minutes=minutes), reason=reason)
            await interaction.response.send_message(
                f"✅ **{member.display_name}** timed out for {minutes} minutes — {reason}", ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to timeout this member.", ephemeral=True)

    @app_commands.command(name="purge", description="[Mod] Delete multiple messages")
    @app_commands.default_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: int):
        if amount < 1 or amount > 100:
            await interaction.response.send_message("Amount must be between 1 and 100.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"✅ Deleted {len(deleted)} messages.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
