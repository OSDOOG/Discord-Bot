import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

class VoiceLogs(commands.Cog):
    """Cog for logging voice state updates (join, leave, move, mute/unmute)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log_channels = {}  # guild_id -> TextChannel

    async def get_or_create_log_channel(self, guild: discord.Guild) -> discord.TextChannel:
        """Find or create dedicated log channel in 'in-out' category or named 'bot-logs' / 'logs'."""
        if guild.id in self.log_channels:
            channel = self.log_channels[guild.id]
            if channel and channel in guild.text_channels:
                return channel

        # 1. Search for 'คนเข้าออก' channel in 'in-out' category
        category = discord.utils.get(guild.categories, name="in-out")
        if category:
            channel = discord.utils.get(category.text_channels, name="คนเข้าออก")
            if channel:
                self.log_channels[guild.id] = channel
                return channel

        # 2. Search for common log channel names
        for ch in guild.text_channels:
            if ch.name in ["bot-logs", "logs", "คนเข้าออก", "voice-logs"]:
                self.log_channels[guild.id] = ch
                return ch

        # 3. Create if none exists
        if not category:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True, manage_channels=True)
            }
            category = await guild.create_category("in-out", overwrites=overwrites)

        channel = await category.create_text_channel("คนเข้าออก")
        await channel.send("📝 **ช่องบันทึกการเข้า/ออกห้องเสียง**\nบอทจะบันทึกการเคลื่อนไหวในห้องเสียงที่นี่")
        self.log_channels[guild.id] = channel
        return channel

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        guild = member.guild
        try:
            log_channel = await self.get_or_create_log_channel(guild)
        except Exception as e:
            print(f"[VoiceLogs] Could not get/create log channel in {guild.name}: {e}")
            return

        now_str = datetime.now().strftime("%H:%M:%S")

        try:
            # 1. Joined a voice channel
            if before.channel is None and after.channel is not None:
                embed = discord.Embed(
                    title="🎤 เข้าห้องเสียง",
                    description=f"**{member.mention}** เข้าห้อง **{after.channel.name}**",
                    color=discord.Color.green()
                )
                embed.add_field(name="เวลา", value=now_str, inline=True)
                if member.avatar:
                    embed.set_thumbnail(url=member.avatar.url)
                await log_channel.send(embed=embed)

            # 2. Left a voice channel
            elif before.channel is not None and after.channel is None:
                embed = discord.Embed(
                    title="🔇 ออกจากห้องเสียง",
                    description=f"**{member.mention}** ออกจากห้อง **{before.channel.name}**",
                    color=discord.Color.red()
                )
                embed.add_field(name="เวลา", value=now_str, inline=True)
                if member.avatar:
                    embed.set_thumbnail(url=member.avatar.url)
                await log_channel.send(embed=embed)

            # 3. Moved between voice channels
            elif before.channel is not None and after.channel is not None and before.channel != after.channel:
                embed = discord.Embed(
                    title="🔄 ย้ายห้องเสียง",
                    description=f"**{member.mention}** ย้ายจาก **{before.channel.name}** ไป **{after.channel.name}**",
                    color=discord.Color.blue()
                )
                embed.add_field(name="เวลา", value=now_str, inline=True)
                if member.avatar:
                    embed.set_thumbnail(url=member.avatar.url)
                await log_channel.send(embed=embed)

            # 4. Mute / Unmute state changed
            elif before.channel is not None and after.channel is not None:
                if before.self_mute != after.self_mute and after.self_mute:
                    embed = discord.Embed(
                        title="🔇 ปิดไมค์",
                        description=f"**{member.mention}** ปิดไมค์ในห้อง **{after.channel.name}**",
                        color=discord.Color.orange()
                    )
                    embed.add_field(name="เวลา", value=now_str, inline=True)
                    await log_channel.send(embed=embed)
                elif before.self_mute != after.self_mute and not after.self_mute:
                    embed = discord.Embed(
                        title="🎤 เปิดไมค์",
                        description=f"**{member.mention}** เปิดไมค์ในห้อง **{after.channel.name}**",
                        color=discord.Color.light_grey()
                    )
                    embed.add_field(name="เวลา", value=now_str, inline=True)
                    await log_channel.send(embed=embed)

        except Exception as e:
            print(f"[VoiceLogs] Error sending log embed in {guild.name}: {e}")

    @commands.hybrid_command(name="testlog", description="ทดสอบระบบ logging การเข้า/ออกห้องเสียง")
    async def testlog(self, ctx: commands.Context):
        guild = ctx.guild
        if not guild:
            await ctx.send("❌ คำสั่งนี้ใช้ได้เฉพาะในเซิร์ฟเวอร์เท่านั้น", ephemeral=True)
            return

        await ctx.defer()
        try:
            log_channel = await self.get_or_create_log_channel(guild)
            test_embed = discord.Embed(
                title="🧪 Test Logging",
                description=f"**{ctx.author.mention}** ทดสอบระบบ voice logging",
                color=discord.Color.purple()
            )
            test_embed.add_field(name="เวลา", value=datetime.now().strftime("%H:%M:%S"), inline=True)
            await log_channel.send(embed=test_embed)
            await ctx.send(f"✅ ส่งข้อความทดสอบไปที่ช่อง {log_channel.mention} เรียบร้อยแล้ว!")
        except Exception as e:
            await ctx.send(f"❌ เกิดข้อผิดพลาดในการทดสอบ log: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceLogs(bot))
