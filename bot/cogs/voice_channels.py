import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import COLOR_GOLD, get_flag
import football_api as api


class VoiceChannels(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rename_task.start()

    def cog_unload(self):
        self.rename_task.cancel()

    @tasks.loop(minutes=2)
    async def rename_task(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            await self._update_voice_channels(guild)

    @rename_task.before_loop
    async def before_rename(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(30)

    async def _update_voice_channels(self, guild: discord.Guild):
        try:
            live = await api.get_live_matches()
            live_matches = [m for m in live if m["status"] in ("IN_PLAY", "LIVE", "PAUSED")]

            # Look for a voice channel with "World Cup" or "⚽" in name to rename
            wc_voice = None
            for vc in guild.voice_channels:
                if "world cup" in vc.name.lower() or "⚽" in vc.name or "🏆" in vc.name:
                    wc_voice = vc
                    break

            if not wc_voice:
                return

            member_count = len(wc_voice.members)

            if live_matches:
                m = live_matches[0]
                hf = get_flag(m["home"])
                af = get_flag(m["away"])
                hs = m["home_score"] if m["home_score"] is not None else 0
                as_ = m["away_score"] if m["away_score"] is not None else 0
                new_name = f"⚽ {m['home']} {hs}-{as_} {m['away']} LIVE"[:100]
            elif member_count > 0:
                new_name = f"🔥 World Cup Chat ({member_count} Fans)"[:100]
            else:
                new_name = "⚽ World Cup Lounge"

            if wc_voice.name != new_name:
                await wc_voice.edit(name=new_name)
        except discord.HTTPException as e:
            if e.status == 429:
                # Rate limited, skip this cycle
                await asyncio.sleep(60)
        except Exception as e:
            print(f"Voice channel rename error: {e}")

    @app_commands.command(name="create_wc_voice", description="[Admin] Create a dynamic World Cup voice channel")
    @app_commands.default_permissions(administrator=True)
    async def create_wc_voice(self, interaction: discord.Interaction):
        try:
            vc = await interaction.guild.create_voice_channel("⚽ World Cup Lounge")
            embed = discord.Embed(
                title="✅ Dynamic Voice Channel Created!",
                description=f"**{vc.name}** has been created.\n\n"
                            f"It will automatically rename to show:\n"
                            f"• `⚽ Team A 1-0 Team B LIVE` during matches\n"
                            f"• `🔥 World Cup Chat (X Fans)` when people are in it\n"
                            f"• `⚽ World Cup Lounge` when empty",
                color=COLOR_GOLD
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to create voice channels.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceChannels(bot))
