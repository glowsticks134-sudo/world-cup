import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import COLOR_GOLD, COLOR_GREEN, COLOR_RED, TRIVIA_COINS, ACHIEVEMENTS
from database import ensure_user, update_coins, log_trivia, grant_achievement, get_user_achievements, get_user
from trivia import get_random_question, check_answer

TRIVIA_TIMEOUT = 20  # seconds


class TriviaView(discord.ui.View):
    def __init__(self, question_data: dict, user_id: int):
        super().__init__(timeout=TRIVIA_TIMEOUT)
        self.question_data = question_data
        self.user_id = user_id
        self.answered = False

        for choice in question_data["choices"]:
            btn = discord.ui.Button(label=choice, style=discord.ButtonStyle.secondary)
            btn.callback = self.make_callback(choice)
            self.add_item(btn)

    def make_callback(self, choice: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("This trivia isn't for you!", ephemeral=True)
                return
            if self.answered:
                await interaction.response.send_message("Already answered!", ephemeral=True)
                return

            self.answered = True
            self.stop()
            correct = check_answer(self.question_data, choice)

            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True
                    if check_answer(self.question_data, item.label):
                        item.style = discord.ButtonStyle.success
                    elif item.label == choice and not correct:
                        item.style = discord.ButtonStyle.danger

            if correct:
                coins = TRIVIA_COINS
                update_coins(interaction.user.id, coins)
                log_trivia(interaction.user.id, True, coins)

                # Achievement check
                user = get_user(interaction.user.id)
                achs = get_user_achievements(interaction.user.id)
                if "trivia_10" not in achs:
                    from database import get_connection
                    conn = get_connection()
                    count = conn.execute("SELECT COUNT(*) FROM trivia_history WHERE user_id=? AND correct=1", (interaction.user.id,)).fetchone()[0]
                    conn.close()
                    if count >= 10:
                        if grant_achievement(interaction.user.id, "trivia_10"):
                            update_coins(interaction.user.id, ACHIEVEMENTS["trivia_10"]["coins"])

                embed = discord.Embed(
                    title="✅ Correct!",
                    description=f"**{choice}** is right!\n\n+**{coins} 🪙 Fan Coins** added to your balance!",
                    color=COLOR_GREEN
                )
            else:
                log_trivia(interaction.user.id, False, 0)
                correct_answer = self.question_data["correct_display"]
                embed = discord.Embed(
                    title="❌ Wrong!",
                    description=f"You chose **{choice}**.\nThe correct answer was **{correct_answer}**.\n\nBetter luck next time!",
                    color=COLOR_RED
                )

            await interaction.response.edit_message(embed=embed, view=self)

        return callback

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
                if check_answer(self.question_data, item.label):
                    item.style = discord.ButtonStyle.success


class Trivia(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_sessions: set = set()

    @app_commands.command(name="trivia", description="Answer a football trivia question and win coins!")
    async def trivia(self, interaction: discord.Interaction):
        ensure_user(interaction.user.id, interaction.user.display_name)

        if interaction.user.id in self.active_sessions:
            await interaction.response.send_message("You already have an active trivia session!", ephemeral=True)
            return

        self.active_sessions.add(interaction.user.id)
        q = get_random_question()

        embed = discord.Embed(
            title="🎯 Football Trivia!",
            description=f"**{q['question']}**\n\n⏰ You have **{TRIVIA_TIMEOUT} seconds** to answer!\n💰 Correct = **{TRIVIA_COINS} Fan Coins**",
            color=COLOR_GOLD,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="Select your answer below")

        view = TriviaView(q, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        await asyncio.sleep(TRIVIA_TIMEOUT + 1)
        self.active_sessions.discard(interaction.user.id)

        if not view.answered:
            timeout_embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"The correct answer was **{q['correct_display']}**.\n\nUse `/trivia` again to try another question!",
                color=COLOR_RED
            )
            try:
                await interaction.edit_original_response(embed=timeout_embed, view=view)
            except Exception:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Trivia(bot))
