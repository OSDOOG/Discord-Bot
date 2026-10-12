import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

class General(commands.Cog):
    """General utility commands (latency, greeting, server info)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="hello", description="ทักทายบอท")
    async def hello(self, ctx: commands.Context):
        await ctx.send(f"Hello {ctx.author.mention}! 👋")

    @commands.hybrid_command(name="ping", description="ตรวจสอบความเร็วการเชื่อมต่อของบอท (Latency)")
    async def ping(self, ctx: commands.Context):
        latency_ms = round(self.bot.latency * 1000)
        await ctx.send(f"Pong! 🏓 Latency: {latency_ms}ms")

    @commands.hybrid_command(name="info", description="แสดงข้อมูลพื้นฐานของเซิร์ฟเวอร์")
    async def info(self, ctx: commands.Context):
        guild = ctx.guild
        if not guild:
            await ctx.send("❌ คำสั่งนี้ใช้ได้เฉพาะในเซิร์ฟเวอร์เท่านั้น", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Server Information: {guild.name}",
            description=f"Created on: {guild.created_at.strftime('%Y-%m-%d')}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Total Members", value=str(guild.member_count), inline=True)
        embed.add_field(name="Total Channels", value=str(len(guild.channels)), inline=True)
        embed.add_field(name="Server Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="bothelp", description="แสดงคำสั่งทั้งหมดของบอท")
    async def bothelp(self, ctx: commands.Context):
        help_message = """
**🎵 Music Commands:**
• `/play [URL/ชื่อเพลง]` (หรือ `.play`) - เล่นเพลงจาก YouTube
• `/pause` (หรือ `.pause`) - หยุดเพลงชั่วคราว
• `/resume` (หรือ `.resume`) - เล่นเพลงต่อ
• `/stop` (หรือ `.stop`) - หยุดเพลงและเคลียร์คิว
• `/skip` (หรือ `.skip`) - ข้ามเพลงปัจจุบัน
• `/queue` (หรือ `.queue`) - แสดงคิวเพลง
• `/clear` (หรือ `.clear`) - ล้างคิวเพลงทั้งหมด
• `/leave` (หรือ `.leave`) - ให้ออกจากห้องเสียง
• `/bassboost` (หรือ `.bassboost`) - เปิด/ปิด Bass Boost
• `/bass [1-10]` (หรือ `.bass [1-10]`) - ตั้งระดับ Bass Boost

**📊 Server Statistics:**
• `/stats` (หรือ `.stats`) - สถิติเซิร์ฟเวอร์แบบละเอียด
• `/setupstats` (หรือ `.setupstats`) - สร้างหมวด Server Statistics
• `/debug` (หรือ `.debug`) - ตรวจสอบจำนวนสมาชิกเชิงลึก

**📝 Logging & General:**
• `/hello`, `/ping`, `/info`, `/testlog`
• สถิติห้องเสียงจะอัปเดตอัตโนมัติทุก 10 นาที เพื่อป้องกัน Discord Rate Limit
        """
        await ctx.send(help_message)

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
