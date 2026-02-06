import discord
from discord.ext import commands
import yt_dlp
import os
import asyncio

# ---------- CONFIG ----------
DEVELOPER_NAME = "Deepanshu Yadav"
IDLE_TIMEOUT = 300

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

queues = {}
idle_tasks = {}

# ---------- YTDLP OPTIONS ----------
YTDL_BASE = {
    "quiet": True,
    "noplaylist": True,
    "cachedir": False,
    "socket_timeout": 20,
}

YTDL_YOUTUBE = {
    **YTDL_BASE,
    "format": "bestaudio/best[protocol^=http]/best",
    "cookiefile": "cookies.txt",
    "extractor_args": {
        "youtube": {
            "player_client": ["android"],
            "skip": ["dash", "hls"]
        }
    },
}

YTDL_SOUNDCLOUD = {
    **YTDL_BASE,
    "format": "bestaudio/best",
}

FFMPEG_OPTS = {
    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 15 "
        "-rw_timeout 20000000"
    ),
    "options": "-vn"
}

# ---------- READY ----------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# ---------- IDLE ----------
async def idle_disconnect(guild):
    await asyncio.sleep(IDLE_TIMEOUT)
    vc = guild.voice_client
    if vc and not vc.is_playing():
        await vc.disconnect()

def schedule_idle(guild):
    if guild.id in idle_tasks:
        idle_tasks[guild.id].cancel()
    idle_tasks[guild.id] = bot.loop.create_task(idle_disconnect(guild))

# ---------- AUDIO ----------
def create_source(url):
    audio = discord.FFmpegPCMAudio(url, **FFMPEG_OPTS)
    return discord.PCMVolumeTransformer(audio, volume=1.0)

# ---------- QUEUE ----------
def play_next(guild):
    vc = guild.voice_client
    if not vc:
        return

    if queues.get(guild.id):
        source = queues[guild.id].pop(0)
        vc.play(source, after=lambda e: play_next(guild))
    else:
        schedule_idle(guild)

# ---------- CONTROLS ----------
class MusicPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def skip(self, i: discord.Interaction, b: discord.ui.Button):
        vc = i.guild.voice_client
        if vc:
            vc.stop()
            await i.response.send_message("⏭️ Skipped", delete_after=2)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, i: discord.Interaction, b: discord.ui.Button):
        vc = i.guild.voice_client
        if vc:
            queues[i.guild.id] = []
            await vc.disconnect()
            await i.response.send_message("Stopped", delete_after=2)

# ---------- EXTRACT WITH FALLBACK ----------
def extract_with_fallback(query):
    # Try YouTube first
    try:
        with yt_dlp.YoutubeDL(YTDL_YOUTUBE) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)
            return info["entries"][0]
    except Exception:
        pass

    # Fallback to SoundCloud
    with yt_dlp.YoutubeDL(YTDL_SOUNDCLOUD) as ydl:
        info = ydl.extract_info(f"scsearch:{query}", download=False)
        return info["entries"][0]

# ---------- /play ----------
@bot.tree.command(name="play", description="Play or queue music")
async def play(interaction: discord.Interaction, search: str):
    await interaction.response.send_message("🎧 Searching...", delete_after=1)

    if not interaction.user.voice:
        return await interaction.followup.send("❌ Join a VC first")

    vc = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect()

    if interaction.guild.id in idle_tasks:
        idle_tasks[interaction.guild.id].cancel()

    try:
        data = extract_with_fallback(search)

        source = create_source(data["url"])
        queues.setdefault(interaction.guild.id, []).append(source)

        if not vc.is_playing():
            play_next(interaction.guild)
            status = "🎧 Now Playing"
        else:
            status = "➕ Added to Queue"

        embed = discord.Embed(
            title=status,
            description=f"**{data['title']}**",
            color=0x2B2D31
        )
        embed.set_thumbnail(url=data.get("thumbnail"))
        embed.add_field(name="Requested by", value=interaction.user.mention)
        embed.set_footer(text=f"Dev: {DEVELOPER_NAME}")

        await interaction.followup.send(embed=embed, view=MusicPanel())

    except Exception:
        await interaction.followup.send(
            "❌ Could not play this song from YouTube or SoundCloud.\nTry another song."
        )

# ---------- TOKEN ----------
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set")

bot.run(TOKEN)
