import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio

class Stats(commands.Cog):
    """Cog for managing and updating server statistics channels with Rate Limit protection."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.stats_categories = {}   # guild_id -> CategoryChannel
        self.stats_channels = {}     # guild_id -> {'members': VoiceChannel, 'bots': VoiceChannel, 'voice': VoiceChannel}
        self.stats_update_loop.start()

    def cog_unload(self):
        self.stats_update_loop.cancel()

    async def get_or_create_stats_channels(self, guild: discord.Guild):
        """Find or create server statistics category and voice channels."""
        category = discord.utils.get(guild.categories, name="📊 Server Statistics")
        if not category:
            category = await guild.create_category("📊 Server Statistics")
        self.stats_categories[guild.id] = category

        if guild.id not in self.stats_channels:
            self.stats_channels[guild.id] = {}

        human_count = sum(1 for m in guild.members if not m.bot)
        bot_count = sum(1 for m in guild.members if m.bot)
        voice_count = sum(1 for m in guild.members if m.voice and m.voice.channel)

        # Members channel
        human_channel = None
        for ch in category.voice_channels:
            if ch.name.startswith("👥 Members:"):
                human_channel = ch
                break
        if not human_channel:
            human_channel = await category.create_voice_channel(f"👥 Members: {human_count}")
        self.stats_channels[guild.id]['members'] = human_channel

        # Bots channel
        bot_channel = None
        for ch in category.voice_channels:
            if ch.name.startswith("🤖 Bots:"):
                bot_channel = ch
                break
        if not bot_channel:
            bot_channel = await category.create_voice_channel(f"🤖 Bots: {bot_count}")
        self.stats_channels[guild.id]['bots'] = bot_channel

        # In Voice channel
        voice_channel = None
        for ch in category.voice_channels:
            if ch.name.startswith("🎤 In Voice:"):
                voice_channel = ch
                break
        if not voice_channel:
            voice_channel = await category.create_voice_channel(f"🎤 In Voice: {voice_count}")
        self.stats_channels[guild.id]['voice'] = voice_channel

        return self.stats_channels[guild.id]

    async def update_guild_stats(self, guild: discord.Guild):
        """Update stat channel names only if the numbers changed, avoiding redundant API calls."""
        try:
            channels = await self.get_or_create_stats_channels(guild)
            human_count = sum(1 for m in guild.members if not m.bot)
            bot_count = sum(1 for m in guild.members if m.bot)
            voice_count = sum(1 for m in guild.members if m.voice and m.voice.channel)

            expected_members_name = f"👥 Members: {human_count}"
            expected_bots_name = f"🤖 Bots: {bot_count}"
            expected_voice_name = f"🎤 In Voice: {voice_count}"

            if channels.get('members') and channels['members'].name != expected_members_name:
                await channels['members'].edit(name=expected_members_name)
                await asyncio.sleep(1)

            if channels.get('bots') and channels['bots'].name != expected_bots_name:
                await channels['bots'].edit(name=expected_bots_name)
                await asyncio.sleep(1)

            if channels.get('voice') and channels['voice'].name != expected_voice_name:
                await channels['voice'].edit(name=expected_voice_name)
                await asyncio.sleep(1)

            print(f"[Stats] Updated stats for {guild.name}: {human_count} members, {bot_count} bots, {voice_count} in voice")
        except discord.errors.RateLimited as rl:
            print(f"[Stats] Rate limited on guild {guild.name}. Retry after: {rl.retry_after}s")
        except Exception as e:
            print(f"[Stats] Error updating stats for {guild.name}: {e}")

    @tasks.loop(minutes=10)
    async def stats_update_loop(self):
        """Background task updating channel statistics every 10 minutes to respect Discord rate limits."""
        for guild in self.bot.guilds:
            await self.update_guild_stats(guild)

    @stats_update_loop.before_loop
    async def before_stats_update_loop(self):
        await self.bot.wait_until_ready()

    @commands.hybrid_command(name="setupstats", description="สร้างหมวดและห้องแสดงสถิติเซิร์ฟเวอร์")
    async def setupstats(self, ctx: commands.Context):
        guild = ctx.guild
        if not guild:
            await ctx.send("❌ คำสั่งนี้ใช้ได้เฉพาะในเซิร์ฟเวอร์เท่านั้น", ephemeral=True)
            return

        await ctx.defer()
        try:
            await self.get_or_create_stats_channels(guild)
            await ctx.send("✅ ตั้งค่าหมวด **📊 Server Statistics** เรียบร้อยแล้ว (จะอัปเดตอัตโนมัติทุก 10 นาที)")
        except Exception as e:
            await ctx.send(f"❌ เกิดข้อผิดพลาดในการตั้งค่า: {e}")

    @commands.hybrid_command(name="stats", description="ดูข้อมูลสถิติสมาชิกและห้องในเซิร์ฟเวอร์แบบละเอียด")
    async def stats(self, ctx: commands.Context):
        guild = ctx.guild
        if not guild:
            await ctx.send("❌ คำสั่งนี้ใช้ได้เฉพาะในเซิร์ฟเวอร์เท่านั้น", ephemeral=True)
            return

        online = sum(1 for member in guild.members if member.status != discord.Status.offline)
        offline = sum(1 for member in guild.members if member.status == discord.Status.offline)
        bots = sum(1 for member in guild.members if member.bot)
        humans = guild.member_count - bots
        in_voice = sum(1 for member in guild.members if member.voice and member.voice.channel)

        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)

        embed = discord.Embed(
            title=f"📊 Server Statistics: {guild.name}",
            color=discord.Color.green()
        )
        embed.add_field(name="👥 สมาชิก", value=f"ทั้งหมด: {guild.member_count}\nคน: {humans}\nบอท: {bots}", inline=True)
        embed.add_field(name="🟢 สถานะ", value=f"ออนไลน์: {online}\nออฟไลน์: {offline}", inline=True)
        embed.add_field(name="🎤 ห้องเสียง", value=f"ในห้องเสียง: {in_voice}", inline=True)
        embed.add_field(name="📢 ช่องทั้งหมด", value=f"ข้อความ: {text_channels}\nเสียง: {voice_channels}", inline=True)
        embed.add_field(name="🏆 ระดับ Boost", value=f"Level {guild.premium_tier}\nBoosts: {guild.premium_subscription_count}", inline=True)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text=f"Server ID: {guild.id}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="debug", description="ตรวจสอบจำนวนสมาชิกเชิงลึก")
    async def debug(self, ctx: commands.Context):
        guild = ctx.guild
        if not guild:
            await ctx.send("❌ คำสั่งนี้ใช้ได้เฉพาะในเซิร์ฟเวอร์เท่านั้น", ephemeral=True)
            return

        total = guild.member_count
        humans = sum(1 for m in guild.members if not m.bot)
        bots = sum(1 for m in guild.members if m.bot)
        in_voice = sum(1 for m in guild.members if m.voice and m.voice.channel)

        debug_msg = f"""**🔍 Debug Member Counts:**
• Total Members: {total}
• 👥 Members (Humans): {humans}
• 🤖 Bots: {bots}
• 🎤 In Voice: {in_voice}"""
        await ctx.send(debug_msg)

async def setup(bot: commands.Bot):
    await bot.add_cog(Stats(bot))
