import discord
import yt_dlp
import asyncio
import os
import json
import time
import warnings
import datetime
import re
import random
from typing import Optional
from gtts import gTTS
from discord import FFmpegPCMAudio
from discord import app_commands, SelectOption, Interaction, ButtonStyle
from discord.ext import commands, tasks
from discord.ui import View, Button, Select
from discord import Embed
from gtts.lang import tts_langs
MUSIC_FOLDER = "music"
os.makedirs(MUSIC_FOLDER, exist_ok=True)
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
queues = {}
now_playings = {}
downloads = []
control_messages = {}
if not os.path.isfile("config.json"):
    raise FileNotFoundError(
        "❌ config.json not found. Please copy config.example.json and fill in your details."
    )
with open("config.json", "r") as f:
    config = json.load(f)
BOT_TOKEN = config.get("BOT_TOKEN")
EMBED_TITLE = config.get("EMBED_TITLE")
EMBED_DESCRIPTION = config.get("EMBED_DESCRIPTION")
EMBED_IMAGE_URL = config.get("EMBED_IMAGE_URL")
VALID_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp")
MAX_QUEUE = config.get("MAX_SONG_QUEUE")
COOLDOWN_PER_UPLOAD = config.get("COOLDOWN_PER_UPLOAD_IN_SECONDS")
MESSAGE_CLUTTER_REMOVAL_DELAY = config.get("MESSAGE_CLUTTER_REMOVAL_DELAY")
DEFAULT_TTS_LANGUAGE = config.get("DEFAULT_TTS_LANGUAGE")
autoplay_guilds = set()
VALID_TTS_LANGUAGES = ("af", "am", "ar", "bg", "bn", "bs", "ca", "cs", "cy", "da", "de", "el", "en", "es", "et", "eu", "fi", "fr", "fr-CA", "gl", "gu", "ha", "hi", "hr", "hu", "id", "is", "it", "iw", "ja", "jw", "km", "kn", "ko", "la", "lt", "lv", "ml", "mr", "ms", "my", "ne", "nl", "no", "pa", "pl", "pt", "pt-PT", "ro", "ru", "si", "sk", "sq", "sr", "su", "sv", "sw", "ta", "te", "th", "tl", "tr", "uk", "ur", "vi", "yue", "zh-CN", "zh-TW", "zh")
PAGE_SIZE = 25
def is_valid_image_url(url: str) -> bool:
    from urllib.parse import urlparse
    try:
        result = urlparse(url)
        if not all([result.scheme in ("http", "https"), result.netloc]):
            return False
        return url.lower().endswith(VALID_IMAGE_EXTENSIONS)
    except:
        return False
if not BOT_TOKEN or BOT_TOKEN.strip() == "":
    raise ValueError("❌ No bot token provided in config.json You can get your individual Bot Token by going to https://discord.com/developers/applications -> Your Application -> BOT -> TOKEN -> (RESET TOKEN)")
if not EMBED_TITLE:
    EMBED_TITLE = "Music Controls"
    warnings.warn("EMBED_NAME missing in config. Using default value.")
if not EMBED_DESCRIPTION:
    EMBED_DESCRIPTION = "Use the buttons below to control music."
    warnings.warn("EMBED_DESCRIPTION missing in config. Using default value.")
if not EMBED_IMAGE_URL or not is_valid_image_url(EMBED_IMAGE_URL):
    EMBED_IMAGE_URL = "https://fonts.gstatic.com/s/e/notoemoji/latest/1f916/512.webp"
    warnings.warn(f"EMBED_IMAGE_URL missing in config. Using default value. Make sure it is a URL with one of these extensions: {VALID_IMAGE_EXTENSIONS}")
if not DEFAULT_TTS_LANGUAGE or DEFAULT_TTS_LANGUAGE not in VALID_TTS_LANGUAGES:
    DEFAULT_TTS_LANGUAGE = "en"
    warnings.warn(f"DEFAULT_TTS_LANGUAGE missing in config. Using default value en. Make sure it is one of these: {VALID_TTS_LANGUAGES}")
try:
    if isinstance(MAX_QUEUE, bool):
        raise TypeError
    MAX_QUEUE = int(MAX_QUEUE)
    if MAX_QUEUE <= 0:
        raise ValueError
except (ValueError, TypeError):
    MAX_QUEUE = 100
    warnings.warn("MAX_SONG_QUEUE missing or not a valid integer in config. Using 100 as default value.")
