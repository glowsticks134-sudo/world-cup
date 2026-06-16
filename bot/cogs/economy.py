import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (
    COLOR_GOLD, COLOR_GREEN, COLOR_RED, DAILY_COINS, ACTIVITY_COINS,
    get_flag, ACHIEVEMENTS
)
from database import (
    ensure_user, get_user, update_coins, claim_daily,
    get_coin_leaderboard, grant_achievement, get_user_achievements, get_server_stats
)


SHOP_ITEMS = [
    {"id": "role_fan", "name": "Fan Role", "desc": "Get the ⭐ Fan role", "cost": 100, "emoji": "⭐"},
    {"id": "role_super", "name": "Super Fan Role", "desc": "Get the 🔥 Super Fan role", "cost": 500, "emoji": "🔥"},
    {"id": "vip_frame", "name": "VIP Profile Frame", "desc": "Show off your VIP status (cosmetic)", "cost": 750, "emoji": "💎"},
    {"id": "lucky_dip", "name": "Lucky Dip", "desc": "Win 0–500 random coins!", "cost": 200, "emoji": "🎲"},
    {"id": "double_daily", "name": "Daily Booster", "desc": "2x daily coins for 1 day", "cost": 300, "emoji": "⚡"},
]


class ShopView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        options = [
            discord.SelectOption(
                label=f"{item['name']} — {item['cost']} 🪙",
                value=item["id"],
                description=item["desc"],
                emoji=item["emoji"]
            )
            for item in SHOP_ITEMS
        ]
        select = discord.ui.Select(placeholder="Choose an item to buy...", options=options)
        select.callback = self.buy_callback
        self.add_item(select)

    async def buy_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This shop menu isn't yours!", ephemeral=True)
            return

        item_id = interaction.data["values"][0]
        item = next((i for i in SHOP_ITEMS if i["id"] == item_id), None)
        if not item:
            await interaction.response.send_message("Item not found.", ephemeral=True)
            return

        user = get_user(interaction.user.id)
        if user["coins"] < item["cost"]:
            embed = discord.Embed(
                title="❌ Insufficient Coins",
                description=f"You need **{item['cost']} 🪙** but only have **{user['coins']} 🪙**.\n\nEarn more with `/daily`, trivia, and predictions!",
                color=COLOR_RED
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        update_coins(interaction.user.id, -item["cost"])

        if item["id"] == "lucky_dip":
            import random
            won = random.randint(0, 500)
            update_coins(interaction.user.id, won)
            result_text = f"🎲 You won **{won} coins** from the lucky dip!"
        elif item["id"] in ("role_fan", "role_super"):
            role_name = "Fan" if item["id"] == "role_fan" else "Super Fan"
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if role:
                try:
                    await interaction.user.add_roles(role)
                    result_text = f"✅ You now have the **{role_name}** role!"
                except discord.Forbidden:
                    result_text = "⚠️ I couldn't assign the role (missing permissions)."
            else:
                result_text = f"⚠️ The **{role_name}** role doesn't exist yet. Ask an admin to create it."
        else:
            result_text = f"✅ You purchased **{item['name']}**!"

        embed = discord.Embed(
            title=f"{item['emoji']} Purchase Successful!",
            description=f"**{item['name']}** — -{item['cost']} 🪙\n\n{result_text}",
            color=COLOR_GREEN,
            timestamp=datetime.utcnow()
        )
        new_user = get_user(interaction.user.id)
        embed.set_footer(text=f"New balance: {new_user['coins']} coins")
        await interaction.response.edit_message(embed=embed, view=None)


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Check your Fan Coin balance")
    async def balance(self, interaction: discord.Interaction):
        ensure_user(interaction.user.id, interaction.user.display_name)
        user = get_user(interaction.user.id)

        embed = discord.Embed(
            title=f"💰 {interaction.user.display_name}'s Wallet",
            color=COLOR_GOLD,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="🪙 Fan Coins", value=f"`{user['coins']:,}`", inline=True)
        embed.add_field(name="📈 Total Earned", value=f"`{user['total_coins']:,}`", inline=True)
        embed.add_field(name="🏆 Points", value=f"`{user['points']:,}`", inline=True)
        embed.add_field(name="🔥 Daily Streak", value=f"`{user['streak']} days`", inline=True)
        embed.set_footer(text="Earn coins with /daily, /trivia, and /predict!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="daily", description="Claim your daily Fan Coins")
    async def daily(self, interaction: discord.Interaction):
        ensure_user(interaction.user.id, interaction.user.display_name)
        user = get_user(interaction.user.id)
        streak = (user["streak"] or 0) + 1
        bonus = min(streak * 10, 200)
        total = DAILY_COINS + bonus

        success = claim_daily(interaction.user.id, total)

        if not success:
            embed = discord.Embed(
                title="⏰ Already Claimed!",
                description=f"You already claimed your daily coins today.\nCome back tomorrow to keep your **{user['streak']}-day streak**!",
                color=COLOR_RED
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Achievement: 7-day streak
        if streak >= 7:
            earned = grant_achievement(interaction.user.id, "streak_7")
            if earned:
                update_coins(interaction.user.id, ACHIEVEMENTS["streak_7"]["coins"])

        embed = discord.Embed(
            title="✅ Daily Coins Claimed!",
            description=f"You received **{total} 🪙 Fan Coins**!\n\n"
                        f"Base: `{DAILY_COINS}` + Streak Bonus: `{bonus}` (Day {streak})\n\n"
                        f"🔥 Keep your streak going — come back tomorrow!",
            color=COLOR_GREEN,
            timestamp=datetime.utcnow()
        )
        new_user = get_user(interaction.user.id)
        embed.set_footer(text=f"Total coins: {new_user['coins']:,} | Streak: {streak} days")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="transfer", description="Transfer Fan Coins to another member")
    async def transfer(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount <= 0:
            await interaction.response.send_message("Amount must be positive!", ephemeral=True)
            return
        if member.id == interaction.user.id:
            await interaction.response.send_message("You can't transfer coins to yourself!", ephemeral=True)
            return
        if member.bot:
            await interaction.response.send_message("You can't transfer coins to a bot!", ephemeral=True)
            return

        ensure_user(interaction.user.id, interaction.user.display_name)
        ensure_user(member.id, member.display_name)
        user = get_user(interaction.user.id)

        if user["coins"] < amount:
            embed = discord.Embed(
                title="❌ Insufficient Coins",
                description=f"You only have **{user['coins']} 🪙** but tried to send **{amount} 🪙**.",
                color=COLOR_RED
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        update_coins(interaction.user.id, -amount)
        update_coins(member.id, amount)

        achs = get_user_achievements(interaction.user.id)
        if "transfer" not in achs:
            grant_achievement(interaction.user.id, "transfer")

        embed = discord.Embed(
            title="✅ Transfer Complete!",
            description=f"You sent **{amount} 🪙** to {member.mention}!",
            color=COLOR_GREEN,
            timestamp=datetime.utcnow()
        )
        new_user = get_user(interaction.user.id)
        embed.set_footer(text=f"Your new balance: {new_user['coins']:,} coins")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shop", description="Browse the Fan Coin shop")
    async def shop(self, interaction: discord.Interaction):
        ensure_user(interaction.user.id, interaction.user.display_name)
        user = get_user(interaction.user.id)

        embed = discord.Embed(
            title="🛒 Fan Coin Shop",
            description=f"Your balance: **{user['coins']:,} 🪙**\n\nSelect an item below to purchase:",
            color=COLOR_GOLD,
            timestamp=datetime.utcnow()
        )
        for item in SHOP_ITEMS:
            embed.add_field(
                name=f"{item['emoji']} {item['name']} — {item['cost']} 🪙",
                value=item["desc"],
                inline=False
            )
        embed.set_footer(text="Earn coins with /daily, /trivia, predictions, and events!")

        view = ShopView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="richlist", description="Top Fan Coin holders")
    async def richlist(self, interaction: discord.Interaction):
        top = get_coin_leaderboard(10)
        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7

        embed = discord.Embed(title="💰 Fan Coin Rich List", color=COLOR_GOLD, timestamp=datetime.utcnow())
        desc = ""
        for i, u in enumerate(top):
            desc += f"{medals[i]} **{u['username']}** — `{u['coins']:,}` 🪙  *(Total earned: {u['total_coins']:,})*\n"
        embed.description = desc or "No data yet!"
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))
