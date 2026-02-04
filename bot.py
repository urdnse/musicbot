import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import datetime
import time
import json
import os
import sys
import urllib.request
import tarfile
import shutil
import stat

# --- AUTO-INSTALLER (RUNS ON STARTUP) ---
def install_ffmpeg_if_missing():
    # Check if ffmpeg is already here
    if os.path.exists("./ffmpeg"):
        return "./ffmpeg"
    
    print("🛠️ FFmpeg missing. Installing automatically...")
    
    # Download the "Golden" v5.1.1 version (Safe for all servers)
    url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
    
    try:
        # 1. Download
        print("⬇️ Downloading...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open("ffmpeg.tar.xz", 'wb') as out:
            shutil.copyfileobj(response, out)
            
        # 2. Extract
        print("📦 Extracting...")
        with tarfile.open("ffmpeg.tar.xz") as f:
            f.extractall()
            
        # 3. Move
        print("📂 Moving...")
        for root, dirs, files in os.walk("."):
            if "ffmpeg" in files:
                path = os.path.join(root, "ffmpeg")
                if path == "./ffmpeg": continue
                shutil.move(path, "./ffmpeg")
                break
        
        # 4. Cleanup & Permissions
        if os.path.exists("ffmpeg.tar.xz"): os.remove("ffmpeg.tar.xz")
        st = os.stat("./ffmpeg")
        os.chmod("./ffmpeg", st.st_mode | stat.S_IEXEC)
        print("✅ FFmpeg Installed Successfully!")
        return "./ffmpeg"
        
    except Exception as e:
        print(f"❌ Install Error: {e}")
        return "ffmpeg" # Fallback to system default

# Run the installer BEFORE the bot starts
ffmpeg_path = install_ffmpeg_if_missing()

# --- CONFIGURATION ---
PLAYLIST_FILE = "playlists.json"

VIRAL_PLAYLISTS = [
    "https://www.youtube.com/playlist?list=PL15B1E77BB5708555",      
    "https://www.youtube.com/playlist?list=PL9bw4S5ePsEEqCMJSiYZ-KTtEjzVy0YvK"
]
INSTA_PLAYLISTS = [
    "https://www.youtube.com/playlist?list=PL9bw4S5ePsEEqCMJSiYZ-KTtEjzVy0YvK",
    "https://www.youtube.com/playlist?list=PLw-VjHDlEOgvtnnnqWlTqByAtC7tXBg6D"
]

def to_cool_font(text):
    mapping = {'A': '𝐀', 'B': '𝐁', 'C': '𝐂', 'D': '𝐃', 'a': '𝐚', 'b': '𝐛', 'c': '𝐜', 'd': '𝐝'} 
    return "".join(mapping.get(char, char) for char in text)

class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.tree.add_command(PlaylistGroup(name="playlist", description="Manage your playlists"))
        await self.tree.sync()
        print("✅ Slash commands synced!")

bot = MusicBot()
queues = {}

# --- AUDIO SETUP ---
print(f"🎵 Bot configured to use FFmpeg at: {ffmpeg_path}")

yt_dl_options = {
    'format': 'bestaudio/best',
    'noplaylist': 'True',
    'quiet': True,
    'default_search': 'auto'
}
ytdl = yt_dlp.YoutubeDL(yt_dl_options)

ffmpeg_options = {
    'executable': ffmpeg_path,
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -threads 1', 
    'options': '-vn'
}

# --- HELPER FUNCTIONS ---
def load_playlists_file():
    if not os.path.exists(PLAYLIST_FILE): return {}
    try:
        with open(PLAYLIST_FILE, 'r') as f: return json.loads(f.read())
    except: return {}

def save_playlists_file(data):
    with open(PLAYLIST_FILE, 'w') as f: json.dump(data, f, indent=4)

def format_time(seconds):
    if not seconds: return "Live"
    return str(datetime.timedelta(seconds=int(seconds)))

def create_progress_embed(interaction, track):
    elapsed = 0
    if track.get('start_time'): elapsed = time.time() - track['start_time']
    duration = track.get('duration_sec', 0)
    if elapsed > duration: elapsed = duration
    percent = elapsed / duration if duration > 0 else 0
    bar = "▬" * int(20 * percent) + "🔘" + "▬" * (20 - int(20 * percent))
    
    embed = discord.Embed(title=track['title'], url=track['url'], color=0x00ffcc)
    embed.set_thumbnail(url=track['thumbnail'])
    embed.add_field(name="", value=f"`{format_time(elapsed)}`  {bar}  `{format_time(duration)}`\n\n**Requested by:** {track['requester']}", inline=False)
    return embed

async def update_message_loop(interaction, message, track):
    while interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        await asyncio.sleep(10)
        try: await message.edit(embed=create_progress_embed(interaction, track))
        except: break

class MusicControls(discord.ui.View):
    def __init__(self, interaction):
        super().__init__(timeout=None)
        self.interaction = interaction
    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.secondary)
    async def pause(self, interaction, button):
        if interaction.guild.voice_client.is_playing(): interaction.guild.voice_client.pause()
        elif interaction.guild.voice_client.is_paused(): interaction.guild.voice_client.resume()
        await interaction.response.send_message("Paused/Resumed", ephemeral=True)
    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.primary)
    async def skip(self, interaction, button):
        interaction.guild.voice_client.stop()
        await interaction.response.send_message("Skipped!", ephemeral=True)
    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, interaction, button):
        queues[interaction.guild.id].clear()
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("Stopped", ephemeral=True)

