import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Setup bot intents
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.voice_states = True
intents.members = True

class ModularBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=".",
            intents=intents,
            help_command=None  # We use our custom /bothelp / .bothelp
        )

    async def setup_hook(self):
        """Automatically load all cogs and sync slash commands."""
        # Load cogs
        initial_extensions = [
            "cogs.general",
            "cogs.stats",
            "cogs.voice_logs",
            "cogs.music"
        ]

        for ext in initial_extensions:
            try:
                await self.load_extension(ext)
                print(f"[Bot] Loaded extension: {ext}")
            except Exception as e:
                print(f"[Bot] Failed to load extension {ext}: {e}")

        # Sync application slash commands globally
        try:
            synced = await self.tree.sync()
            print(f"[Bot] Synced {len(synced)} application (slash) commands globally.")
        except Exception as e:
            print(f"[Bot] Failed to sync application commands: {e}")

    async def on_ready(self):
        print("--------------------------------------------------")
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"Connected to {len(self.guilds)} servers")
        print("--------------------------------------------------")
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening, name="/bothelp หรือ .bothelp")
        )

    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """Global prefix command error handler."""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore invalid commands silently
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ ข้อมูลไม่ครบถ้วน: กรุณาระบุ `{error.param.name}`", ephemeral=True)
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ รูปแบบข้อมูลไม่ถูกต้อง", ephemeral=True)
        else:
            print(f"[Bot] Command error in {ctx.command}: {error}")

bot = ModularBot()

if __name__ == "__main__":
    if not TOKEN or TOKEN == "your_actual_bot_token_here" or TOKEN == "your_bot_token_here":
        print("Error: Please specify your valid DISCORD_TOKEN in the .env file!")
    else:
        bot.run(TOKEN)
