import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import COLOR_GOLD, COLOR_GREEN, get_flag
from database import get_server_config, set_server_config
import football_api as api


def build_standings_embed(groups: list) -> discord.Embed:
    embed = discord.Embed(
        title="🏆 World Cup Group Standings",
        color=COLOR_GOLD,
        timestamp=datetime.utcnow()
    )
    if not groups:
        embed.description = "Standings not yet available. Check back during the tournament!"
        return embed

    for group in groups[:8]:
        name = group["group"]
        table = group["table"]
        val = "```\n"
        val += f"{'#':<3} {'Team':<18} {'P':<3} {'W':<3} {'D':<3} {'L':<3} {'GD':<5} {'Pts'}\n"
        val += "─" * 42 + "\n"
        for t in table[:4]:
            gd = f"+{t['gd']}" if t["gd"] > 0 else str(t["gd"])
            val += f"{t['position']:<3} {t['team'][:17]:<18} {t['played']:<3} {t['won']:<3} {t['draw']:<3} {t['lost']:<3} {gd:<5} {t['points']}\n"
        val += "```"
        embed.add_field(name=f"📊 {name}", value=val, inline=False)

    embed.set_footer(text="Updates every 10 minutes")
    return embed


def build_scorers_embed(scorers: list) -> discord.Embed:
    embed = discord.Embed(
        title="⚽ Top Scorers",
        color=COLOR_GOLD,
        timestamp=datetime.utcnow()
    )
    if not scorers:
        embed.description = "No scorer data available yet."
        return embed

    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    desc = ""
    for i, s in enumerate(scorers[:10]):
        m = medals[i] if i < len(medals) else "  "
        tf = get_flag(s["team"])
        desc += f"{m} **{s['player']}** {tf} {s['team']}\n   ⚽ `{s['goals']} goals`"
        if s.get("assists"):
            desc += f" • 🎯 `{s['assists']} assists`"
        desc += "\n"
    embed.description = desc
    return embed


class Standings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.update_task.start()

    def cog_unload(self):
        self.update_task.cancel()

    @tasks.loop(minutes=10)
    async def update_task(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            config = get_server_config(guild.id)
            if not config or not config.get("bracket_channel_id"):
                continue
            channel = guild.get_channel(config["bracket_channel_id"])
            if not channel:
                continue
            try:
                groups = await api.get_standings()
                scorers = await api.get_scorers()
                embed1 = build_standings_embed(groups)
                embed2 = build_scorers_embed(scorers)

                msg_id = config.get("bracket_message_id")
                if msg_id:
                    try:
                        msg = await channel.fetch_message(msg_id)
                        await msg.edit(embeds=[embed1, embed2])
                        continue
                    except discord.NotFound:
                        pass
                msg = await channel.send(embeds=[embed1, embed2])
                set_server_config(guild.id, bracket_message_id=msg.id)
            except Exception as e:
                print(f"Standings update error: {e}")

    @update_task.before_loop
    async def before_update(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(20)

    @app_commands.command(name="standings", description="View World Cup group standings")
    async def standings_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        groups = await api.get_standings()
        embed = build_standings_embed(groups)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="scorers", description="View World Cup top scorers")
    async def scorers_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        scorers = await api.get_scorers()
        embed = build_scorers_embed(scorers)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="setup_bracket", description="[Admin] Set the tournament tracker channel")
    @app_commands.default_permissions(administrator=True)
    async def setup_bracket(self, interaction: discord.Interaction, channel: discord.TextChannel):
        set_server_config(interaction.guild_id, bracket_channel_id=channel.id)
        await interaction.response.send_message(f"✅ Tournament tracker will auto-update in {channel.mention}.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Standings(bot))
