import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import os

# --- SETUP ---
# We don't need to find FFmpeg anymore. Docker put it in the standard place.
ffmpeg_executable = "ffmpeg"

class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Slash commands synced!")

bot = MusicBot()

# --- AUDIO SETTINGS ---
yt_dl_options = {
    'format': 'bestaudio/best',
    'noplaylist': 'True',
    'quiet': True,
    'default_search': 'auto'
}
ytdl = yt_dlp.YoutubeDL(yt_dl_options)

ffmpeg_options = {
    'executable': ffmpeg_executable,
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 
    'options': '-vn'
}

# --- COMMANDS ---
@bot.tree.command(name="play", description="Play a song")
async def play(interaction: discord.Interaction, search: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ Join a Voice Channel first!", ephemeral=True)

    # 1. Show loading (Don't delete this message!)
    await interaction.response.send_message(f"🔍 **Searching for:** `{search}`...")

    if not interaction.guild.voice_client:
        await interaction.user.voice.channel.connect()

    try:
        # 2. Get Song Info
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{search}", download=False))
        
        if 'entries' in data:
            data = data['entries'][0]

        song_url = data['url']
        title = data['title']

        # 3. Play
        voice = interaction.guild.voice_client
        
        if voice.is_playing():
            voice.stop() # For testing, just stop current and play new
            
        source = discord.FFmpegPCMAudio(song_url, **ffmpeg_options)
        voice.play(source)

        # 4. Success Message
        await interaction.edit_original_response(content=f"🎶 **Now Playing:** {title}")

    except Exception as e:
        # 5. Error Handler (Shows you WHY it failed instead of vanishing)
        await interaction.edit_original_response(content=f"❌ **Error:** {e}")

@bot.tree.command(name="stop", description="Stop music")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("Stopped.")

# Start
bot.run(os.environ["DISCORD_TOKEN"])
