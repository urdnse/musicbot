import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import json
import os

# --- DATABASE SETUP ---
PLAYLIST_FILE = "playlists.json"
def load_db():
    if not os.path.exists(PLAYLIST_FILE): return {}
    with open(PLAYLIST_FILE, "r") as f: return json.load(f)
def save_db(data):
    with open(PLAYLIST_FILE, "w") as f: json.dump(data, f, indent=4)

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
    'cookiefile': 'cookies.txt',  # MUST upload this file to GitHub
    'extractor_args': {'youtube': {'player_client': ['web_embedded']}}
}
FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

# --- PRO CONTROL PANEL ---
class MusicPanel(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Skip", emoji="⏭️", style=discord.ButtonStyle.primary)
    async def skip(self, interaction, button):
        interaction.guild.voice_client.stop()
        await interaction.response.send_message("⏭️ Skipped!", delete_after=2.0) # Auto-delete in 2s

    @discord.ui.button(label="Stop", emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, interaction, button):
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("⏹️ Stopped.", delete_after=2.0)

# --- COMMANDS ---
@bot.tree.command(name="play", description="Play a song")
async def play(interaction: discord.Interaction, search: str):
    await interaction.response.send_message(f"🔍 Searching: `{search}`...", delete_after=2.0)
    
    if not interaction.guild.voice_client:
        await interaction.user.voice.channel.connect()
    
    with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
        info = ydl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
        url = info['url']
        
    source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTS)
    interaction.guild.voice_client.play(source)
    
    embed = discord.Embed(title=info['title'], color=0x2b2d31)
    embed.add_field(name="🙋 Requested By", value=interaction.user.mention, inline=True)
    embed.set_footer(text="Dev: Deepanshu Yadav")
    await interaction.channel.send(embed=embed, view=MusicPanel(bot))

# --- PLAYLIST SYSTEM ---
@bot.tree.command(name="playlist_create", description="Create a playlist")
async def pl_create(interaction: discord.Interaction, name: str):
    db = load_db()
    db[name] = []
    save_db(db)
    await interaction.response.send_message(f"✅ Playlist `{name}` created!", ephemeral=True)

@bot.tree.command(name="playlist_add", description="Add song to playlist")
async def pl_add(interaction: discord.Interaction, playlist: str, song_url: str):
    db = load_db()
    if playlist in db:
        db[playlist].append(song_url)
        save_db(db)
        await interaction.response.send_message(f"➕ Added to `{playlist}`", delete_after=2.0)
    else:
        await interaction.response.send_message("❌ Not found.", ephemeral=True)

bot.run(os.environ["DISCORD_TOKEN"])
