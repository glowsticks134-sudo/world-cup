import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import COLOR_GOLD, COLOR_GREEN, COLOR_RED, COLOR_DARK, get_flag, PREDICTION_CORRECT_COINS, PREDICTION_BONUS_EXACT_SCORE
from database import (
    ensure_user, get_user, save_prediction, get_user_predictions,
    get_leaderboard, update_coins, update_points, grant_achievement, get_user_achievements
)
import football_api as api


class PredictMatchSelect(discord.ui.Select):
    def __init__(self, matches: list):
        self.matches_data = {str(m["id"]): m for m in matches}
        options = []
        for m in matches[:25]:
            hf = get_flag(m["home"])
            af = get_flag(m["away"])
            label = f"{m['home']} vs {m['away']}"
            desc = api.format_status(m)
            options.append(discord.SelectOption(label=label[:100], value=str(m["id"]), description=desc[:100], emoji="⚽"))
        super().__init__(placeholder="Select a match to predict...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        match_id = int(self.values[0])
        match = self.matches_data[self.values[0]]
        view = PredictWinnerView(match)
        embed = discord.Embed(
            title=f"🎯 Predict: {match['home']} vs {match['away']}",
            description=f"{get_flag(match['home'])} **{match['home']}** vs **{match['away']}** {get_flag(match['away'])}\n\nWho will win?",
            color=COLOR_GOLD
        )
        embed.set_footer(text="Correct prediction = 200 coins + 100 points | Exact score = 500 bonus coins!")
        await interaction.response.edit_message(embed=embed, view=view)


class PredictWinnerView(discord.ui.View):
    def __init__(self, match: dict):
        super().__init__(timeout=120)
        self.match = match
        self.add_item(PredictButton(match["home"], "HOME", discord.ButtonStyle.primary))
        self.add_item(PredictButton("Draw", "DRAW", discord.ButtonStyle.secondary))
        self.add_item(PredictButton(match["away"], "AWAY", discord.ButtonStyle.danger))


class PredictButton(discord.ui.Button):
    def __init__(self, label: str, value: str, style: discord.ButtonStyle):
        super().__init__(label=f"{get_flag(label)} {label}" if value != "DRAW" else "🤝 Draw", style=style)
        self.value = value
        self.winner_label = label

    async def callback(self, interaction: discord.Interaction):
        view: PredictWinnerView = self.view
        match = view.match
        ensure_user(interaction.user.id, interaction.user.display_name)

        result = save_prediction(
            interaction.user.id, match["id"],
            match["home"], match["away"], self.winner_label
        )

        achs = get_user_achievements(interaction.user.id)
        if "first_prediction" not in achs:
            earned = grant_achievement(interaction.user.id, "first_prediction")
            if earned:
                update_coins(interaction.user.id, 50)

        embed = discord.Embed(
            title="✅ Prediction Saved!",
            description=f"You predicted **{get_flag(self.winner_label)} {self.winner_label}** to win!\n\n"
                        f"{get_flag(match['home'])} {match['home']} vs {match['away']} {get_flag(match['away'])}",
            color=COLOR_GREEN,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="Points awarded when the match finishes.")
        await interaction.response.edit_message(embed=embed, view=None)


class Predictions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="predict", description="Predict the winner of an upcoming World Cup match")
    async def predict(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ensure_user(interaction.user.id, interaction.user.display_name)

        matches = await api.get_upcoming_matches(days=5)
        todays = await api.get_todays_matches()
        all_matches = todays + [m for m in matches if m["id"] not in {x["id"] for x in todays}]
        predictable = [m for m in all_matches if m["status"] in ("SCHEDULED", "TIMED", "IN_PLAY", "LIVE")]

        if not predictable:
            # Use mock for demo
            predictable = api.MOCK_MATCHES

        embed = discord.Embed(
            title="🎯 World Cup Predictions",
            description="Select a match below to place your prediction.\n\n✅ **Correct winner** = 200 coins + 100 points\n⭐ **Exact scoreline** = Extra 500 bonus coins!",
            color=COLOR_GOLD
        )

        view = discord.ui.View(timeout=120)
        view.add_item(PredictMatchSelect(predictable[:25]))
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="mypredictions", description="View your prediction history")
    async def mypredictions(self, interaction: discord.Interaction):
        ensure_user(interaction.user.id, interaction.user.display_name)
        preds = get_user_predictions(interaction.user.id)

        embed = discord.Embed(
            title=f"🎯 {interaction.user.display_name}'s Predictions",
            color=COLOR_GOLD,
            timestamp=datetime.utcnow()
        )

        if not preds:
            embed.description = "You haven't made any predictions yet!\nUse `/predict` to get started."
        else:
            desc = ""
            for p in preds[:10]:
                resolved = p["resolved"]
                icon = "✅" if resolved and p["points_awarded"] > 0 else ("❌" if resolved else "⏳")
                hf = get_flag(p["home_team"])
                af = get_flag(p["away_team"])
                desc += f"{icon} {hf} {p['home_team']} vs {p['away_team']} {af}\n"
                desc += f"   Your pick: **{p['predicted_winner']}**"
                if resolved:
                    desc += f" | Result: **{p.get('actual_winner','?')}** | `+{p['points_awarded']}pts`"
                desc += "\n\n"
            embed.description = desc.strip()

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="leaderboard", description="View the World Cup prediction leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        top = get_leaderboard(10)
        medals = ["🥇", "🥈", "🥉", "🏅", "🏅", "🏅", "🏅", "🏅", "🏅", "🏅"]

        embed = discord.Embed(
            title="🏆 World Cup Prediction Leaderboard",
            color=COLOR_GOLD,
            timestamp=datetime.utcnow()
        )

        if not top:
            embed.description = "No predictions made yet. Be the first with `/predict`!"
        else:
            desc = "```\n"
            desc += f"{'Rank':<5} {'Player':<20} {'Points':<10} {'Coins':<10}\n"
            desc += "─" * 47 + "\n"
            for i, u in enumerate(top):
                medal = medals[i] if i < len(medals) else "  "
                desc += f"{medal:<6} {u['username'][:18]:<20} {u['points']:<10} {u['coins']:<10}\n"
            desc += "```"
            embed.description = desc

        embed.set_footer(text="Earn points by predicting match results correctly!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="mypoints", description="Check your prediction points and rank")
    async def mypoints(self, interaction: discord.Interaction):
        ensure_user(interaction.user.id, interaction.user.display_name)
        user = get_user(interaction.user.id)
        top = get_leaderboard(100)
        rank = next((i + 1 for i, u in enumerate(top) if u["user_id"] == interaction.user.id), None)
        preds = get_user_predictions(interaction.user.id)
        correct = sum(1 for p in preds if p["resolved"] and p["points_awarded"] > 0)

        embed = discord.Embed(
            title=f"📊 {interaction.user.display_name}'s Stats",
            color=COLOR_GOLD,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="🏆 Points", value=f"`{user['points']}`", inline=True)
        embed.add_field(name="💰 Fan Coins", value=f"`{user['coins']}`", inline=True)
        embed.add_field(name="🎖️ Rank", value=f"`#{rank}`" if rank else "`Unranked`", inline=True)
        embed.add_field(name="🎯 Predictions", value=f"`{len(preds)}`", inline=True)
        embed.add_field(name="✅ Correct", value=f"`{correct}`", inline=True)
        embed.add_field(name="🔥 Streak", value=f"`{user['streak']} days`", inline=True)

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Predictions(bot))
