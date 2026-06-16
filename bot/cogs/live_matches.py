import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (
    COLOR_GREEN, COLOR_GOLD, COLOR_RED, COLOR_DARK,
    LIVE_MATCH_UPDATE_INTERVAL, NO_MATCH_UPDATE_INTERVAL, get_flag
)
from database import get_server_config, set_server_config
import football_api as api


def build_live_embed(matches: list, todays: list) -> discord.Embed:
    now = datetime.utcnow().strftime("%H:%M UTC")
    live = [m for m in matches if m["status"] in ("IN_PLAY", "LIVE", "PAUSED")]

    if live:
        embed = discord.Embed(
            title="⚽ LIVE WORLD CUP MATCHES",
            color=COLOR_GREEN,
            timestamp=datetime.utcnow()
        )
        embed.description = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for m in live:
            hf = get_flag(m["home"])
            af = get_flag(m["away"])
            hs = m["home_score"] if m["home_score"] is not None else 0
            as_ = m["away_score"] if m["away_score"] is not None else 0
            status = api.format_status(m)
            embed.description += f"\n{hf} **{m['home']}** `{hs} - {as_}` **{m['away']}** {af}\n"
            embed.description += f"  {status}\n"
            embed.description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        embed.set_footer(text=f"🏆 Match Center • Updates every 60s • {now}")
    else:
        embed = discord.Embed(
            title="⚽ WORLD CUP MATCH CENTER",
            color=COLOR_GOLD,
            timestamp=datetime.utcnow()
        )
        upcoming_today = [m for m in todays if m["status"] in ("SCHEDULED", "TIMED")]
        finished_today = [m for m in todays if m["status"] == "FINISHED"]

        if upcoming_today:
            val = ""
            for m in upcoming_today[:5]:
                hf = get_flag(m["home"])
                af = get_flag(m["away"])
                val += f"{hf} **{m['home']}** vs **{m['away']}** {af}\n"
                val += f"  🕐 {api.format_status(m)}\n\n"
            embed.add_field(name="📅 Today's Upcoming Matches", value=val.strip() or "None", inline=False)

        if finished_today:
            val = ""
            for m in finished_today[:5]:
                hf = get_flag(m["home"])
                af = get_flag(m["away"])
                hs = m["home_score"] if m["home_score"] is not None else 0
                as_ = m["away_score"] if m["away_score"] is not None else 0
                val += f"{hf} **{m['home']}** `{hs} - {as_}` **{m['away']}** {af} ✅\n"
            embed.add_field(name="✅ Today's Results", value=val.strip() or "None", inline=False)

        if not upcoming_today and not finished_today:
            embed.description = "No matches scheduled today. Check back soon!\n\nUse `/schedule` to see upcoming fixtures."

        embed.set_footer(text=f"🏆 Match Center • Updates every 5m (no live matches) • {now}")

    return embed


class LiveMatches(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.update_task.start()

    def cog_unload(self):
        self.update_task.cancel()

    @tasks.loop(seconds=LIVE_MATCH_UPDATE_INTERVAL)
    async def update_task(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            await self._update_guild(guild)

    async def _update_guild(self, guild: discord.Guild):
        config = get_server_config(guild.id)
        if not config or not config.get("live_channel_id"):
            return

        channel = guild.get_channel(config["live_channel_id"])
        if not channel:
            return

        try:
            live = await api.get_live_matches()
            todays = await api.get_todays_matches()

            # Adjust loop interval based on live matches
            if live:
                self.update_task.change_interval(seconds=LIVE_MATCH_UPDATE_INTERVAL)
            else:
                self.update_task.change_interval(seconds=NO_MATCH_UPDATE_INTERVAL)

            embed = build_live_embed(live, todays)

            msg_id = config.get("live_message_id")
            if msg_id:
                try:
                    msg = await channel.fetch_message(msg_id)
                    await msg.edit(embed=embed)
                    return
                except discord.NotFound:
                    pass

            msg = await channel.send(embed=embed)
            set_server_config(guild.id, live_message_id=msg.id)
        except Exception as e:
            print(f"Live update error ({guild.name}): {e}")

    @update_task.before_loop
    async def before_update(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(5)

    @app_commands.command(name="live", description="Show current live World Cup matches")
    async def live_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        live = await api.get_live_matches()
        todays = await api.get_todays_matches()
        embed = build_live_embed(live, todays)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="schedule", description="Show upcoming World Cup fixtures")
    async def schedule(self, interaction: discord.Interaction):
        await interaction.response.defer()
        matches = await api.get_upcoming_matches(days=7)
        embed = discord.Embed(title="📅 Upcoming World Cup Fixtures", color=COLOR_GOLD, timestamp=datetime.utcnow())

        if not matches:
            embed.description = "No upcoming fixtures found. The tournament may be between stages."
        else:
            by_date: dict = {}
            for m in matches[:15]:
                dt = m.get("match_dt")
                key = dt.strftime("%A, %d %B") if dt else "TBD"
                by_date.setdefault(key, []).append(m)

            for date_label, ms in list(by_date.items())[:5]:
                val = ""
                for m in ms:
                    hf = get_flag(m["home"])
                    af = get_flag(m["away"])
                    t = m["match_dt"].strftime("%H:%M UTC") if m.get("match_dt") else "TBD"
                    val += f"{hf} {m['home']} vs {m['away']} {af} — `{t}`\n"
                embed.add_field(name=date_label, value=val.strip(), inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="setup_live", description="[Admin] Set the live match channel")
    @app_commands.default_permissions(administrator=True)
    async def setup_live(self, interaction: discord.Interaction, channel: discord.TextChannel):
        set_server_config(interaction.guild_id, live_channel_id=channel.id)
        await interaction.response.send_message(
            f"✅ Live match updates will post in {channel.mention} every 60 seconds.", ephemeral=True
        )
        await self._update_guild(interaction.guild)

    @app_commands.command(name="setup_notifications", description="[Admin] Set match notification channel")
    @app_commands.default_permissions(administrator=True)
    async def setup_notifications(self, interaction: discord.Interaction, channel: discord.TextChannel):
        set_server_config(interaction.guild_id, notify_channel_id=channel.id)
        await interaction.response.send_message(
            f"✅ Match notifications will be sent to {channel.mention}.", ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(LiveMatches(bot))