try:
    if isinstance(COOLDOWN_PER_UPLOAD, bool):
        raise TypeError
    COOLDOWN_PER_UPLOAD = int(COOLDOWN_PER_UPLOAD)
    if COOLDOWN_PER_UPLOAD <= 0:
        raise ValueError
except (ValueError, TypeError):
    COOLDOWN_PER_UPLOAD = 10
    warnings.warn("COOLDOWN_PER_UPLOAD_IN_SECONDS missing or not a valid integer in config. Using 10 as default value.")
try:
    if isinstance(MESSAGE_CLUTTER_REMOVAL_DELAY, bool):
        raise TypeError
    MESSAGE_CLUTTER_REMOVAL_DELAY = int(MESSAGE_CLUTTER_REMOVAL_DELAY)
    if MESSAGE_CLUTTER_REMOVAL_DELAY <= 0:
        raise ValueError
except (ValueError, TypeError):
    MESSAGE_CLUTTER_REMOVAL_DELAY = 5
    warnings.warn("MESSAGE_CLUTTER_REMOVAL_DELAY missing or not a valid integer in config. Using 5 as default value.")
def split_message(text, limit=2000):
    lines = text.split("\n")
    chunks = []
    current = ""
    for line in lines:
        if len(current) + len(line) + 1 > limit:
            chunks.append(current)
            current = line
        else:
            current += ("\n" if current else "") + line
    if current:
        chunks.append(current)
    return chunks
async def send_msg(ctxi, content, ephemeral: bool = True, view=None, delete_after: int = MESSAGE_CLUTTER_REMOVAL_DELAY):
    msg = None
    if isinstance(ctxi, discord.Interaction):
        if not ctxi.response.is_done():
            if view is not None:
                await ctxi.response.send_message(content, ephemeral=ephemeral, view=view)
            else:
                await ctxi.response.send_message(content, ephemeral=ephemeral)
            msg = await ctxi.original_response()
        else:
            if view is not None:
                msg = await ctxi.followup.send(content, ephemeral=ephemeral, view=view)
            else:
                msg = await ctxi.followup.send(content, ephemeral=ephemeral)

        if ephemeral and delete_after > 0:
            await asyncio.sleep(delete_after)
            try:
                await msg.delete()
            except:
                pass
    else:
        if view is not None:
            msg = await ctxi.send(content, view=view)
        else:
            msg = await ctxi.send(content)
        if delete_after > 0:
            await asyncio.sleep(delete_after)
            try:
                await msg.delete()
            except:
                pass
            try:
                await ctxi.message.delete()
            except:
                pass
    return msg
def ctxi_helper(ctxi, argument: str):
    is_interaction = isinstance(ctxi, discord.Interaction)
    if argument == "user":
        return ctxi.user if is_interaction else ctxi.author
    if argument == "member":
        return ctxi.user if is_interaction else ctxi.author
    if argument == "guild_name":
        return ctxi.guild.name if ctxi.guild else None
    if argument == "voice_channel":
        member = ctxi.user if is_interaction else ctxi.author
        return member.voice.channel if member and member.voice else None
    raise ValueError(f"Unknown argument: {argument}")
async def create_control_embed(guild):
    queue_count = len(queues.get(guild.id, []))
    desc = EMBED_DESCRIPTION
    if queue_count > 0:
        desc += f" | {queue_count} song{'s' if queue_count != 1 else ''} queued"
    embed = discord.Embed(
        title=EMBED_TITLE,
        description=desc,
        color=0x1DB954
    )
    embed.set_image(url=EMBED_IMAGE_URL)
    np = now_playings.get(guild.id)
    if np:
        embed.set_footer(text=f"Now Playing: {np['title']}")
    autoplay_label = "🔀 Autoplay ON" if guild.id in autoplay_guilds else "🔀 Autoplay OFF"
    view = View(timeout=None)
    view.add_item(Button(label="⏯ Play/Pause", custom_id="play_pause", style=ButtonStyle.success))
    view.add_item(Button(label="⏭ Skip", custom_id="skip", style=ButtonStyle.primary))
    view.add_item(Button(label=autoplay_label, custom_id="autoplay", style=ButtonStyle.success))
    view.add_item(Button(label="📃 Queue", custom_id="queue", style=ButtonStyle.primary))
    view.add_item(Button(label="🗑️ Clear Queue", custom_id="clearqueue", style=ButtonStyle.danger))
    view.add_item(Button(label="ℹ️ Now Playing", custom_id="nowplaying", style=ButtonStyle.primary))
    view.add_item(Button(label="🎵 Play Local", custom_id="play_local", style=ButtonStyle.secondary))
    view.add_item(Button(label="🔉", custom_id="vol_down", style=ButtonStyle.secondary))
    view.add_item(Button(label="🔊", custom_id="vol_up", style=ButtonStyle.secondary))
    view.add_item(Button(label="📤 Upload Current", custom_id="upload_current", style=ButtonStyle.secondary))
    view.add_item(Button(label="📤 From Queue", custom_id="upload_from_queue", style=ButtonStyle.secondary))
    view.add_item(Button(label="📤 From Local", custom_id="upload_from_local", style=ButtonStyle.secondary))
    return embed, view
