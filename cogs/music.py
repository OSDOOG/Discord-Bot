import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import re
import ssl
try:
    import certifi
except ImportError:
    certifi = None

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

# Custom SSL context for maximum compatibility
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

YDL_OPTIONS = {
    'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio[ext=mp3]/bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'nocheckcertificate': True,
    'socket_timeout': 30,
    'retries': 3,
    'ssl_options': ssl_context,
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'ios'],
            'player_skip': ['webpage', 'configs', 'js']
        }
    },
    'http_headers': {
        'User-Agent': 'com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip'
    }
}

class Music(commands.Cog):
    """Cog for YouTube music playback, queuing, and audio enhancements."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.song_queues = {}          # guild_id -> list of song_info dicts
        self.now_playing = {}          # guild_id -> current song_info dict
        self.bass_boost_enabled = {}   # guild_id -> bool
        self.bass_levels = {}          # guild_id -> int (1-10)
        self.restart_in_progress = {}  # guild_id -> bool

    def get_queue(self, guild_id: int):
        if guild_id not in self.song_queues:
            self.song_queues[guild_id] = []
        return self.song_queues[guild_id]

    async def ensure_voice(self, ctx: commands.Context) -> discord.VoiceClient:
        """Connects to the author's voice channel or moves if needed."""
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ คุณต้องอยู่ในห้องเสียงก่อนใช้งานคำสั่งนี้!", ephemeral=True)
            return None

        target_channel = ctx.author.voice.channel
        vc = ctx.guild.voice_client

        if vc:
            if vc.channel != target_channel:
                await vc.move_to(target_channel)
            return vc
        else:
            try:
                vc = await target_channel.connect(timeout=10.0, reconnect=True)
                return vc
            except Exception as e:
                await ctx.send(f"❌ ไม่สามารถเชื่อมต่อห้องเสียงได้: {e}")
                return None

    async def extract_song_info(self, query: str, requester: discord.Member, channel: discord.TextChannel):
        """Extract song metadata and direct audio stream URL using yt-dlp."""
        if yt_dlp is None:
            raise Exception("yt-dlp ไม่ได้ติดตั้งอยู่ในระบบ กรุณารัน pip install yt-dlp")

        youtube_patterns = [
            r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
            r'https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
            r'https?://youtu\.be/([a-zA-Z0-9_-]+)',
            r'https?://(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]+)',
        ]
        is_url = any(re.match(p, query) for p in youtube_patterns)
        search_query = query if is_url else f"ytsearch:{query}"

        loop = asyncio.get_event_loop()
        def fetch():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                return ydl.extract_info(search_query, download=False)

        info = await loop.run_in_executor(None, fetch)

        if 'entries' in info:
            entries = info['entries']
            if not entries:
                raise Exception("ไม่พบเพลงตามที่ค้นหา")
            info = entries[0]

        # Select best audio stream
        audio_url = None
        formats = info.get('formats', [])
        for f in formats:
            if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                audio_url = f.get('url')
                break

        if not audio_url:
            for f in formats:
                if f.get('acodec') != 'none':
                    audio_url = f.get('url')
                    break

        if not audio_url:
            audio_url = info.get('url')

        return {
            'title': info.get('title', 'Unknown Title'),
            'url': info.get('webpage_url', query),
            'stream_url': audio_url,
            'duration': info.get('duration', 0),
            'thumbnail': info.get('thumbnail', ''),
            'requester': requester,
            'channel': channel
        }

    async def play_next_song(self, guild: discord.Guild):
        """Play next track from guild queue."""
        vc = guild.voice_client
        queue = self.get_queue(guild.id)

        if not vc or not vc.is_connected():
            self.now_playing[guild.id] = None
            return

        if len(queue) == 0:
            self.now_playing[guild.id] = None
            return

        song = queue.pop(0)
        self.now_playing[guild.id] = song

        # Prepare FFmpeg audio filters (Bass boost)
        bass_enabled = self.bass_boost_enabled.get(guild.id, False)
        bass_lvl = self.bass_levels.get(guild.id, 5)

        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        if bass_enabled and bass_lvl > 0:
            gain_db = bass_lvl * 2
            ffmpeg_options['options'] += f' -af "bass=g={gain_db}:f=100:w=200"'

        try:
            source = discord.FFmpegPCMAudio(song['stream_url'], **ffmpeg_options)
            transformed = discord.PCMVolumeTransformer(source, volume=1.0)

            def after_playback(err):
                if err:
                    print(f"[Music] Playback error in {guild.name}: {err}")
                if self.restart_in_progress.get(guild.id, False):
                    self.restart_in_progress[guild.id] = False
                    return
                asyncio.run_coroutine_threadsafe(self.play_next_song(guild), self.bot.loop)

            vc.play(transformed, after=after_playback)

            channel = song.get('channel')
            if channel:
                embed = discord.Embed(
                    title="🎵 Now Playing",
                    description=f"**[{song['title']}]({song['url']})**",
                    color=discord.Color.purple()
                )
                embed.add_field(name="เพิ่มโดย", value=song['requester'].mention, inline=True)
                bass_status = f"🔊 ON (Level {bass_lvl}/10)" if bass_enabled else "🔇 OFF"
                embed.add_field(name="Bass Boost", value=bass_status, inline=True)
                if song.get('thumbnail'):
                    embed.set_thumbnail(url=song['thumbnail'])
                await channel.send(embed=embed)

        except Exception as e:
            print(f"[Music] Error playing song in {guild.name}: {e}")
            channel = song.get('channel')
            if channel:
                await channel.send(f"❌ ไม่สามารถเล่นเพลง **{song['title']}** ได้: {e}")
            await self.play_next_song(guild)

    @commands.hybrid_command(name="play", description="เล่นเพลงจาก YouTube หรือค้นหาชื่อเพลง")
    @app_commands.describe(query="ชื่อเพลงหรือลิงก์ YouTube")
    async def play(self, ctx: commands.Context, *, query: str):
        vc = await self.ensure_voice(ctx)
        if not vc:
            return

        await ctx.defer()
        try:
            song_info = await self.extract_song_info(query, ctx.author, ctx.channel)
            queue = self.get_queue(ctx.guild.id)

            if not vc.is_playing() and not vc.is_paused():
                queue.insert(0, song_info)
                await self.play_next_song(ctx.guild)
                await ctx.send(f"🎶 เริ่มเล่น: **{song_info['title']}**")
            else:
                queue.append(song_info)
                await ctx.send(f"📋 เพิ่มในคิวลำดับที่ **{len(queue)}**: **{song_info['title']}**")

        except Exception as e:
            await ctx.send(f"❌ ไม่สามารถเล่นเพลงได้: {e}")

    @commands.hybrid_command(name="pause", description="หยุดเพลงชั่วคราว")
    async def pause(self, ctx: commands.Context):
        vc = ctx.guild.voice_client
        if not vc or not vc.is_playing():
            await ctx.send("❌ ไม่มีเพลงที่กำลังเล่นอยู่", ephemeral=True)
            return

        vc.pause()
        await ctx.send("⏸️ หยุดเพลงชั่วคราวแล้ว")

    @commands.hybrid_command(name="resume", description="เล่นเพลงต่อจากที่หยุดไว้")
    async def resume(self, ctx: commands.Context):
        vc = ctx.guild.voice_client
        if not vc or not vc.is_paused():
            await ctx.send("❌ ไม่มีเพลงที่หยุดไว้", ephemeral=True)
            return

        vc.resume()
        await ctx.send("▶️ เล่นเพลงต่อแล้ว")

    @commands.hybrid_command(name="skip", description="ข้ามเพลงปัจจุบัน")
    async def skip(self, ctx: commands.Context):
        vc = ctx.guild.voice_client
        if not vc or not vc.is_playing():
            await ctx.send("❌ ไม่มีเพลงที่กำลังเล่นอยู่", ephemeral=True)
            return

        vc.stop()
        await ctx.send("⏭️ ข้ามเพลงปัจจุบันเรียบร้อย")

    @commands.hybrid_command(name="stop", description="หยุดเล่นเพลงและล้างคิวทั้งหมด")
    async def stop(self, ctx: commands.Context):
        vc = ctx.guild.voice_client
        if not vc:
            await ctx.send("❌ บอทไม่ได้อยู่ในห้องเสียง", ephemeral=True)
            return

        self.get_queue(ctx.guild.id).clear()
        self.now_playing[ctx.guild.id] = None
        vc.stop()
        await ctx.send("⏹️ หยุดเล่นและล้างคิวเพลงทั้งหมดแล้ว")

    @commands.hybrid_command(name="queue", description="แสดงรายการเพลงในคิว")
    async def queue(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        current = self.now_playing.get(guild_id)
        queue_list = self.get_queue(guild_id)

        if not current and len(queue_list) == 0:
            await ctx.send("❌ ไม่มีเพลงในคิว", ephemeral=True)
            return

        embed = discord.Embed(title="🎵 คิวเพลงทั้งหมด", color=discord.Color.blue())
        if current:
            embed.add_field(
                name="🎶 กำลังเล่นอยู่",
                value=f"**[{current['title']}]({current['url']})**\nเพิ่มโดย: {current['requester'].mention}",
                inline=False
            )

        if queue_list:
            desc = ""
            for i, s in enumerate(queue_list[:10], 1):
                desc += f"**{i}.** [{s['title']}]({s['url']}) - {s['requester'].mention}\n"
            embed.add_field(name=f"📋 เพลงในคิว ({len(queue_list)} เพลง)", value=desc, inline=False)
            if len(queue_list) > 10:
                embed.set_footer(text=f"และอีก {len(queue_list) - 10} เพลง...")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="clear", description="ล้างคิวเพลงทั้งหมด")
    async def clear(self, ctx: commands.Context):
        queue = self.get_queue(ctx.guild.id)
        count = len(queue)
        queue.clear()
        await ctx.send(f"🗑️ ล้างคิวเพลงจำนวน {count} เพลงเรียบร้อยแล้ว")

    @commands.hybrid_command(name="bassboost", description="เปิด/ปิด โหมด Bass Boost")
    async def bassboost(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        vc = ctx.guild.voice_client
        if not vc or not vc.is_playing():
            await ctx.send("❌ ต้องเปิดเพลงอยู่จึงจะเปิด/ปิด Bass Boost ได้", ephemeral=True)
            return

        self.bass_boost_enabled[guild_id] = not self.bass_boost_enabled.get(guild_id, False)
        status = "เปิดแล้ว 🔊" if self.bass_boost_enabled[guild_id] else "ปิดแล้ว 🔇"
        await ctx.send(f"**Bass Boost {status}** กำลังประมวลผลเพลงเดิมใหม่...")

        # Replay current song with filter applied
        current = self.now_playing.get(guild_id)
        if current:
            self.restart_in_progress[guild_id] = True
            vc.stop()
            await asyncio.sleep(0.5)
            self.get_queue(guild_id).insert(0, current)
            await self.play_next_song(ctx.guild)

    @commands.hybrid_command(name="bass", description="ตั้งค่าระดับ Bass Boost (1-10)")
    @app_commands.describe(level="ระดับความแรงของ Bass ระหว่าง 1 ถึง 10")
    async def bass(self, ctx: commands.Context, level: int):
        if level < 1 or level > 10:
            await ctx.send("❌ ระดับ Bass ต้องอยู่ระหว่าง 1 ถึง 10", ephemeral=True)
            return

        guild_id = ctx.guild.id
        vc = ctx.guild.voice_client
        if not vc or not vc.is_playing():
            await ctx.send("❌ ต้องเปิดเพลงอยู่จึงจะปรับระดับ Bass ได้", ephemeral=True)
            return

        self.bass_levels[guild_id] = level
        self.bass_boost_enabled[guild_id] = True
        await ctx.send(f"🔊 ตั้งค่า Bass Boost เป็นระดับ **{level}/10** กำลังอัปเดต...")

        current = self.now_playing.get(guild_id)
        if current:
            self.restart_in_progress[guild_id] = True
            vc.stop()
            await asyncio.sleep(0.5)
            self.get_queue(guild_id).insert(0, current)
            await self.play_next_song(ctx.guild)

    @commands.hybrid_command(name="leave", description="ให้ออกจากห้องเสียงและเคลียร์ข้อมูล")
    async def leave(self, ctx: commands.Context):
        vc = ctx.guild.voice_client
        if not vc:
            await ctx.send("❌ บอทไม่ได้อยู่ในห้องเสียง", ephemeral=True)
            return

        self.get_queue(ctx.guild.id).clear()
        self.now_playing[ctx.guild.id] = None
        await vc.disconnect(force=True)
        await ctx.send("👋 ออกจากห้องเสียงเรียบร้อยแล้ว")

    @commands.hybrid_command(name="forceleave", description="บังคับตัดการเชื่อมต่อห้องเสียงเมื่อบอทค้าง")
    async def forceleave(self, ctx: commands.Context):
        vc = ctx.guild.voice_client
        self.get_queue(ctx.guild.id).clear()
        self.now_playing[ctx.guild.id] = None

        if vc:
            try:
                await vc.disconnect(force=True)
            except Exception:
                pass

        await ctx.send("🔨 Force disconnect สำเร็จ ล้างข้อมูลเพลงทั้งหมดแล้ว")

async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
