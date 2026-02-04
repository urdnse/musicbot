import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import os

# --- CONFIGURATION ---
DEVELOPER_NAME = "Deepanshu Yadav" 

class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync()

bot = MusicBot()

# --- THE 2026 BYPASS CONFIG ---
yt_dl_options = {
    'format': 'bestaudio/best',
    'noplaylist': 'True',
    'quiet': True,
    'nocheckcertificate': True,
    # The 'tv' client currently avoids most Bot/DRM blocks
    'extractor_args': {
        'youtube': {
            'player_client': ['tv'], 
        }
    },
    'cookiefile': 'cookies.txt' # MUST upload a fresh Netscape cookies.txt
}
ytdl = yt_dlp.YoutubeDL(yt_dl_options)

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 
    'options': '-vn'
}

@bot.tree.command(name="play", description="Play a song")
async def play(interaction: discord.Interaction, search: str):
    # Sends searching message that deletes after 2 seconds
    await interaction.response.send_message(f"🔍 Searching: `{search}`...", delete_after=2.0)
    
    if not interaction.user.voice:
        return await interaction.followup.send("❌ Join a VC first!", ephemeral=True)
    if not interaction.guild.voice_client:
        await interaction.user.voice.channel.connect()

    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{search}", download=False))
        track = data['entries'][0]
        
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(track['url'], **ffmpeg_options))
        interaction.guild.voice_client.play(source)
        
        embed = discord.Embed(title=f"🎶 {track['title']}", color=0x2b2d31)
        embed.set_footer(text=f"Dev: {DEVELOPER_NAME}")
        await interaction.channel.send(embed=embed)
    except Exception as e:
        await interaction.channel.send(f"❌ Error: {e}", delete_after=5.0)

# Stop command with auto-delete notification
@bot.tree.command(name="stop", description="Stop music")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("🛑 Stopped.", delete_after=2.0)
    else:
        await interaction.response.send_message("❌ Not connected.", ephemeral=True)

bot.run(os.environ["DISCORD_TOKEN"])