async def send_control_embed_to_discord_chat(ctxi):
    guild = ctxi.guild
    channelid = ctxi.channel.id
    channel = guild.get_channel(channelid)
    embed, view = await create_control_embed(guild)
    if isinstance(ctxi, discord.Interaction):
        try:
            sent_msg = await ctxi.followup.send(embed=embed, view=view)
        except:
            return None
    else:
        try:
            sent_msg = await channel.send(embed=embed, view=view)
        except:
            return None
    control_messages[guild.id] = sent_msg
    return sent_msg
async def play_next(ctxi):
    guild = ctxi.guild
    if guild.id in autoplay_guilds:
        local_files = [f for f in os.listdir(MUSIC_FOLDER) if os.path.isfile(os.path.join(MUSIC_FOLDER, f))]
        if local_files:
            random_file = random.choice(local_files)
            queues.setdefault(guild.id, []).append({"url": os.path.join(MUSIC_FOLDER, random_file), "title": random_file, "local": True})
    if guild.id not in queues or not queues[guild.id]:
        now_playings[guild.id] = None
        return
    item = queues[guild.id].pop(0)
    url = item['url']
    title = item['title']
    voice_client = guild.voice_client
    if not voice_client:
        queues.setdefault(guild.id, []).insert(0, item)
        return
    try:
        if item.get("local") or (os.path.isfile(url) and MUSIC_FOLDER in url):
            source = discord.FFmpegPCMAudio(url, before_options='-nostdin', options='-vn')
            now_playings[guild.id] = {"title": title, "url": url, "local": True, "start_time": time.time(), "position": 0}
        else:
            async def fetch_info():
                def blocking():
                    ydl_opts = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        return ydl.extract_info(url, download=False)
                return await asyncio.to_thread(blocking)

            info = await fetch_info()
            audio_url = info.get('url', url)
            now_playings[guild.id] = {"title": info.get("title", title), "url": url, "local": False, "start_time": time.time(), "position": 0}
            source = discord.FFmpegPCMAudio(
                audio_url,
                before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
                options='-vn'
            )
        source = discord.PCMVolumeTransformer(source, volume=0.2)
        def after_playing(error):
            try:
                asyncio.run_coroutine_threadsafe(play_next(ctxi), bot.loop)
            except:
                pass
        voice_client.play(source, after=after_playing)
    except Exception as e:
        queues.setdefault(guild.id, []).insert(0, item)
        await asyncio.sleep(1)
        await play_next(ctxi)
async def join_logic(ctxi, clearqueue: bool = True):
    guild = ctxi.guild
    channel = ctxi_helper(ctxi, "voice_channel")
    if not channel:
        await send_msg(ctxi, "❌ You are not in a voice channel.")
        return
    await send_control_embed_to_discord_chat(ctxi)
    if guild.voice_client:
        await guild.voice_client.move_to(channel)
    else:
        await channel.connect()
    if clearqueue:
            await clearqueue_logic(ctxi)
async def play_logic(ctxi, url):
    guild_id = ctxi.guild.id
    if guild_id not in queues:
        queues[guild_id] = []
    try:
        ydl_opts = {
            'format': 'bestaudio',
            'quiet': True,
            'extract_flat': True
        }
        is_playlist = "playlist" in url
        if not is_playlist:
            ydl_opts['extract_flat'] = False
        def _extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        info = await asyncio.to_thread(_extract)
        if 'entries' in info:
            added_titles = []
            for entry in info['entries']:
                if len(queues[guild_id]) >= MAX_QUEUE:
                    await send_msg(ctxi, f"❌ Queue is full (max {MAX_QUEUE} songs).")
                    break
                video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                queues[guild_id].append({"url": video_url, "title": entry.get("title", "Unknown Title"), "local": False})
                added_titles.append(entry.get("title", "Unknown Title"))
            await send_msg(ctxi, f"🎶 Added {len(added_titles)} titles from playlist to the queue.")
        else:
            if len(queues[guild_id]) >= MAX_QUEUE:
                await send_msg(ctxi, f"❌ Queue is full (max {MAX_QUEUE} songs).")
                return
            title = info.get("title", "Unknown Title")
            queues[guild_id].append({"url": url, "title": title, "local": False})
            await send_msg(ctxi, f"🎶 Added to queue: {title}")
        vc = ctxi.guild.voice_client
        if vc and not vc.is_playing():
            await play_next(ctxi)
    except Exception as e:
        await send_msg(ctxi, f"❌ Failed to add video/playlist: {e}")
