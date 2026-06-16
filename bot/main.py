import discord
from discord.ext import commands
import asyncio
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from config import DISCORD_TOKEN
from database import init_db

# ─── Startup Banner ───────────────────────────────────────────────────────────
BANNER = """
\033[32m╔══════════════════════════════════════════════════════════╗
║        ⚽  WORLD CUP FESTIVAL BOT  ⚽                     ║
║                                                          ║
║   Live Scores • Predictions • Economy • Trivia           ║
║   Auto-updating channels • Notifications • Giveaways     ║
╚══════════════════════════════════════════════════════════╝\033[0m
"""

COGS = [
    "cogs.worldcup_hub",
    "cogs.live_matches",
    "cogs.predictions",
    "cogs.economy",
    "cogs.trivia_cog",
    "cogs.leaderboard_board",
    "cogs.standings",
    "cogs.giveaway",
    "cogs.admin",
    "cogs.moderation",
    "cogs.voice_channels",
    "cogs.notifications",
]


class WorldCupBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True
        intents.voice_states = True

        super().__init__(
            command_prefix="!wcf ",
            intents=intents,
            help_command=None,
            application_id=None,
        )

    async def setup_hook(self):
        print(BANNER)
        print(f"\033[33m[{datetime.utcnow().strftime('%H:%M:%S')}] Loading cogs...\033[0m")

        for cog in COGS:
            try:
                await self.load_extension(cog)
                print(f"  \033[32m✅ {cog}\033[0m")
            except Exception as e:
                print(f"  \033[31m❌ {cog}: {e}\033[0m")

        print(f"\033[33m[{datetime.utcnow().strftime('%H:%M:%S')}] Syncing slash commands...\033[0m")
        try:
            synced = await self.tree.sync()
            print(f"\033[32m✅ Synced {len(synced)} slash commands globally.\033[0m")
        except Exception as e:
            print(f"\033[31m❌ Command sync failed: {e}\033[0m")

    async def on_ready(self):
        print(f"\n\033[32m{'─'*55}")
        print(f"  ✅ Bot Online: {self.user} (ID: {self.user.id})")
        print(f"  📡 Connected to {len(self.guilds)} server(s)")
        print(f"  🕐 Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"{'─'*55}\033[0m\n")

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="⚽ World Cup 2026 | /worldcup"
            )
        )

    async def on_app_command_error(self, interaction: discord.Interaction, error: Exception):
        msg = "An error occurred. Please try again later."
        if isinstance(error, discord.app_commands.MissingPermissions):
            msg = "❌ You don't have permission to use this command."
        elif isinstance(error, discord.app_commands.BotMissingPermissions):
            msg = "❌ I don't have the required permissions for this action."
        elif isinstance(error, discord.app_commands.CommandOnCooldown):
            msg = f"⏰ Command on cooldown. Try again in `{error.retry_after:.1f}s`."

        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass

        print(f"[Command Error] {interaction.command.name if interaction.command else 'unknown'}: {error}")

    async def on_guild_join(self, guild: discord.Guild):
        print(f"✅ Joined new guild: {guild.name} ({guild.id})")
        # Try to send a welcome message to the first available text channel
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                embed = discord.Embed(
                    title="⚽ World Cup Festival Bot has arrived!",
                    description=(
                        "Thanks for adding me! Here's how to get started:\n\n"
                        "**1.** Use `/setup_all` to configure all auto-updating channels\n"
                        "**2.** Use `/worldcup` to open the tournament hub\n"
                        "**3.** Members can `/predict`, `/trivia`, and `/daily`\n\n"
                        "Use `/help` to see all available commands!\n\n"
                        "🏆 Let the World Cup Festival begin!"
                    ),
                    color=0xFFD700
                )
                try:
                    await channel.send(embed=embed)
                except Exception:
                    pass
                break


async def main():
    if not DISCORD_TOKEN:
        print("\033[31m❌ DISCORD_TOKEN environment variable not set!\033[0m")
        print("   Set it in Replit Secrets as DISCORD_TOKEN")
        return

    # Init database
    print("\033[33mInitializing database...\033[0m")
    init_db()

    bot = WorldCupBot()

    try:
        await bot.start(DISCORD_TOKEN)
    except discord.LoginFailure:
        print("\033[31m❌ Invalid Discord token! Check your DISCORD_TOKEN secret.\033[0m")
    except KeyboardInterrupt:
        print("\n\033[33m🛑 Bot shutting down...\033[0m")
        await bot.close()
    except Exception as e:
        print(f"\033[31m❌ Fatal error: {e}\033[0m")
        raise


if __name__ == "__main__":
    asyncio.run(main())
