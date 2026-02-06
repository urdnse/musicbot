import discord
from discord.ext import commands
import yt_dlp
import os
import asyncio

# ---------- CONFIG ----------
DEVELOPER_NAME = "Deepanshu Yadav"
IDLE_TIMEOUT = 300  # 5 minutes

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

idle_tasks = {}

# ---------- YTDLP OPTIONS ----------
YTDL_OPTS = {
    "format": "bestaudio[ext=m4a]/bestaudio/best",
    "quiet": True,
    "noplaylist": True,
    "cookiefile": "cookies.txt",
    "extractor_args": {
        "youtube": {
            "player_client": ["android"]
        }
    },
    "socket_timeout": 15,
}

# STRONG FFMPEG RECONNECT
FFMPEG_OPTS = {
    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 10 "
        "-rw_timeout 15000000"
    ),
    "options": "-vn"
}

# ---------- READY ----------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# ---------- IDLE DISCONNECT ----------
async def idle_disconnect(guild: discord.Guild):
    await asyncio.sleep(IDLE_TIMEOUT)
    vc = guild.voice_client
    if vc and not vc.is_playing():
        await vc.disconnect()

def schedule_idle(guild):
    if guild.id in idle_tasks:
        idle_tasks[guild.id].cancel()
    idle_tasks[guild.id] = bot.loop.create_task(idle_disconnect(guild))

# ---------- CONTROL PANEL ----------
class MusicPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.primary)
    async def pause(self, i: discord.Interaction, b: discord.ui.Button):
        vc = i.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await i.response.send_message("Paused", delete_after=2)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.primary)
    async def resume(self, i: discord.Interaction, b: discord.ui.Button):
        vc = i.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await i.response.send_message("Resumed", delete_after=2)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def skip(self, i: discord.Interaction, b: discord.ui.Button):
        vc = i.guild.voice_client
        if vc:
            vc.stop()
            await i.response.send_message("Skipped", delete_after=2)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, i: discord.Interaction, b: discord.ui.Button):
        vc = i.guild.voice_client
        if vc:
            if i.guild.id in idle_tasks:
                idle_tasks[i.guild.id].cancel()
            await vc.disconnect()
            await i.response.send_message("Stopped", delete_after=2)

# ---------- SAFE AUDIO SOURCE ----------
def create_source(stream_url):
    audio = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTS)
    return discord.PCMVolumeTransformer(audio, volume=1.0)

# ---------- /play ----------
@bot.tree.command(name="play", description="Play music")
async def play(interaction: discord.Interaction, search: str):
    # Respond instantly to avoid "thinking" freeze
    await interaction.response.send_message("🎧 Loading...", delete_after=1)

    if not interaction.user.voice:
        return await interaction.followup.send("❌ Join a VC first")

    vc = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect()

    # Cancel idle timer
    if interaction.guild.id in idle_tasks:
        idle_tasks[interaction.guild.id].cancel()

    try:
        with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
            data = ydl.extract_info(f"ytsearch:{search}", download=False)["entries"][0]

        stream_url = data["url"]
        title = data["title"]
        duration = data.get("duration", 0)
        thumbnail = data.get("thumbnail")

        source = create_source(stream_url)

        vc.play(
            source,
            after=lambda e: schedule_idle(interaction.guild)
        )

        bar = "🔘───────────────"
        total = f"{duration//60}:{duration%60:02d}"

        embed = discord.Embed(
            title="🎧 NOW PLAYING",
            description=f"**{title}**\n\n`0:00` {bar} `{total}`",
            color=0x2B2D31
        )
        embed.set_thumbnail(url=thumbnail)
        embed.add_field(name="Requested by", value=interaction.user.mention)
        embed.add_field(name="Voice Channel", value=interaction.user.voice.channel.mention)
        embed.set_footer(text=f"Dev: {DEVELOPER_NAME}")

        await interaction.followup.send(embed=embed, view=MusicPanel())

    except Exception as e:
        await interaction.followup.send(f"❌ Failed to play: `{e}`")

# ---------- TOKEN ----------
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set")

bot.run(TOKEN)