async def play_local_logic(ctxi, filename):
    filepath = os.path.join(MUSIC_FOLDER, filename)
    if not os.path.isfile(filepath):
        await send_msg(ctxi, f"❌ File not found: {filename}")
        return
    guild_id = ctxi.guild.id
    if guild_id not in queues:
        queues[guild_id] = []
    if len(queues[guild_id]) >= MAX_QUEUE:
        await send_msg(ctxi, f"❌ Queue is full (max {MAX_QUEUE} songs).")
        return
    queues[guild_id].append({"url": filepath, "title": filename, "local": True})
    vc = ctxi.guild.voice_client
    if not vc:
        await send_msg(ctxi, "❌ Bot is not connected to a voice channel.")
        return
    if not vc.is_playing():
        await play_next(ctxi)
async def list_local_files(ctxi):
    if not os.path.isdir(MUSIC_FOLDER):
        await send_msg(ctxi, "❌ Music folder not found.")
        return
    files = [f for f in os.listdir(MUSIC_FOLDER) if os.path.isfile(os.path.join(MUSIC_FOLDER, f))]
    if not files:
        await send_msg(ctxi, "No local files found.")
        return
    view = PaginatedFileSelect(files, ctxi)
    msg = await send_msg(ctxi, "🎵 Select a file to play from the dropdown:", ephemeral=True, view=view, delete_after=0)
    view.message = msg
class FileSelect(Select):
    def __init__(self, files, parent_view):
        options = [
            SelectOption(label=f[:100], description=f"File {f}"[:100])
            for f in files
        ]
        super().__init__(placeholder="Select a file", options=options)
        self.parent_view = parent_view
    async def callback(self, interaction: Interaction):
        await self.parent_view.select_callback(interaction)
class PaginatedFileSelect(View):
    def __init__(self, files, ctx):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.files = files
        self.page = 0
        self.select = FileSelect([], self)
        self.add_item(self.select)
        self.prev_button = Button(label="Previous", style=ButtonStyle.secondary)
        self.prev_button.callback = self.prev_page
        self.add_item(self.prev_button)
        self.next_button = Button(label="Next", style=ButtonStyle.secondary)
        self.next_button.callback = self.next_page
        self.add_item(self.next_button)
        self.update_options()
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass
    def update_options(self):
        start = self.page * PAGE_SIZE
        end = start + PAGE_SIZE
        page_files = self.files[start:end]
        options = []
        for f in page_files:
            desc = f"Queue {f}"
            if len(desc)>100: desc = desc[:97]+"..."
            options.append(SelectOption(label=f[:100], description=desc))
        self.select.options = options
        self.prev_button.disabled = self.page == 0
        self.next_button.disabled = end >= len(self.files)
    async def select_callback(self, interaction: Interaction):
        filename = interaction.data["values"][0]
        await play_local_logic(self.ctx, filename)
        if self.message:
            try:
                await self.message.delete()
            except:
                pass
        self.stop()
    async def prev_page(self, interaction: Interaction):
        await interaction.response.defer()
        if self.page > 0:
            self.page -= 1
            self.update_options()
            await interaction.followup.edit_message(
                message_id=interaction.message.id, view=self
            )
    async def next_page(self, interaction: Interaction):
        await interaction.response.defer()
        if (self.page + 1) * PAGE_SIZE < len(self.files):
            self.page += 1
            self.update_options()
            await interaction.followup.edit_message(
                message_id=interaction.message.id, view=self
            )
async def skip_logic(ctxi):
    vc = ctxi.guild.voice_client
    guild_id = ctxi.guild.id
    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop()
        await send_msg(ctxi, "⏭ Skipped current song.")
    elif guild_id in queues and queues[guild_id]:
        await play_next(ctxi)
        await send_msg(ctxi, "⏭ Skipped current song.")
    else:
        await send_msg(ctxi, "❌ Nothing is playing to skip.")
async def pause_logic(ctxi):
    vc = ctxi.guild.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await send_msg(ctxi, "⏸ Playback paused.")
