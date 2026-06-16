import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import COLOR_GOLD, COLOR_GREEN, COLOR_DARK, get_flag, ACHIEVEMENTS
from database import (
    ensure_user, get_user, get_user_achievements, get_leaderboard,
    get_server_stats, update_coins, grant_achievement
)
import football_api as api


WORLD_CUP_2026_DATE = datetime(2026, 6, 11, 18, 0, 0)


class WorldCupHubView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.select(
        placeholder="⚽ Explore World Cup...",
        options=[
            discord.SelectOption(label="📅 Schedule", value="schedule", description="View upcoming matches", emoji="📅"),
            discord.SelectOption(label="🏆 Standings", value="standings", description="Group stage standings", emoji="🏆"),
            discord.SelectOption(label="⚽ Top Scorers", value="scorers", description="Tournament top scorers", emoji="⚽"),
            discord.SelectOption(label="📊 Server Stats", value="stats", description="Server participation stats", emoji="📊"),
            discord.SelectOption(label="🏅 My Profile", value="profile", description="Your points, coins & achievements", emoji="🏅"),
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        choice = select.values[0]
        await interaction.response.defer()

        if choice == "schedule":
            matches = await api.get_upcoming_matches(7)
            todays = await api.get_todays_matches()
            all_m = todays + [m for m in matches if m["id"] not in {x["id"] for x in todays}]
            embed = discord.Embed(title="📅 World Cup Fixtures", color=COLOR_GOLD, timestamp=datetime.utcnow())
            if not all_m:
                embed.description = "No upcoming fixtures found."
            else:
                for m in all_m[:10]:
                    hf = get_flag(m["home"])
                    af = get_flag(m["away"])
                    status = api.format_status(m)
                    embed.add_field(
                        name=f"{hf} {m['home']} vs {m['away']} {af}",
                        value=status, inline=False
                    )

        elif choice == "standings":
            groups = await api.get_standings()
            embed = discord.Embed(title="🏆 Group Standings", color=COLOR_GOLD, timestamp=datetime.utcnow())
            if not groups:
                embed.description = "Standings not available yet."
            else:
                for g in groups[:4]:
                    val = "\n".join(
                        f"`{t['position']}. {t['team'][:15]:<15} {t['points']}pts`"
                        for t in g["table"][:4]
                    )
                    embed.add_field(name=f"📊 {g['group']}", value=val, inline=True)

        elif choice == "scorers":
            scorers = await api.get_scorers()
            embed = discord.Embed(title="⚽ Top Scorers", color=COLOR_GOLD, timestamp=datetime.utcnow())
            medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
            desc = ""
            for i, s in enumerate(scorers[:8]):
                desc += f"{medals[i]} **{s['player']}** — ⚽ {s['goals']} goals\n"
            embed.description = desc or "No data available."

        elif choice == "stats":
            stats = get_server_stats()
            embed = discord.Embed(title="📊 Server Statistics", color=COLOR_GOLD, timestamp=datetime.utcnow())
            embed.add_field(name="🎯 Predictions", value=f"`{stats['total_predictions']:,}`", inline=True)
            embed.add_field(name="👥 Participants", value=f"`{stats['total_users']:,}`", inline=True)
            embed.add_field(name="🪙 Coins Earned", value=f"`{stats['total_coins']:,}`", inline=True)
            embed.add_field(name="📅 Active Today", value=f"`{stats['active_today']:,}`", inline=True)
            embed.add_field(name="✅ Completion", value=f"`{stats['completion_rate']}%`", inline=True)

        elif choice == "profile":
            ensure_user(interaction.user.id, interaction.user.display_name)
            user = get_user(interaction.user.id)
            achs = get_user_achievements(interaction.user.id)
            top = get_leaderboard(100)
            rank = next((i + 1 for i, u in enumerate(top) if u["user_id"] == interaction.user.id), None)

            embed = discord.Embed(
                title=f"🏅 {interaction.user.display_name}'s Profile",
                color=COLOR_GOLD,
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.add_field(name="🏆 Points", value=f"`{user['points']:,}`", inline=True)
            embed.add_field(name="💰 Fan Coins", value=f"`{user['coins']:,}`", inline=True)
            embed.add_field(name="🎖️ Rank", value=f"`#{rank}`" if rank else "`-`", inline=True)
            embed.add_field(name="🔥 Streak", value=f"`{user['streak']} days`", inline=True)

            ach_text = " ".join(
                ACHIEVEMENTS[k]["icon"] + " " + ACHIEVEMENTS[k]["name"]
                for k in achs if k in ACHIEVEMENTS
            ) or "No achievements yet"
            embed.add_field(name="🏅 Achievements", value=ach_text, inline=False)
        else:
            embed = discord.Embed(title="World Cup Hub", color=COLOR_GOLD)

        await interaction.edit_original_response(embed=embed)


class WorldCupHub(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="worldcup", description="Open the World Cup Festival hub dashboard")
    async def worldcup(self, interaction: discord.Interaction):
        ensure_user(interaction.user.id, interaction.user.display_name)

        now = datetime.utcnow()
        delta = WORLD_CUP_2026_DATE - now
        if delta.total_seconds() > 0:
            days = delta.days
            hours = delta.seconds // 3600
            countdown = f"⏳ **{days} days, {hours} hours** until kick-off!"
        else:
            countdown = "⚽ The World Cup is happening **RIGHT NOW**!"

        live = await api.get_live_matches()
        live_count = len([m for m in live if m["status"] in ("IN_PLAY", "LIVE", "PAUSED")])

        embed = discord.Embed(
            title="⚽ World Cup Festival — Dashboard",
            description=(
                f"Welcome to the **World Cup Festival** — your ultimate World Cup experience!\n\n"
                f"🌍 **FIFA World Cup 2026** — USA · Canada · Mexico\n"
                f"{countdown}\n\n"
                f"{'🟢 **' + str(live_count) + ' matches LIVE now!**' if live_count else '📅 No live matches right now'}\n\n"
                f"Use the menu below to explore the tournament, check standings, view your profile, and more!"
            ),
            color=COLOR_GOLD,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="⚡ Quick Commands", value=(
            "`/predict` — Predict match results\n"
            "`/daily` — Claim daily coins\n"
            "`/trivia` — Win coins with trivia\n"
            "`/balance` — Check your coins\n"
            "`/leaderboard` — Top predictors"
        ), inline=True)
        embed.add_field(name="🏆 Live Features", value=(
            "`/live` — Live match scores\n"
            "`/schedule` — Upcoming fixtures\n"
            "`/standings` — Group tables\n"
            "`/scorers` — Top scorers\n"
            "`/shop` — Fan Coin shop"
        ), inline=True)
        embed.set_footer(text="World Cup Festival Bot • Use /help for all commands")

        view = WorldCupHubView()
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="achievements", description="View your achievement badges")
    async def achievements(self, interaction: discord.Interaction):
        ensure_user(interaction.user.id, interaction.user.display_name)
        achs = get_user_achievements(interaction.user.id)

        embed = discord.Embed(
            title=f"🏅 {interaction.user.display_name}'s Achievements",
            color=COLOR_GOLD,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        earned_text = ""
        locked_text = ""
        for key, ach in ACHIEVEMENTS.items():
            if key in achs:
                earned_text += f"{ach['icon']} **{ach['name']}** — {ach['desc']}\n"
            else:
                locked_text += f"🔒 ~~{ach['name']}~~ — {ach['desc']}\n"

        embed.add_field(name="✅ Earned", value=earned_text or "None yet!", inline=False)
        embed.add_field(name="🔒 Locked", value=locked_text or "All unlocked! Amazing!", inline=False)
        embed.set_footer(text=f"{len(achs)}/{len(ACHIEVEMENTS)} achievements earned")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="help", description="Show all World Cup Festival commands")
    async def help_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚽ World Cup Festival — All Commands",
            color=COLOR_GOLD,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="⚽ Match Info", value=(
            "`/worldcup` — Main hub dashboard\n"
            "`/live` — Live match scores\n"
            "`/schedule` — Upcoming fixtures\n"
            "`/standings` — Group standings\n"
            "`/scorers` — Top scorers\n"
        ), inline=False)
        embed.add_field(name="🎯 Predictions", value=(
            "`/predict` — Predict match winner\n"
            "`/mypredictions` — Your prediction history\n"
            "`/leaderboard` — Top predictors\n"
            "`/mypoints` — Your stats & rank\n"
        ), inline=False)
        embed.add_field(name="💰 Economy", value=(
            "`/balance` — Your coin balance\n"
            "`/daily` — Claim daily coins\n"
            "`/transfer` — Send coins to a member\n"
            "`/shop` — Buy items with coins\n"
            "`/richlist` — Top coin holders\n"
        ), inline=False)
        embed.add_field(name="🎮 Games & Events", value=(
            "`/trivia` — Football trivia for coins\n"
            "`/achievements` — Your badges\n"
        ), inline=False)
        embed.add_field(name="🛠️ Admin", value=(
            "`/setup_live` — Set live match channel\n"
            "`/setup_leaderboard` — Set leaderboard channel\n"
            "`/setup_stats` — Set stats channel\n"
            "`/setup_bracket` — Set tournament tracker\n"
            "`/setup_notifications` — Set notification channel\n"
            "`/giveaway` — Start a giveaway\n"
            "`/admin_coins` — Add/remove coins\n"
            "`/event` — Start/stop hype events\n"
        ), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(WorldCupHub(bot))
