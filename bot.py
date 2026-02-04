import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import datetime
import os
import json

# --- CONFIGURATION ---
ffmpeg_executable = "ffmpeg"
DEVELOPER_NAME = "Deepanshu Yadav" 
PLAYLIST_FILE = "playlists.json"  # <--- database file

# --- GLOBAL STATE ---
guild_settings = {}

def get_settings(guild_id):
    if guild_id not in guild_settings:
        guild_settings[guild_id] = {
            'volume': 1.0,
            'loop': False,
            'shuffle': False,
            'autoplay': True,
            'queue': [],
            'now_playing': None,
            'text_channel': None,
            'last_message': None
        }
    return guild_settings[guild_id]

# --- DATABASE FUNCTIONS ---
def load_playlists():
    if not os.path.exists(PLAYLIST_FILE):
        return {}
    try:
        with open(PLAYLIST_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_playlists(data):
    with open(PLAYLIST_FILE, 'w') as f:
        json.dump(data, f, indent=4)

class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        # Register the Playlist Group
        self.tree.add_command(PlaylistCommands(name="playlist", description="Manage your playlists"))
        await self.tree.sync()
        print("✅ Slash commands synced!")

bot = MusicBot()

# --- AUDIO SETUP ---
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

# --- UI: THE PRO PANEL ---
class MusicPanel(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.settings = get_settings(self.guild_id)

    # --- ROW 1 ---
    @discord.ui.button(label="Down", emoji="🔉", style=discord.ButtonStyle.primary, row=0)
    async def vol_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice = interaction.guild.voice_client
        if voice and voice.source:
            self.settings['volume'] = max(0.0, self.settings['volume'] - 0.1)
            voice.source.volume = self.settings['volume']
            await interaction.response.send_message(f"🔉 Volume: {int(self.settings['volume']*100)}%", delete_after=2)
        else: await interaction.response.defer()

    @discord.ui.button(label="Back", emoji="⏮️", style=discord.ButtonStyle.primary, row=0)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice = interaction.guild.voice_client
        if voice and voice.is_playing():
            voice.stop()
            await interaction.response.send_message("⏮️ Replaying...", delete_after=2)

    @discord.ui.button(label="Pause", emoji="⏸️", style=discord.ButtonStyle.primary, row=0)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice = interaction.guild.voice_client
        if voice.is_playing():
            voice.pause()
            button.emoji = "▶️"
            button.label = "Resume"
        else:
            voice.resume()
            button.emoji = "⏸️"
            button.label = "Pause"
        await interaction.response.edit_message(view=self)

    # --- ROW 2 ---
    @discord.ui.button(label="Skip", emoji="⏭️", style=discord.ButtonStyle.primary, row=1)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice = interaction.guild.voice_client
        if voice:
            voice.stop()
            await interaction.response.send_message("⏭️ Skipped!", delete_after=2)

    @discord.ui.button(label="Up", emoji="🔊", style=discord.ButtonStyle.primary, row=1)
    async def vol_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice = interaction.guild.voice_client
        if voice and voice.source:
            self.settings['volume'] = min(2.0, self.settings['volume'] + 0.1)
            voice.source.volume = self.settings['volume']
            await interaction.response.send_message(f"🔊 Volume: {int(self.settings['volume']*100)}%", delete_after=2)
        else: await interaction.response.defer()

    # --- ROW 3 ---
    @discord.ui.button(label="Shuffle", emoji="🔀", style=discord.ButtonStyle.secondary, row=2)
    async def shuffle_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.settings['shuffle'] = not self.settings['shuffle']
        button.style = discord.ButtonStyle.green if self.settings['shuffle'] else discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Loop", emoji="🔁", style=discord.ButtonStyle.secondary, row=2)
    async def loop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.settings['loop'] = not self.settings['loop']
        button.style = discord.ButtonStyle.green if self.settings['loop'] else discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Stop", emoji="⏹️", style=discord.ButtonStyle.danger, row=2)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice = interaction.guild.voice_client
        if voice:
            settings = get_settings(interaction.guild.id)
            settings['queue'].clear()
            settings['now_playing'] = None
            await voice.disconnect()
            
            if settings['last_message']:
                try: await settings['last_message'].delete()
                except: pass
                
            await interaction.response.send_message("⏹️ Stopped.", delete_after=5)

    # --- ROW 4 ---
    @discord.ui.button(label="AutoPlay", emoji="🔄", style=discord.ButtonStyle.secondary, row=3)
    async def autoplay_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.settings['autoplay'] = not self.settings['autoplay']
        button.style = discord.ButtonStyle.green if self.settings['autoplay'] else discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Queue", emoji="📜", style=discord.ButtonStyle.secondary, row=3)
    async def playlist(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = get_settings(interaction.guild.id)
        queue = settings['queue']
        if not queue:
            return await interaction.response.send_message("📜 Queue is empty.", ephemeral=True)
        
        desc = ""
        for i, t in enumerate(queue[:10]):
            desc += f"`{i+1}.` {t['title']}\n"
        
        embed = discord.Embed(title="📜 Queue", description=desc, color=0x2b2d31)
        await interaction.response.send_message(embed=embed, ephemeral=True)


def create_panel_embed(track):
    embed = discord.Embed(description=f"💿 **{track['title']}**", color=0x2b2d31)
    embed.set_author(name="MUSIC PANEL", icon_url=track['thumbnail'])
    embed.add_field(name="🙋 Requested By", value=track['requester'], inline=True)
    embed.add_field(name="⏳ Duration", value=track['duration'], inline=True)
    embed.add_field(name="🎵 Author", value=track['uploader'], inline=True)
    embed.set_thumbnail(url=track['thumbnail'])
    embed.set_footer(text=f"Dev: {DEVELOPER_NAME} • Enjoy the music! 🎧")
    return embed

async def play_next(guild, voice):
    settings = get_settings(guild.id)
    
    # 1. DELETE OLD PANEL
    if settings['last_message']:
        try: await settings['last_message'].delete()
        except: pass
        settings['last_message'] = None

    # 2. GET NEXT SONG
    track = None
    if settings['loop'] and settings['now_playing']:
        track = settings['now_playing']
    elif settings['queue']:
        track = settings['queue'].pop(0)
    
    # 3. IF NO SONG
    if not track:
        settings['now_playing'] = None
        if settings['text_channel']:
            try: await settings['text_channel'].send("✅ **Queue Finished.**", delete_after=10)
            except: pass
        return

    # 4. PLAY SONG
    settings['now_playing'] = track
    try:
        audio_source = discord.FFmpegPCMAudio(track['url'], **ffmpeg_options)
        transformer = discord.PCMVolumeTransformer(audio_source, volume=settings['volume'])
        
        voice.play(transformer, after=lambda e: bot.loop.create_task(play_next(guild, voice)))
        
        # Send Panel
        if settings['text_channel']:
            embed = create_panel_embed(track)
            view = MusicPanel(guild.id)
            msg = await settings['text_channel'].send(embed=embed, view=view)
            settings['last_message'] = msg
            
    except Exception as e:
        print(f"Error playing: {e}")

# --- COMMANDS ---

@bot.tree.command(name="play", description="Play a song")
async def play(interaction: discord.Interaction, search: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ Join VC first!", ephemeral=True)

    await interaction.response.send_message(f"🔍 **Searching:** `{search}`...", delete_after=5)
    
    if not interaction.guild.voice_client:
        await interaction.user.voice.channel.connect()

    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{search}", download=False))
        if 'entries' in data: data = data['entries'][0]

        duration_str = str(datetime.timedelta(seconds=int(data.get('duration', 0))))
        track = {
            'url': data['url'],
            'title': data['title'],
            'duration': duration_str,
            'uploader': data.get('uploader', 'Unknown'),
            'thumbnail': data.get('thumbnail', ''),
            'requester': interaction.user.mention
        }
        
        settings = get_settings(interaction.guild.id)
        settings['text_channel'] = interaction.channel
        voice = interaction.guild.voice_client
        
        if voice.is_playing():
            settings['queue'].append(track)
            await interaction.channel.send(f"✅ **Queued:** {track['title']}", delete_after=5)
        else:
            settings['now_playing'] = track
            audio_source = discord.FFmpegPCMAudio(track['url'], **ffmpeg_options)
            transformer = discord.PCMVolumeTransformer(audio_source, volume=settings['volume'])
            
            voice.play(transformer, after=lambda e: bot.loop.create_task(play_next(interaction.guild, voice)))
            
            embed = create_panel_embed(track)
            view = MusicPanel(interaction.guild.id)
            msg = await interaction.channel.send(embed=embed, view=view)
            settings['last_message'] = msg

    except Exception as e:
        await interaction.channel.send(f"❌ Error: {e}", delete_after=10)

@bot.tree.command(name="skip", description="Skip current song")
async def skip(interaction: discord.Interaction):
    voice = interaction.guild.voice_client
    if voice and voice.is_playing():
        voice.stop()
        await interaction.response.send_message("⏭️ **Skipped!**", delete_after=2)
    else:
        await interaction.response.send_message("❌ Nothing to skip.", ephemeral=True)

@bot.tree.command(name="stop", description="Stop and disconnect")
async def stop(interaction: discord.Interaction):
    voice = interaction.guild.voice_client
    if voice:
        settings = get_settings(interaction.guild.id)
        settings['queue'].clear()
        settings['now_playing'] = None
        
        await voice.disconnect()
        
        if settings['last_message']:
            try: await settings['last_message'].delete()
            except: pass
            
        await interaction.response.send_message("🛑 **Stopped.**", delete_after=5)
    else:
        await interaction.response.send_message("❌ Not connected.", ephemeral=True)

@bot.tree.command(name="playlists", description="Show all playlists")
async def playlists(interaction: discord.Interaction):
    data = load_playlists()
    user_key_start = f"{interaction.user.id}_"
    
    my_playlists = []
    for key in data:
        if key.startswith(user_key_start):
            name = key.replace(user_key_start, "")
            count = len(data[key])
            my_playlists.append(f"• **{name}** ({count} songs)")
            
    if not my_playlists:
        await interaction.response.send_message("📂 You have no playlists.", ephemeral=True)
    else:
        desc = "\n".join(my_playlists)
        embed = discord.Embed(title="📂 Your Playlists", description=desc, color=0x2b2d31)
        await interaction.response.send_message(embed=embed, ephemeral=True)

# --- PLAYLIST GROUP COMMANDS ---
class PlaylistCommands(app_commands.Group):
    
    @app_commands.command(name="create", description="Create a new playlist")
    async def create(self, interaction: discord.Interaction, name: str):
        data = load_playlists()
        key = f"{interaction.user.id}_{name}"
        
        if key in data:
            return await interaction.response.send_message(f"❌ Playlist **{name}** already exists!", ephemeral=True)
            
        data[key] = []
        save_playlists(data)
        await interaction.response.send_message(f"✅ Created playlist **{name}**!", ephemeral=True)

    @app_commands.command(name="delete", description="Delete a playlist")
    async def delete(self, interaction: discord.Interaction, name: str):
        data = load_playlists()
        key = f"{interaction.user.id}_{name}"
        
        if key not in data:
            return await interaction.response.send_message(f"❌ Playlist **{name}** not found!", ephemeral=True)
            
        del data[key]
        save_playlists(data)
        await interaction.response.send_message(f"🗑️ Deleted **{name}**.", ephemeral=True)

    @app_commands.command(name="add", description="Add a song to a playlist")
    async def add(self, interaction: discord.Interaction, playlist: str, song: str):
        data = load_playlists()
        key = f"{interaction.user.id}_{playlist}"
        
        if key not in data:
            return await interaction.response.send_message(f"❌ Playlist **{playlist}** doesn't exist. Create it first!", ephemeral=True)

        await interaction.response.send_message(f"🔍 Searching: `{song}`...", ephemeral=True)
        
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{song}", download=False))
            if 'entries' in info: info = info['entries'][0]
            
            duration_str = str(datetime.timedelta(seconds=int(info.get('duration', 0))))
            track_data = {
                'url': info['url'],
                'title': info['title'],
                'duration': duration_str,
                'uploader': info.get('uploader', 'Unknown'),
                'thumbnail': info.get('thumbnail', ''),
                'requester': interaction.user.mention
            }
            
            data[key].append(track_data)
            save_playlists(data)
            
            await interaction.edit_original_response(content=f"✅ Added **{info['title']}** to **{playlist}**!")
            
        except Exception as e:
            await interaction.edit_original_response(content=f"❌ Error finding song: {e}")

    @app_commands.command(name="play", description="Load and play a playlist")
    async def play_playlist(self, interaction: discord.Interaction, playlist: str):
        if not interaction.user.voice:
            return await interaction.response.send_message("❌ Join VC first!", ephemeral=True)
            
        data = load_playlists()
        key = f"{interaction.user.id}_{playlist}"
        
        if key not in data or not data[key]:
            return await interaction.response.send_message(f"❌ Playlist **{playlist}** is empty or missing.", ephemeral=True)

        await interaction.response.send_message(f"📂 Loading **{playlist}**...", delete_after=5)

        if not interaction.guild.voice_client:
            await interaction.user.voice.channel.connect()

        settings = get_settings(interaction.guild.id)
        settings['text_channel'] = interaction.channel
        
        # Add all songs to queue
        count = 0
        for track in data[key]:
            # We clone the track object so modifying it doesn't break the saved file
            # Update requester to current user
            new_track = track.copy()
            new_track['requester'] = interaction.user.mention
            settings['queue'].append(new_track)
            count += 1
            
        await interaction.channel.send(f"✅ Loaded **{count}** songs from **{playlist}**!", delete_after=5)

        # Start playing if not already
        if not interaction.guild.voice_client.is_playing():
            await play_next(interaction.guild, interaction.guild.voice_client)

bot.run(os.environ["DISCORD_TOKEN"])