async def resume_logic(ctxi):
    vc = ctxi.guild.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await send_msg(ctxi, "⏯ Playback resumed.")
    else:
        await send_msg(ctxi, "❌ Nothing is paused.")
async def clearqueue_logic(ctxi):
    try:
        count = len(queues.get(ctxi.guild.id, []))
        queues[ctxi.guild.id] = []
        await send_msg(ctxi, f"🗑️ Cleared {count} song{'s' if count != 1 else ''}.")
    except Exception as e:
        await send_msg(ctxi, f"❌ Error clearing queue: {e}")
async def download_logic(ctxi, arg: str = None):
    guild_id = ctxi.guild.id
    now = time.time()
    existing = next((d for d in downloads if d["guild_id"] == guild_id), None)
    if existing and now - existing.get("last_time", 0) < COOLDOWN_PER_UPLOAD:
        await send_msg(ctxi, f"❌ Downloads can only be used once every {COOLDOWN_PER_UPLOAD}s per guild.")
        return
    if not existing:
        downloads.append({"guild_id": guild_id, "islocal": False, "string": "", "last_time": now})
    else:
        existing["last_time"] = now
    if not arg:
        np = now_playings.get(guild_id)
        if np:
            await send_msg(ctxi, "📤 Trying to upload current song as file.")
            await upload_current(ctxi)
            asyncio.get_running_loop().create_task(upload_to_discord_chat(ctxi))
        else:
            await send_msg(ctxi, "❌ Nothing is playing.")
            return
    elif arg == "queue":
        view = await list_upload_from_queue(ctxi)
        if view:
            await view.wait()
            asyncio.get_running_loop().create_task(upload_to_discord_chat(ctxi))
    elif arg == "local":
        view = await list_upload_from_local(ctxi)
        if view:
            await view.wait()
            asyncio.get_running_loop().create_task(upload_to_discord_chat(ctxi))
    else:
        await send_msg(ctxi, "❌ Unrecognized Command.")
        return
async def upload_current(ctxi):
    guild_id = ctxi.guild.id
    entry = next((d for d in downloads if d["guild_id"] == guild_id), None)
    if not entry:
        return
    np = now_playings.get(guild_id)
    if not np:
        await send_msg(ctxi, "❌ Nothing is playing.")
        return
    current_url = np["url"]
    is_local_file = os.path.isfile(current_url) and MUSIC_FOLDER in current_url

    if is_local_file:
        entry["islocal"] = True
        entry["string"] = os.path.basename(current_url)
    else:
        filename_candidates = [f for f in os.listdir(MUSIC_FOLDER) if os.path.splitext(f)[0] in np["title"]]
        if filename_candidates:
            entry["islocal"] = True
            entry["string"] = filename_candidates[0]
        else:
            entry["islocal"] = False
            entry["string"] = current_url
async def list_upload_from_queue(ctxi):
    guild_id = ctxi.guild.id
    queue_items = queues.get(guild_id, [])
    if not queue_items:
        await send_msg(ctxi, "❌ Queue empty")
        return
    class UploadQueueSelect(PaginatedFileSelect):
        def update_options(self):
            start = self.page * PAGE_SIZE
            end = start + PAGE_SIZE
            page_items = queue_items[start:end]
            options = []
            for idx, item in enumerate(page_items, start=start):
                title = item.get("title", f"Song {idx}")
                options.append(SelectOption(label=title[:100], value=str(idx)))
            self.select.options = options
            self.prev_button.disabled = self.page == 0
            self.next_button.disabled = end >= len(queue_items)
        async def select_callback(self, interaction):
            idx = int(interaction.data["values"][0])
            item = queue_items[idx]
            entry = next((d for d in downloads if d["guild_id"] == guild_id), None)
            if entry:
                entry["islocal"] = False
                entry["string"] = item["url"]
            if self.message:
                try:
                    await self.message.delete()
                except:
                    pass
            self.stop()
    files = [f"{item.get('title', 'Unknown')}" for item in queue_items]
    view = UploadQueueSelect(files, ctxi)
    msg = await send_msg(ctxi, "🎵 Select a song from the queue to upload:", ephemeral=True, view=view, delete_after=0)
    view.message = msg
    return view
