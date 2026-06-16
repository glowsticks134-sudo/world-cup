import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import COLOR_GREEN, COLOR_GOLD, COLOR_RED, get_flag
from database import get_server_config
import football_api as api

# Track what we've already notified about
_notified_kickoff: set = set()
_notified_30min: set = set()
_notified_halftime: set = set()
_notified_fulltime: set = set()
_last_scores: dict = {}


class Notifications(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.notify_task.start()

    def cog_unload(self):
        self.notify_task.cancel()

    @tasks.loop(seconds=60)
    async def notify_task(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            await self._check_notifications(guild)

    @notify_task.before_loop
    async def before_notify(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(15)

    async def _check_notifications(self, guild: discord.Guild):
        config = get_server_config(guild.id)
        if not config or not config.get("notify_channel_id"):
            return

        channel = guild.get_channel(config["notify_channel_id"])
        if not channel:
            return

        try:
            live = await api.get_live_matches()
            upcoming = await api.get_upcoming_matches(1)
            now = datetime.utcnow()

            # Kickoff notifications (from scheduled to live)
            for m in live:
                mid = m["id"]
                status = m["status"]

                # Kickoff
                if status in ("IN_PLAY", "LIVE") and mid not in _notified_kickoff:
                    _notified_kickoff.add(mid)
                    hf = get_flag(m["home"])
                    af = get_flag(m["away"])
                    embed = discord.Embed(
                        title="⚽ KICKOFF!",
                        description=f"{hf} **{m['home']}** vs **{m['away']}** {af}\n\n🟢 The match has started!",
                        color=COLOR_GREEN,
                        timestamp=datetime.utcnow()
                    )
                    embed.set_footer(text="Use /predict to predict the result!")
                    await channel.send(embed=embed)

                # Halftime
                if status == "PAUSED" and mid not in _notified_halftime:
                    _notified_halftime.add(mid)
                    hf = get_flag(m["home"])
                    af = get_flag(m["away"])
                    hs = m["home_score"] if m["home_score"] is not None else 0
                    as_ = m["away_score"] if m["away_score"] is not None else 0
                    embed = discord.Embed(
                        title="🟡 HALFTIME!",
                        description=f"{hf} **{m['home']} {hs} - {as_} {m['away']}** {af}\n\n15-minute break. What a half!",
                        color=COLOR_GOLD,
                        timestamp=datetime.utcnow()
                    )
                    await channel.send(embed=embed)

                # Full time
                if status == "FINISHED" and mid not in _notified_fulltime:
                    _notified_fulltime.add(mid)
                    hf = get_flag(m["home"])
                    af = get_flag(m["away"])
                    hs = m["home_score"] if m["home_score"] is not None else 0
                    as_ = m["away_score"] if m["away_score"] is not None else 0
                    winner = m.get("winner")
                    if winner == "HOME_TEAM":
                        result = f"🏆 **{m['home']}** wins!"
                    elif winner == "AWAY_TEAM":
                        result = f"🏆 **{m['away']}** wins!"
                    else:
                        result = "🤝 It's a draw!"
                    embed = discord.Embed(
                        title="🏁 FULL TIME!",
                        description=f"{hf} **{m['home']} {hs} - {as_} {m['away']}** {af}\n\n{result}",
                        color=COLOR_RED,
                        timestamp=datetime.utcnow()
                    )
                    embed.set_footer(text="Predictions for this match will now be resolved!")
                    await channel.send(embed=embed)

                # Goal detection (score change)
                key = str(mid)
                hs = m["home_score"] if m["home_score"] is not None else 0
                as_ = m["away_score"] if m["away_score"] is not None else 0
                score_key = f"{hs}-{as_}"
                if key in _last_scores and _last_scores[key] != score_key and status in ("IN_PLAY", "LIVE"):
                    prev = _last_scores[key]
                    prev_hs, prev_as = map(int, prev.split("-"))
                    if hs > prev_hs:
                        scorer_team = m["home"]
                        scorer_flag = get_flag(m["home"])
                    else:
                        scorer_team = m["away"]
                        scorer_flag = get_flag(m["away"])

                    embed = discord.Embed(
                        title="⚽ GOAAAAL!",
                        description=f"{scorer_flag} **{scorer_team}** scores!\n\n"
                                    f"{get_flag(m['home'])} **{m['home']} {hs} - {as_} {m['away']}** {get_flag(m['away'])}\n"
                                    f"⏱️ {m.get('minute', '?')}'",
                        color=COLOR_GREEN,
                        timestamp=datetime.utcnow()
                    )
                    await channel.send(embed=embed)
                _last_scores[key] = score_key

            # 30-minute pre-match notifications
            for m in upcoming:
                mid = m["id"]
                dt = m.get("match_dt")
                if not dt:
                    continue
                diff = (dt - now).total_seconds()
                if 0 < diff <= 1800 and mid not in _notified_30min:
                    _notified_30min.add(mid)
                    hf = get_flag(m["home"])
                    af = get_flag(m["away"])
                    embed = discord.Embed(
                        title="⏰ Match Starting Soon!",
                        description=f"{hf} **{m['home']}** vs **{m['away']}** {af}\n\n"
                                    f"🕐 Kicks off in **30 minutes**!\n\n"
                                    f"Use `/predict` to place your prediction!",
                        color=COLOR_GOLD,
                        timestamp=datetime.utcnow()
                    )
                    await channel.send(embed=embed)

        except Exception as e:
            print(f"Notification error ({guild.name}): {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Notifications(bot))
