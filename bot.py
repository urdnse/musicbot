import discord
from discord.ext import commands
import yt_dlp
import os

# ---------- CONFIG ----------
DEVELOPER_NAME = "Deepanshu Yadav"
intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)

music_queue = {}
loop_song = {}
stay_connected = {}

# ---------- YTDLP OPTIONS ----------
YTDL_OPTS = {
    "format": "bestaudio[ext=m4a]/bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "cookiefile": "cookies.txt",
    "extractor_args": {
        "youtube": {
            "player_client": ["android"]
        }
    }
}

FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn"
}

# ---------- BOT READY ----------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# ---------- PLAY NEXT ----------
async def play_next(guild):
    if loop_song.get(guild.id) and guild.voice_client:
        guild.voice_client.play(loop_song[guild.id], after=lambda e: bot.loop.create_task(play_next(guild)))
        return

    if music_queue.get(guild.id):
        source = music_queue[guild.id].pop(0)
        guild.voice_client.play(source, after=lambda e: bot.loop.create_task(play_next(guild)))
    else:
        if not stay_connected.get(guild.id):
            await guild.voice_client.disconnect()

# ---------- MUSIC PANEL ----------
class MusicPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Pause", emoji="⏸️")
    async def pause(self, i: discord.Interaction, b: discord.ui.Button):
        vc = i.guild.voice_client
        if vc.is_playing():
            vc.pause()
            await i.response.send_message("⏸️ Paused", delete_after=2)

    @discord.ui.button(label="Resume", emoji="▶️")
    async def resume(self, i: discord.Interaction, b: discord.ui.Button):
        vc = i.guild.voice_client
        if vc.is_paused():
            vc.resume()
            await i.response.send_message("▶️ Resumed", delete_after=2)

    @discord.ui.button(label="Skip", emoji="⏭️")
    async def skip(self, i: discord.Interaction, b: discord.ui.Button):
        vc = i.guild.voice_client
        if vc:
            vc.stop()
            await i.response.send_message("⏭️ Skipped", delete_after=2)

    @discord.ui.button(label="Stop", emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, i: discord.Interaction, b: discord.ui.Button):
        vc = i.guild.voice_client
        if vc:
            music_queue[i.guild.id] = []
            loop_song[i.guild.id] = None
            await vc.disconnect()
            await i.response.send_message("⏹️ Stopped", delete_after=2)

# ---------- /play ----------
@bot.tree.command(name="play", description="Play music")
async def play(interaction: discord.Interaction, search: str):
    await interaction.response.defer()

    if not interaction.user.voice:
        return await interaction.followup.send("❌ Join a VC first")

    vc = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect()

    with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
        info = ydl.extract_info(f"ytsearch:{search}", download=False)["entries"][0]

    url = info.get("url")
    source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTS)

    music_queue.setdefault(interaction.guild.id, []).append(source)

    if not vc.is_playing():
        await play_next(interaction.guild)

    embed = discord.Embed(
        title="🎶 Added to Queue",
        description=info["title"],
        color=0x5865F2
    )
    embed.set_footer(text=f"Dev: {DEVELOPER_NAME}")

    await interaction.followup.send(embed=embed, view=MusicPanel())

# ---------- /loop ----------
@bot.tree.command(name="loop", description="Loop current song")
async def loop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc or not vc.source:
        return await interaction.response.send_message("❌ Nothing playing")

    loop_song[interaction.guild.id] = vc.source
    await interaction.response.send_message("🔁 Loop enabled")

# ---------- /24x7 ----------
@bot.tree.command(name="24x7", description="Keep bot in VC")
async def stay(interaction: discord.Interaction):
    stay_connected[interaction.guild.id] = True
    await interaction.response.send_message("🟢 24/7 mode enabled")

# ---------- TOKEN ----------
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set")

bot.run(TOKEN)