async def list_upload_from_local(ctxi):
    guild_id = ctxi.guild.id
    files = [f for f in os.listdir(MUSIC_FOLDER) if os.path.isfile(os.path.join(MUSIC_FOLDER, f))]
    if not files:
        await send_msg(ctxi, "❌ Folder empty")
        return
    class UploadLocalSelect(PaginatedFileSelect):
        async def select_callback(self, interaction):
            filename = interaction.data["values"][0]
            entry = next((d for d in downloads if d["guild_id"] == guild_id), None)
            if entry:
                entry["islocal"] = True
                entry["string"] = filename
            if self.message:
                try: await self.message.delete()
                except: pass
            self.stop()
    view = UploadLocalSelect(files, ctxi)
    msg = await send_msg(ctxi, "🎵 Select a local file to upload:", ephemeral=True, view=view, delete_after=0)
    view.message = msg
    return view
async def upload_to_discord_chat(ctxi):
    guild_id = ctxi.guild.id
    entry = next((d for d in downloads if d["guild_id"] == guild_id), None)
    if not entry or not entry["string"]:
        await send_msg(ctxi, "❌ Upload failed")
        return
    if not entry["islocal"]:
        entry["string"] = await download_to_local(entry["string"])
        entry["islocal"] = True
    file_path = os.path.join(MUSIC_FOLDER, entry["string"])
    if os.path.isfile(file_path):
        file_size = os.path.getsize(file_path)
        if file_size < 8 * 1024 * 1024:
            try:
                await ctxi.channel.send(file=discord.File(file_path))
                await send_msg(ctxi, f"✅ Uploaded {entry['string']}", ephemeral=True)
            except Exception as e:
                await send_msg(ctxi, f"❌ Upload failed: {e}")
        else:
            await send_msg(ctxi, f"❌ File too large for Discord (<8MB): {entry['string']}")
    else:
        await send_msg(ctxi, f"❌ File not found: {entry['string']}")
async def download_to_local(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(MUSIC_FOLDER, '%(title)s.%(ext)s'),
        'quiet': True
    }
    def blocking_download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    full_path = await asyncio.to_thread(blocking_download)
    return os.path.basename(full_path)
async def tts_logic(interaction, text, lang=DEFAULT_TTS_LANGUAGE, keepfile=False):
    guild_id = interaction.guild.id
    if len(text) > 500:
        await send_msg(interaction, "❌ TTS string too long (>500 chars).")
        return
    vc = interaction.guild.voice_client
    if not vc:
        await send_msg(interaction, "❌ Bot not connected to voice channel.")
        return

    if not lang:
        lang = DEFAULT_TTS_LANGUAGE
    if lang not in tts_langs():
        await send_msg(interaction, f"❌ Unsupported language `{lang}`. Try one of: {', '.join(tts_langs().keys())}")
        return
    await send_msg(interaction, "🤖 TTS Enabled. 🔊")
    snippet = re.sub(r'[^a-zA-Z0-9_-]', '_', text[:10])
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    tts_file = os.path.join(
        MUSIC_FOLDER,
        f"tts{lang}_{snippet}_{timestamp}_{interaction.guild.id}.mp3"
    )
    loop = asyncio.get_running_loop()
    def create_tts():
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(tts_file)
    await loop.run_in_executor(None, create_tts)
    original_track = now_playings.get(guild_id)
    current_track_data = None
    if original_track:
        current_track_data = {
            "title": original_track.get("title"),
            "url": original_track.get("url"),
            "local": original_track.get("local"),
            "position": original_track.get("position", 0)
        }
        original_volume = getattr(vc.source, "volume", 0.2)
    else:
        original_volume = 0.2
    if vc.is_playing() or vc.is_paused():
        if hasattr(vc.source, "volume"):
            for v in [original_volume * i / 10 for i in range(10, -1, -1)]:
                vc.source.volume = max(v, 0)
                await asyncio.sleep(0.1)
        if vc.is_playing() and original_track:
            original_track["position"] = original_track.get("position", 0) + time.time() - original_track.get("start_time", time.time())
            current_track_data["position"] = original_track["position"]
        vc.stop()
    done = asyncio.Event()
    def after_playing(error):
        done.set()
    source = FFmpegPCMAudio(tts_file)
    tts_audio = discord.PCMVolumeTransformer(source, volume=0.2)
    vc.play(tts_audio, after=after_playing)
    await done.wait()
    if not keepfile:
        try:
            os.remove(tts_file)
        except:
            pass
    if current_track_data:
        now_playings[guild_id] = current_track_data
        try:
            pos = current_track_data.get("position", 0)
            if current_track_data.get("local"):
                filepath = current_track_data["url"]
                source = FFmpegPCMAudio(filepath, before_options=f"-ss {int(pos)}", options="-vn")
            else:
                def fetch_url():
                    with yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'quiet': True}) as ydl:
                        info = ydl.extract_info(current_track_data["url"], download=False)
                        return info.get("url", current_track_data["url"])
                audio_url = await asyncio.to_thread(fetch_url)
                source = FFmpegPCMAudio(
                    audio_url,
                    before_options=f"-ss {int(pos)} -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin",
                    options="-vn"
                )
            resumed = discord.PCMVolumeTransformer(source, volume=0.2)
            def after_resumed(error):
                pass
            vc.play(resumed, after=after_resumed)
            await asyncio.sleep(0.1)
            now_playings[guild_id]["start_time"] = time.time()
            for v in [original_volume * i / 10 for i in range(11)]:
                resumed.volume = v
                await asyncio.sleep(0.1)
        except Exception as e:
            await send_msg(interaction, f"⚠️ Could not resume track: {e}")
