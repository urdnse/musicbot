import discord
from discord.ext import commands
import yt_dlp
import os
import asyncio

# ---------- CONFIG ----------
DEVELOPER_NAME = "Deepanshu Yadav"
intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- YTDLP ----------
YTDL_OPTS = {
    "format": "bestaudio[ext=m4a]/bestaudio/best",
    "quiet": True,
    "noplaylist": True,
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

# ---------- READY ----------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

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
            await vc.disconnect()
            await i.response.send_message("Stopped", delete_after=2)

# ---------- /play ----------
@bot.tree.command(name="play", description="Play music")
async def play(interaction: discord.Interaction, search: str):
    await interaction.response.defer()

    if not interaction.user.voice:
        return await interaction.followup.send("❌ Join a voice channel first")

    vc = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect()

    with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
        info = ydl.extract_info(f"ytsearch:{search}", download=False)["entries"][0]

    url = info["url"]
    title = info["title"]
    duration = info.get("duration", 0)
    thumbnail = info.get("thumbnail")

    source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTS)
    vc.play(source)

    # Fake progress bar
    progress_bar = "🔘───────────────"
    total_time = f"0:{duration//60:02d}:{duration%60:02d}"

    embed = discord.Embed(
        title="🎧 NOW PLAYING",
        description=f"**{title}**\n\n`0:00` {progress_bar} `{total_time}`",
        color=0x2B2D31
    )

    embed.set_thumbnail(url=thumbnail)
    embed.add_field(
        name="Requested by",
        value=interaction.user.mention,
        inline=True
    )
    embed.add_field(
        name="Voice Channel",
        value=interaction.user.voice.channel.mention,
        inline=True
    )
    embed.set_footer(text=f"Dev: {DEVELOPER_NAME}")

    await interaction.followup.send(embed=embed, view=MusicPanel())

# ---------- TOKEN ----------
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set")

bot.run(TOKEN)
