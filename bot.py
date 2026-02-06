import discord
from discord.ext import commands
import yt_dlp
import os

# -------- CONFIG --------
DEVELOPER_NAME = "Deepanshu Yadav"

intents = discord.Intents.all()

class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = MusicBot()

# -------- YTDLP OPTIONS (RAILWAY SAFE) --------
YTDL_OPTS = {
    "format": "bestaudio[ext=m4a]/bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "nocheckcertificate": True,
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

# -------- MUSIC CONTROLS --------
class MusicPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Skip", emoji="⏭️", style=discord.ButtonStyle.primary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.send_message("⏭️ Skipped", delete_after=2)

    @discord.ui.button(label="Stop", emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await interaction.response.send_message("⏹️ Stopped", delete_after=2)

# -------- PLAY COMMAND --------
@bot.tree.command(name="play", description="Play music from YouTube")
async def play(interaction: discord.Interaction, search: str):
    await interaction.response.defer()

    if not interaction.user.voice:
        return await interaction.followup.send("❌ Join a voice channel first")

    if not interaction.guild.voice_client:
        await interaction.user.voice.channel.connect()

    try:
        with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
            info = ydl.extract_info(f"ytsearch:{search}", download=False)
            data = info["entries"][0]

        stream_url = data.get("url") or data.get("webpage_url")

        source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTS)
        vc = interaction.guild.voice_client
        vc.play(source)

        embed = discord.Embed(
            title="🎶 Now Playing",
            description=data["title"],
            color=0x5865F2
        )
        embed.set_footer(text=f"Developer: {DEVELOPER_NAME}")

        await interaction.followup.send(embed=embed, view=MusicPanel())

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")

# -------- RUN BOT --------
bot.run(os.environ["DISCORD_TOKEN"])