async def autoplay_logic(ctxi):
    guild_id = ctxi.guild.id
    if guild_id in autoplay_guilds:
        autoplay_guilds.discard(guild_id)
        await send_msg(ctxi, "😴 Autoplay stopping after current queue.")
    else:
        autoplay_guilds.add(guild_id)
        await send_msg(ctxi, "🔀 Autoplay Activated.")
        vc = ctxi.guild.voice_client
        if vc and not vc.is_playing():
            await play_next(ctxi)
@bot.command(name="controls")
async def controls_command(ctx):
    result = await send_control_embed_to_discord_chat(ctx)
    if result is None:
        await send_msg(ctx, "Something went wrong")
@bot.command(name="join")
async def join_command(ctx, clearqueue: bool = True): 
    await join_logic(ctx, clearqueue)
@bot.command(name="play")
async def play(ctx, url: str): 
    await play_logic(ctx, url)
@bot.command(name="local")
async def listlocal(ctx):
    await list_local_files(ctx)
@bot.command(name="skip")
async def skip(ctx): 
    await skip_logic(ctx)
@bot.command(name="pause")
async def pause(ctx): 
    await pause_logic(ctx)
@bot.command(name="resume") 
async def resume(ctx): 
    await resume_logic(ctx)
@bot.command(name="download")
async def download_command(ctx, arg: str = None):
    await download_logic(ctx, arg)
@bot.command(name="clear")
async def clearqueue_command(ctx):
    await clearqueue_logic(ctx)
@bot.command(name="tts")
async def tts_command(ctx, text: str, lang: str = None, keepfile: bool = False):
    await tts_logic(ctx, text, lang, keepfile)
@bot.command(name="autoplay")
async def autoplay_command(ctx):
    await autoplay_logic(ctx)
