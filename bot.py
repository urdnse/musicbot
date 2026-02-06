import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os

# --- CONFIG ---
DEVELOPER_NAME = "Deepanshu Yadav"

class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync()

bot = MusicBot()

# --- AUDIO BYPASS CONFIG ---
YTDL_OPTS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'nocheckcertificate': True,
    'cookiefile': 'cookies.txt', 
    'extractor_args': {'youtube': {'player_client': ['web_embedded']}}
}

FFMPEG_OPTS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# --- PRO PANEL VIEW ---
class MusicPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Skip", emoji="⏭️", style=discord.ButtonStyle.primary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("⏭️ Skipped!", delete_after=2.0)

    @discord.ui.button(label="Stop", emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("⏹️ Stopped.", delete_after=2.0)

@bot.tree.command(name="play", description="Play music")
async def play(interaction: discord.Interaction, search: str):
    await interaction.response.send_message(f"🔍 Searching: `{search}`...", delete_after=2.0)
    
    if not interaction.guild.voice_client:
        await interaction.user.voice.channel.connect()

    try:
        with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
            info = ydl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
            url = info['url']
        
        source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTS)
        interaction.guild.voice_client.play(source)
        
        embed = discord.Embed(title=f"🎶 {info['title']}", color=0x2b2d31)
        embed.set_footer(text=f"Dev: {DEVELOPER_NAME}")
        await interaction.channel.send(embed=embed, view=MusicPanel())
    except Exception as e:
        await interaction.channel.send(f"❌ Error: {e}", delete_after=5.0)

bot.run(os.environ["DISCORD_TOKEN"])