async def play_next_song(interaction):
    guild_id = interaction.guild.id
    if guild_id in queues and queues[guild_id]:
        track = queues[guild_id].pop(0)
        if 'source' not in track:
            try:
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(track['url'], download=False))
                track['title'] = data['title']
                track['thumbnail'] = data.get('thumbnail', '')
                track['duration_sec'] = data.get('duration', 0)
                track['source'] = discord.FFmpegPCMAudio(data['url'], **ffmpeg_options)
            except Exception as e:
                print(f"Error loading song: {e}")
                await play_next_song(interaction)
                return

        track['start_time'] = time.time()
        voice = interaction.guild.voice_client
        voice.play(track['source'], after=lambda e: bot.loop.create_task(play_next_song(interaction)))
        
        try:
            msg = await interaction.channel.send(embed=create_progress_embed(interaction, track), view=MusicControls(interaction))
            bot.loop.create_task(update_message_loop(interaction, msg, track))
        except: pass

@bot.tree.command(name="play", description="Play a song")
async def play(interaction: discord.Interaction, search: str):
    if not interaction.user.voice: return await interaction.response.send_message("❌ Join VC first!", ephemeral=True)
    await interaction.response.send_message(f"🔍 **Searching for** `{search}`...")
    if not interaction.guild.voice_client: await interaction.user.voice.channel.connect()

    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{search}", download=False))
        if 'entries' in data: data = data['entries'][0]
        track = {'url': data['webpage_url'], 'title': data['title'], 'thumbnail': data.get('thumbnail', ''), 'duration_sec': data.get('duration', 0), 'requester': interaction.user.mention, 'source': discord.FFmpegPCMAudio(data['url'], **ffmpeg_options)}
        
        if interaction.guild.voice_client.is_playing():
            if interaction.guild.id not in queues: queues[interaction.guild.id] = []
            queues[interaction.guild.id].append(track)
            await interaction.edit_original_response(content=f"✅ Added to Queue: **{track['title']}**")
        else:
            await interaction.delete_original_response()
            track['start_time'] = time.time()
            interaction.guild.voice_client.play(track['source'], after=lambda e: bot.loop.create_task(play_next_song(interaction)))
            msg = await interaction.channel.send(embed=create_progress_embed(interaction, track), view=MusicControls(interaction))
            bot.loop.create_task(update_message_loop(interaction, msg, track))
    except Exception as e: await interaction.edit_original_response(content=f"Error: {e}")

@bot.tree.command(name="viral", description="Play Viral Hits")
async def viral(interaction: discord.Interaction):
    if not interaction.user.voice: return await interaction.response.send_message("❌ Join VC!", ephemeral=True)
    await interaction.response.send_message("🇮🇳 **Loading...**")
    if not interaction.guild.voice_client: await interaction.user.voice.channel.connect()
    await load_playlist_robust(interaction, VIRAL_PLAYLISTS, "Viral India")

async def load_playlist_robust(interaction, urls, source_name):
    loop = asyncio.get_event_loop()
    data = None
    for url in urls:
        try:
            with yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'extract_flat': True, 'quiet': True}) as ydl:
                data = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            if data and 'entries' in data: break 
        except: continue

    if not data: return await interaction.edit_original_response(content="❌ Error loading.")
    guild_id = interaction.guild.id
    if guild_id not in queues: queues[guild_id] = []
    for entry in data['entries']:
        if entry.get('url'): queues[guild_id].append({'url': entry['url'], 'title': entry.get('title', 'Hit'), 'thumbnail': '', 'duration_sec': 0, 'requester': interaction.user.mention})
    
    await interaction.edit_original_response(content=f"✅ **{source_name}** Loaded!")
    if not interaction.guild.voice_client.is_playing(): await play_next_song(interaction)

class PlaylistGroup(app_commands.Group):
    @app_commands.command(name="create", description="Create playlist")
    async def create(self, interaction: discord.Interaction, name: str):
        guild_id = interaction.guild.id
        playlist_data = []
        if guild_id in queues:
            for track in queues[guild_id]: playlist_data.append({'title': track['title'], 'url': track['url'], 'thumbnail': track.get('thumbnail',''), 'duration_sec': track.get('duration_sec',0), 'requester': interaction.user.mention})
        all_playlists = load_playlists_file()
        all_playlists[f"{interaction.user.id}_{name}"] = playlist_data
        save_playlists_file(all_playlists)
        await interaction.response.send_message(f"✅ Created **{name}**", ephemeral=True)

    @app_commands.command(name="load", description="Load playlist")
    async def load(self, interaction: discord.Interaction, name: str):
        all_playlists = load_playlists_file()
        user_key = f"{interaction.user.id}_{name}"
        if user_key not in all_playlists: return await interaction.response.send_message("❌ Not found", ephemeral=True)
        tracks = all_playlists[user_key]
        guild_id = interaction.guild.id
        if guild_id not in queues: queues[guild_id] = []
        for t in tracks: queues[guild_id].append(t)
        await interaction.response.send_message(f"✅ Loaded **{name}**")
        if interaction.guild.voice_client and not interaction.guild.voice_client.is_playing(): await play_next_song(interaction)

bot.run(os.environ["DISCORD_TOKEN"])