@tree.command(name="controls", description="Show the music control embed")
async def controls_slash(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    result = await send_control_embed_to_discord_chat(interaction)
    if result is None:
        await send_msg(interaction, "Something went wrong")
@tree.command(name="join", description="Bot joins voice channel")
@app_commands.describe(clearqueue="Optional: leave empty for clear queue before joining")
async def join_slash(interaction: discord.Interaction, clearqueue : bool = True): 
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await join_logic(interaction, clearqueue)
@tree.command(name="play", description="Play a YouTube video")
@app_commands.describe(url="YouTube video URL or: 🆕 https://www.youtube.com/playlist?list=LIST_ID")
async def play_slash(interaction: discord.Interaction, url: str):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await play_logic(interaction, url) 
@tree.command(name="local", description="List all local music files available")
async def listlocal_slash(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await list_local_files(interaction)
@tree.command(name="skip", description="Skip the current song") 
async def skip_slash(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await skip_logic(interaction)
@tree.command(name="pause", description="Pause playback") 
async def pause_slash(interaction: discord.Interaction): 
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await pause_logic(interaction)
@tree.command(name="resume", description="Resume playback") 
async def resume_slash(interaction: discord.Interaction): 
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await resume_logic(interaction)
@tree.command(name="download", description="Download the currently playing song or choose from queue/local")
@app_commands.describe(arg="Optional: leave empty for current song, or 'queue' or 'local'")
async def download_slash(interaction: discord.Interaction, arg: Optional[str] = None):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await download_logic(interaction, arg)
@tree.command(name="clearqueue", description="Clears the song queue")
async def clearqueue_slash(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await clearqueue_logic(interaction)
@tree.command(name="tts", description="Send a text-to-speech message in voice channel")
@app_commands.describe(
    text="The text to speak (max 500 chars)",
    lang="Optional: ttsmodel 'en' 'de' 'com'",
    keepfile="True or False"
)
async def tts_slash(interaction: discord.Interaction, text: str, lang: Optional[str] = None, keepfile: bool = False):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await tts_logic(interaction, text, lang, keepfile)
@tree.command(name="autoplay", description="Autoplay random from local") 
async def autoplay_slash(interaction: discord.Interaction): 
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await autoplay_logic(interaction)
@tree.command(name="__clear_channel__", description="Deletes all messages in this channel",)
@app_commands.checks.has_permissions(manage_messages=True)
async def clear_channel(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    channel = interaction.channel
    try:
        deleted = await channel.purge(limit=None)
        await send_msg(interaction, f"✅ Cleared {len(deleted)} messages.", ephemeral=True)
    except Exception as e:
        await send_msg(interaction, f"❌ Failed to clear messages: {e}", ephemeral=True)
@bot.event
async def on_interaction(interaction: discord.Interaction):
    custom_id = interaction.data.get("custom_id") if interaction.data else None
    if not custom_id:
        return
    vc = interaction.guild.voice_client
    response_sent = False
    if custom_id == "play_pause":
        if vc:
            if vc.is_playing():
                await pause_logic(interaction)
                response_sent = True
            elif vc.is_paused():
                await resume_logic(interaction)
                response_sent = True
            else:
                await send_msg(interaction, "❌ Nothing is playing or paused.", ephemeral=True)
                response_sent = True
        else:
            await send_msg(interaction, "❌ Not connected to a voice channel.", ephemeral=True)
            response_sent = True
    elif custom_id == "skip":
        if vc and (vc.is_playing() or vc.is_paused()):
            await skip_logic(interaction)
            response_sent = True
        elif queues.get(interaction.guild.id, []):
            await skip_logic(interaction)
            response_sent = True
    elif custom_id == "queue":
        qlist = queues.get(interaction.guild.id, [])
        np = now_playings.get(interaction.guild.id)
        header = ""
        if np:
            header = f"▶ Now: {np['title']}\n\n"
        if not qlist:
            if header:
                await send_msg(interaction, f"📕 Queue:\n{header}(queue empty)", ephemeral=True, delete_after=0)
            else:
                await send_msg(interaction, "Queue is empty.", ephemeral=True)
            return
        text = header + "\n".join([f"{i+1}. {item['title']}" for i, item in enumerate(qlist)])
        if len(text) > 1900:
            text = text[:1900] + "\n… (discord doesn't allow more text...)"
        await send_msg(interaction, f"📕 Queue:\n{text}", ephemeral=True, delete_after=0)
        return
    elif custom_id == "nowplaying":
        np = now_playings.get(interaction.guild.id)
        if np:
            elapsed = int(time.time() - np.get("start_time", time.time()))
            mins, secs = divmod(elapsed, 60)
            text = f"{np['title']} ({mins}:{secs:02d} elapsed)"
        else:
            text = "Nothing is playing."
        await send_msg(interaction, f"ℹ️ Now Playing: {text}", ephemeral=True, delete_after=0)
        response_sent = True
        return
    elif custom_id == "play_local":
        await list_local_files(interaction)
        response_sent = True
    elif custom_id == "upload_current":
        await download_logic(interaction, None)
        response_sent = True
    elif custom_id == "upload_from_local":
        await download_logic(interaction, "local")
        response_sent = True
    elif custom_id == "upload_from_queue":
        await download_logic(interaction, "queue")
        response_sent = True
    elif custom_id == "clearqueue":
        await clearqueue_logic(interaction)
        response_sent = True
    elif custom_id == "autoplay":
        await autoplay_logic(interaction)
        response_sent = True
    elif custom_id == "vol_down":
        if vc and vc.source and hasattr(vc.source, "volume"):
            vc.source.volume = max(0.0, vc.source.volume - 0.05)
            await send_msg(interaction, f"🔉 Volume: {int(vc.source.volume * 100)}%", ephemeral=True)
        else:
            await send_msg(interaction, "❌ Nothing is playing.", ephemeral=True)
        response_sent = True
    elif custom_id == "vol_up":
        if vc and vc.source and hasattr(vc.source, "volume"):
            vc.source.volume = min(1.0, vc.source.volume + 0.05)
            await send_msg(interaction, f"🔊 Volume: {int(vc.source.volume * 100)}%", ephemeral=True)
        else:
            await send_msg(interaction, "❌ Nothing is playing.", ephemeral=True)
        response_sent = True
    if not response_sent and not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
@bot.event
async def on_ready():
    await tree.sync()
    print(f"[DEBUG] Logged in as {bot.user}")
    for guild in bot.guilds:
        if guild.voice_client:
            try:
                await guild.voice_client.disconnect(force=True)
            except:
                pass
bot.run(BOT_TOKEN)
