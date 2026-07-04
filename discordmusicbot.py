import asyncio
import ctypes.util
import datetime
import json
import logging
import os
import random
import re
import sys
import time
from typing import Optional

import discord
import yt_dlp
from discord import FFmpegPCMAudio
from discord import app_commands, SelectOption, Interaction, ButtonStyle
from discord.ext import commands, tasks
from discord.ui import View, Button, Select
from gtts import gTTS
from gtts.lang import tts_langs

log = logging.getLogger("discordmusicbot")
if not logging.getLogger().handlers:
    discord.utils.setup_logging(level=logging.INFO)

# Anchor all paths to the script's folder so the bot also works when started
# from another working directory (e.g. a Termux:Boot script).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_FOLDER = os.path.join(BASE_DIR, "music")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
os.makedirs(MUSIC_FOLDER, exist_ok=True)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

queues = {}
now_playings = {}
downloads = {}
control_messages = {}
guild_volumes = {}
play_locks = {}
idle_since = {}
autoplay_guilds = set()

DEFAULT_VOLUME = 0.2
MAX_PLAY_RETRIES = 2
PAGE_SIZE = 25
VALID_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp")
VALID_TTS_LANGUAGES = ("af", "am", "ar", "bg", "bn", "bs", "ca", "cs", "cy", "da", "de", "el", "en", "es", "et", "eu", "fi", "fr", "fr-CA", "gl", "gu", "ha", "hi", "hr", "hu", "id", "is", "it", "iw", "ja", "jw", "km", "kn", "ko", "la", "lt", "lv", "ml", "mr", "ms", "my", "ne", "nl", "no", "pa", "pl", "pt", "pt-PT", "ro", "ru", "si", "sk", "sq", "sr", "su", "sv", "sw", "ta", "te", "th", "tl", "tr", "uk", "ur", "vi", "yue", "zh-CN", "zh-TW", "zh")

# Exit code for unrecoverable setup problems (bad config/token). run-termux.sh
# treats it as "do not restart" so a misconfigured bot can't crash-loop.
EXIT_FATAL_SETUP = 2

if not os.path.isfile(CONFIG_PATH):
    log.critical("config.json not found. Copy config.example.json to config.json and fill in your details.")
    sys.exit(EXIT_FATAL_SETUP)
try:
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
except (json.JSONDecodeError, OSError) as e:
    log.critical("config.json could not be read: %s", e)
    sys.exit(EXIT_FATAL_SETUP)

BOT_TOKEN = config.get("BOT_TOKEN")
EMBED_TITLE = config.get("EMBED_TITLE")
EMBED_DESCRIPTION = config.get("EMBED_DESCRIPTION")
EMBED_IMAGE_URL = config.get("EMBED_IMAGE_URL")
DEFAULT_TTS_LANGUAGE = config.get("DEFAULT_TTS_LANGUAGE")


def is_valid_image_url(url: str) -> bool:
    from urllib.parse import urlparse
    try:
        result = urlparse(url)
        if not all([result.scheme in ("http", "https"), result.netloc]):
            return False
        return url.lower().endswith(VALID_IMAGE_EXTENSIONS)
    except (ValueError, AttributeError):
        return False


def config_int(name, default, allow_zero=False):
    value = config.get(name)
    try:
        if isinstance(value, bool):
            raise TypeError
        value = int(value)
        if value < 0 or (value == 0 and not allow_zero):
            raise ValueError
        return value
    except (ValueError, TypeError):
        log.warning("%s missing or not a valid integer in config. Using %s as default value.", name, default)
        return default


if not BOT_TOKEN or BOT_TOKEN.strip() == "" or BOT_TOKEN == "YOUR BOT TOKEN":
    log.critical("No bot token provided in config.json. You can get your individual Bot Token by going to https://discord.com/developers/applications -> Your Application -> BOT -> TOKEN -> (RESET TOKEN)")
    sys.exit(EXIT_FATAL_SETUP)
if not EMBED_TITLE:
    EMBED_TITLE = "Music Controls"
    log.warning("EMBED_TITLE missing in config. Using default value.")
if not EMBED_DESCRIPTION:
    EMBED_DESCRIPTION = "Use the buttons below to control music."
    log.warning("EMBED_DESCRIPTION missing in config. Using default value.")
if not EMBED_IMAGE_URL or not is_valid_image_url(EMBED_IMAGE_URL):
    EMBED_IMAGE_URL = "https://fonts.gstatic.com/s/e/notoemoji/latest/1f916/512.webp"
    log.warning("EMBED_IMAGE_URL missing in config. Using default value. Make sure it is a URL with one of these extensions: %s", VALID_IMAGE_EXTENSIONS)
if not DEFAULT_TTS_LANGUAGE or DEFAULT_TTS_LANGUAGE not in VALID_TTS_LANGUAGES:
    DEFAULT_TTS_LANGUAGE = "en"
    log.warning("DEFAULT_TTS_LANGUAGE missing in config. Using default value en. Make sure it is one of these: %s", VALID_TTS_LANGUAGES)

MAX_QUEUE = config_int("MAX_SONG_QUEUE", 100)
COOLDOWN_PER_UPLOAD = config_int("COOLDOWN_PER_UPLOAD_IN_SECONDS", 10)
MESSAGE_CLUTTER_REMOVAL_DELAY = config_int("MESSAGE_CLUTTER_REMOVAL_DELAY", 5)
IDLE_DISCONNECT_MINUTES = config_int("IDLE_DISCONNECT_MINUTES", 10, allow_zero=True)

YTDL_STREAM_OPTS = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True, 'no_warnings': True}
FFMPEG_RECONNECT = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin'


def load_opus():
    # discord.py's automatic lookup (ctypes.util.find_library) usually fails on
    # Android/Termux, which silently breaks voice. Try the known locations.
    if discord.opus.is_loaded():
        return True
    candidates = []
    prefix = os.environ.get("PREFIX")  # set by Termux
    if prefix:
        candidates.append(os.path.join(prefix, "lib", "libopus.so"))
        candidates.append(os.path.join(prefix, "lib", "libopus.so.0"))
    found = ctypes.util.find_library("opus")
    if found:
        candidates.append(found)
    candidates += ["libopus.so.0", "libopus.so", "libopus.0.dylib", "opus"]
    for candidate in candidates:
        try:
            discord.opus.load_opus(candidate)
            log.info("Loaded opus library: %s", candidate)
            return True
        except OSError:
            continue
    log.warning("Could not load the opus library - voice playback will fail. On Termux run: pkg install opus")
    return False


def safe_local_path(filename):
    """Resolve a music file name to an absolute path inside MUSIC_FOLDER.

    Returns None for anything that would escape the folder. Select-menu values
    arrive from the client and cannot be trusted, so every file access based on
    user input must go through here.
    """
    if not filename or not isinstance(filename, str) or os.path.isabs(filename):
        return None
    music_root = os.path.realpath(MUSIC_FOLDER)
    path = os.path.realpath(os.path.join(music_root, filename))
    try:
        if os.path.commonpath([path, music_root]) != music_root:
            return None
    except ValueError:
        return None
    if path == music_root:
        return None
    return path


def list_music_files():
    try:
        return sorted(f for f in os.listdir(MUSIC_FOLDER) if os.path.isfile(os.path.join(MUSIC_FOLDER, f)))
    except OSError as e:
        log.warning("Could not list music folder: %s", e)
        return []


def get_volume(guild_id):
    return guild_volumes.get(guild_id, DEFAULT_VOLUME)


async def send_msg(ctxi, content, ephemeral: bool = True, view=None, delete_after: int = MESSAGE_CLUTTER_REMOVAL_DELAY):
    msg = None
    try:
        if isinstance(ctxi, discord.Interaction):
            if not ctxi.response.is_done():
                if view is not None:
                    await ctxi.response.send_message(content, ephemeral=ephemeral, view=view)
                else:
                    await ctxi.response.send_message(content, ephemeral=ephemeral)
                msg = await ctxi.original_response()
            else:
                if view is not None:
                    msg = await ctxi.followup.send(content, ephemeral=ephemeral, view=view, wait=True)
                else:
                    msg = await ctxi.followup.send(content, ephemeral=ephemeral, wait=True)
            if ephemeral and delete_after > 0 and msg is not None:
                # delay= schedules the delete in the background instead of
                # blocking the caller for the full delay
                await msg.delete(delay=delete_after)
        else:
            if view is not None:
                msg = await ctxi.send(content, view=view)
            else:
                msg = await ctxi.send(content)
            if delete_after > 0:
                await msg.delete(delay=delete_after)
                await ctxi.message.delete(delay=delete_after)
    except discord.HTTPException as e:
        log.warning("Failed to send message: %s", e)
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


class ControlPanelView(View):
    def __init__(self, guild=None):
        super().__init__(timeout=None)
        if guild is not None and guild.id in autoplay_guilds:
            self.autoplay_button.label = "🔀 Autoplay ON"

    @staticmethod
    def _guild_vc(interaction):
        if interaction.guild is None:
            return None
        return interaction.guild.voice_client

    @discord.ui.button(label="⏯ Play/Pause", custom_id="play_pause", style=ButtonStyle.success)
    async def play_pause_button(self, interaction: Interaction, button: Button):
        if interaction.guild is None:
            return
        vc = self._guild_vc(interaction)
        if vc and vc.is_playing():
            await pause_logic(interaction)
        elif vc and vc.is_paused():
            await resume_logic(interaction)
        elif vc:
            await send_msg(interaction, "❌ Nothing is playing or paused.")
        else:
            await send_msg(interaction, "❌ Not connected to a voice channel.")

    @discord.ui.button(label="⏭ Skip", custom_id="skip", style=ButtonStyle.primary)
    async def skip_button(self, interaction: Interaction, button: Button):
        if interaction.guild is None:
            return
        await skip_logic(interaction)

    @discord.ui.button(label="🔀 Autoplay", custom_id="autoplay", style=ButtonStyle.success)
    async def autoplay_button(self, interaction: Interaction, button: Button):
        if interaction.guild is None:
            return
        await autoplay_logic(interaction)

    @discord.ui.button(label="📃 Queue", custom_id="queue", style=ButtonStyle.primary)
    async def queue_button(self, interaction: Interaction, button: Button):
        if interaction.guild is None:
            return
        await show_queue(interaction)

    @discord.ui.button(label="🗑️ Clear Queue", custom_id="clearqueue", style=ButtonStyle.danger)
    async def clearqueue_button(self, interaction: Interaction, button: Button):
        if interaction.guild is None:
            return
        await clearqueue_logic(interaction)

    @discord.ui.button(label="ℹ️ Now Playing", custom_id="nowplaying", style=ButtonStyle.primary)
    async def nowplaying_button(self, interaction: Interaction, button: Button):
        if interaction.guild is None:
            return
        await show_now_playing(interaction)

    @discord.ui.button(label="🎵 Play Local", custom_id="play_local", style=ButtonStyle.secondary)
    async def play_local_button(self, interaction: Interaction, button: Button):
        if interaction.guild is None:
            return
        await list_local_files(interaction)

    @discord.ui.button(label="🔉", custom_id="vol_down", style=ButtonStyle.secondary)
    async def vol_down_button(self, interaction: Interaction, button: Button):
        if interaction.guild is None:
            return
        await nudge_volume(interaction, -0.05)

    @discord.ui.button(label="🔊", custom_id="vol_up", style=ButtonStyle.secondary)
    async def vol_up_button(self, interaction: Interaction, button: Button):
        if interaction.guild is None:
            return
        await nudge_volume(interaction, 0.05)

    @discord.ui.button(label="📤 Upload Current", custom_id="upload_current", style=ButtonStyle.secondary)
    async def upload_current_button(self, interaction: Interaction, button: Button):
        if interaction.guild is None:
            return
        await download_logic(interaction, None)

    @discord.ui.button(label="📤 From Queue", custom_id="upload_from_queue", style=ButtonStyle.secondary)
    async def upload_from_queue_button(self, interaction: Interaction, button: Button):
        if interaction.guild is None:
            return
        await download_logic(interaction, "queue")

    @discord.ui.button(label="📤 From Local", custom_id="upload_from_local", style=ButtonStyle.secondary)
    async def upload_from_local_button(self, interaction: Interaction, button: Button):
        if interaction.guild is None:
            return
        await download_logic(interaction, "local")


async def nudge_volume(interaction, delta):
    guild = interaction.guild
    vc = guild.voice_client
    if vc and vc.source and hasattr(vc.source, "volume"):
        new_volume = min(1.0, max(0.0, vc.source.volume + delta))
        vc.source.volume = new_volume
        guild_volumes[guild.id] = new_volume
        emoji = "🔊" if delta > 0 else "🔉"
        await send_msg(interaction, f"{emoji} Volume: {int(new_volume * 100)}%")
    else:
        await send_msg(interaction, "❌ Nothing is playing.")


async def show_queue(interaction):
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


async def show_now_playing(interaction):
    np = now_playings.get(interaction.guild.id)
    if np:
        elapsed = int(time.time() - np.get("start_time", time.time()))
        mins, secs = divmod(elapsed, 60)
        text = f"{np['title']} ({mins}:{secs:02d} elapsed)"
    else:
        text = "Nothing is playing."
    await send_msg(interaction, f"ℹ️ Now Playing: {text}", ephemeral=True, delete_after=0)


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
    view = ControlPanelView(guild)
    return embed, view


async def send_control_embed_to_discord_chat(ctxi):
    guild = ctxi.guild
    embed, view = await create_control_embed(guild)
    old_msg = control_messages.get(guild.id)
    if old_msg is not None:
        try:
            await old_msg.delete()
        except discord.HTTPException:
            pass
    try:
        if isinstance(ctxi, discord.Interaction):
            sent_msg = await ctxi.followup.send(embed=embed, view=view, wait=True)
        else:
            sent_msg = await ctxi.channel.send(embed=embed, view=view)
    except discord.HTTPException as e:
        log.warning("Failed to send control embed: %s", e)
        return None
    control_messages[guild.id] = sent_msg
    return sent_msg


async def update_control_embed(guild):
    msg = control_messages.get(guild.id)
    if msg is None:
        return
    embed, view = await create_control_embed(guild)
    try:
        await msg.edit(embed=embed, view=view)
    except discord.HTTPException:
        control_messages.pop(guild.id, None)


async def play_next(ctxi):
    guild = ctxi.guild
    lock = play_locks.setdefault(guild.id, asyncio.Lock())
    async with lock:
        voice_client = guild.voice_client
        if not voice_client:
            return
        if voice_client.is_playing() or voice_client.is_paused():
            return
        while True:
            queue = queues.setdefault(guild.id, [])
            if not queue and guild.id in autoplay_guilds:
                local_files = list_music_files()
                if local_files:
                    random_file = random.choice(local_files)
                    queue.append({"url": os.path.join(MUSIC_FOLDER, random_file), "title": random_file, "local": True})
            if not queue:
                now_playings[guild.id] = None
                await update_control_embed(guild)
                return
            item = queue.pop(0)
            url = item['url']
            title = item['title']
            try:
                if item.get("local"):
                    source = FFmpegPCMAudio(url, before_options='-nostdin', options='-vn')
                    now_playings[guild.id] = {"title": title, "url": url, "local": True, "start_time": time.time(), "position": 0}
                else:
                    def blocking():
                        with yt_dlp.YoutubeDL(YTDL_STREAM_OPTS) as ydl:
                            return ydl.extract_info(url, download=False)
                    info = await asyncio.to_thread(blocking)
                    audio_url = info.get('url', url)
                    now_playings[guild.id] = {"title": info.get("title", title), "url": url, "local": False, "start_time": time.time(), "position": 0}
                    source = FFmpegPCMAudio(audio_url, before_options=FFMPEG_RECONNECT, options='-vn')
                source = discord.PCMVolumeTransformer(source, volume=get_volume(guild.id))

                def after_playing(error):
                    if error:
                        log.warning("Playback of %s ended with error: %s", title, error)
                    try:
                        asyncio.run_coroutine_threadsafe(play_next(ctxi), bot.loop)
                    except RuntimeError:
                        pass
                voice_client.play(source, after=after_playing)
                await update_control_embed(guild)
                return
            except Exception as e:
                log.warning("Failed to start playback of %s: %s", title, e)
                retries = item.get("retries", 0) + 1
                if retries < MAX_PLAY_RETRIES:
                    item["retries"] = retries
                    queue.insert(0, item)
                    await asyncio.sleep(1)
                else:
                    try:
                        await send_msg(ctxi, f"⚠️ Skipping `{title}` after repeated playback failures.")
                    except Exception:
                        pass
                # loop continues with the next queue entry


async def join_logic(ctxi, clearqueue: bool = True):
    guild = ctxi.guild
    channel = ctxi_helper(ctxi, "voice_channel")
    if not channel:
        await send_msg(ctxi, "❌ You are not in a voice channel.")
        return
    await send_control_embed_to_discord_chat(ctxi)
    # Voice connects time out regularly on flaky (mobile) networks - retry once.
    for attempt in (1, 2):
        try:
            if guild.voice_client:
                await guild.voice_client.move_to(channel)
            else:
                await channel.connect(timeout=30)
            break
        except (asyncio.TimeoutError, discord.ClientException, discord.HTTPException) as e:
            log.warning("Voice connect failed (attempt %d): %s", attempt, e)
            if guild.voice_client:
                try:
                    await guild.voice_client.disconnect(force=True)
                except discord.HTTPException:
                    pass
            if attempt == 2:
                await send_msg(ctxi, f"❌ Could not connect to the voice channel: {e}")
                return
            await asyncio.sleep(2)
    idle_since.pop(guild.id, None)
    if clearqueue:
        await clearqueue_logic(ctxi)


async def leave_logic(ctxi):
    guild = ctxi.guild
    vc = guild.voice_client
    if not vc:
        await send_msg(ctxi, "❌ Not connected to a voice channel.")
        return
    try:
        await vc.disconnect(force=True)
    except discord.HTTPException as e:
        log.warning("Voice disconnect failed: %s", e)
    now_playings[guild.id] = None
    idle_since.pop(guild.id, None)
    await update_control_embed(guild)
    await send_msg(ctxi, "👋 Left the voice channel.")


async def volume_logic(ctxi, percent: int):
    guild = ctxi.guild
    if percent < 0 or percent > 100:
        await send_msg(ctxi, "❌ Volume must be between 0 and 100.")
        return
    guild_volumes[guild.id] = percent / 100
    vc = guild.voice_client
    if vc and vc.source and hasattr(vc.source, "volume"):
        vc.source.volume = percent / 100
    await send_msg(ctxi, f"🔊 Volume set to {percent}%")


async def play_logic(ctxi, url):
    guild_id = ctxi.guild.id
    queue = queues.setdefault(guild_id, [])
    try:
        # extract_flat 'in_playlist' resolves single videos fully but keeps
        # playlist entries lightweight; yt-dlp decides what is a playlist.
        ydl_opts = {'format': 'bestaudio/best', 'quiet': True, 'no_warnings': True, 'extract_flat': 'in_playlist'}

        def _extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        info = await asyncio.to_thread(_extract)
        if not info:
            await send_msg(ctxi, "❌ Could not read any video information from that link.")
            return
        if info.get('entries') is not None:
            added_titles = []
            skipped = 0
            for entry in info['entries']:
                if not entry:
                    # private/deleted playlist items come back as None
                    skipped += 1
                    continue
                if len(queue) >= MAX_QUEUE:
                    await send_msg(ctxi, f"❌ Queue is full (max {MAX_QUEUE} songs).")
                    break
                video_url = entry.get('url')
                if not video_url and entry.get('id'):
                    video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                if not video_url:
                    skipped += 1
                    continue
                queue.append({"url": video_url, "title": entry.get("title") or "Unknown Title", "local": False})
                added_titles.append(entry.get("title") or "Unknown Title")
            note = f" ({skipped} unavailable skipped)" if skipped else ""
            await send_msg(ctxi, f"🎶 Added {len(added_titles)} titles from playlist to the queue.{note}")
        else:
            if len(queue) >= MAX_QUEUE:
                await send_msg(ctxi, f"❌ Queue is full (max {MAX_QUEUE} songs).")
                return
            title = info.get("title", "Unknown Title")
            queue.append({"url": url, "title": title, "local": False})
            await send_msg(ctxi, f"🎶 Added to queue: {title}")
        vc = ctxi.guild.voice_client
        if vc and not vc.is_playing():
            await play_next(ctxi)
        else:
            await update_control_embed(ctxi.guild)
    except yt_dlp.utils.DownloadError as e:
        await send_msg(ctxi, f"❌ Failed to add video/playlist: {e}\nIf this keeps happening, yt-dlp may be outdated (run: pip install -U yt-dlp).")
    except Exception as e:
        log.exception("play_logic failed")
        await send_msg(ctxi, f"❌ Failed to add video/playlist: {e}")


async def play_local_logic(ctxi, filename):
    filepath = safe_local_path(filename)
    if not filepath or not os.path.isfile(filepath):
        await send_msg(ctxi, f"❌ File not found: {filename}")
        return
    guild_id = ctxi.guild.id
    queue = queues.setdefault(guild_id, [])
    if len(queue) >= MAX_QUEUE:
        await send_msg(ctxi, f"❌ Queue is full (max {MAX_QUEUE} songs).")
        return
    queue.append({"url": filepath, "title": os.path.basename(filepath), "local": True})
    vc = ctxi.guild.voice_client
    if not vc:
        await send_msg(ctxi, "❌ Bot is not connected to a voice channel.")
        return
    if not vc.is_playing():
        await play_next(ctxi)
    else:
        await update_control_embed(ctxi.guild)


async def list_local_files(ctxi):
    files = list_music_files()
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
        self.message = None
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
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

    def update_options(self):
        start = self.page * PAGE_SIZE
        end = start + PAGE_SIZE
        page_files = self.files[start:end]
        options = []
        for f in page_files:
            desc = f"Queue {f}"
            if len(desc) > 100:
                desc = desc[:97] + "..."
            options.append(SelectOption(label=f[:100], description=desc))
        self.select.options = options
        self.prev_button.disabled = self.page == 0
        self.next_button.disabled = end >= len(self.files)

    async def select_callback(self, interaction: Interaction):
        await interaction.response.defer()
        filename = interaction.data["values"][0]
        # select values are client-supplied: only accept what we offered
        if filename not in self.files:
            return
        await play_local_logic(self.ctx, filename)
        if self.message:
            try:
                await self.message.delete()
            except discord.HTTPException:
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
    elif queues.get(guild_id):
        await play_next(ctxi)
        await send_msg(ctxi, "⏭ Skipped current song.")
    else:
        await send_msg(ctxi, "❌ Nothing is playing to skip.")


async def pause_logic(ctxi):
    vc = ctxi.guild.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await send_msg(ctxi, "⏸ Playback paused.")
    else:
        await send_msg(ctxi, "❌ Nothing is playing.")


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
        await update_control_embed(ctxi.guild)
        await send_msg(ctxi, f"🗑️ Cleared {count} song{'s' if count != 1 else ''}.")
    except Exception as e:
        log.exception("clearqueue failed")
        await send_msg(ctxi, f"❌ Error clearing queue: {e}")


async def download_logic(ctxi, arg: str = None):
    guild_id = ctxi.guild.id
    now = time.time()
    existing = downloads.get(guild_id)
    if existing and now - existing.get("last_time", 0) < COOLDOWN_PER_UPLOAD:
        await send_msg(ctxi, f"❌ Downloads can only be used once every {COOLDOWN_PER_UPLOAD}s per guild.")
        return
    downloads[guild_id] = {"islocal": False, "string": "", "last_time": now}
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
    entry = downloads.get(guild_id)
    if not entry:
        return
    np = now_playings.get(guild_id)
    if not np:
        await send_msg(ctxi, "❌ Nothing is playing.")
        return
    if np.get("local"):
        entry["islocal"] = True
        entry["string"] = os.path.basename(np["url"])
    else:
        entry["islocal"] = False
        entry["string"] = np["url"]


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
            await interaction.response.defer()
            try:
                idx = int(interaction.data["values"][0])
            except (KeyError, IndexError, ValueError):
                return
            if not 0 <= idx < len(queue_items):
                return
            item = queue_items[idx]
            entry = downloads.get(guild_id)
            if entry:
                entry["islocal"] = False
                entry["string"] = item["url"]
            if self.message:
                try:
                    await self.message.delete()
                except discord.HTTPException:
                    pass
            self.stop()
    files = [f"{item.get('title', 'Unknown')}" for item in queue_items]
    view = UploadQueueSelect(files, ctxi)
    msg = await send_msg(ctxi, "🎵 Select a song from the queue to upload:", ephemeral=True, view=view, delete_after=0)
    view.message = msg
    return view


async def list_upload_from_local(ctxi):
    guild_id = ctxi.guild.id
    files = list_music_files()
    if not files:
        await send_msg(ctxi, "❌ Folder empty")
        return

    class UploadLocalSelect(PaginatedFileSelect):
        async def select_callback(self, interaction):
            await interaction.response.defer()
            filename = interaction.data["values"][0]
            # select values are client-supplied: only accept what we offered
            if filename not in self.files:
                return
            entry = downloads.get(guild_id)
            if entry:
                entry["islocal"] = True
                entry["string"] = filename
            if self.message:
                try:
                    await self.message.delete()
                except discord.HTTPException:
                    pass
            self.stop()
    view = UploadLocalSelect(files, ctxi)
    msg = await send_msg(ctxi, "🎵 Select a local file to upload:", ephemeral=True, view=view, delete_after=0)
    view.message = msg
    return view


async def upload_to_discord_chat(ctxi):
    guild_id = ctxi.guild.id
    entry = downloads.get(guild_id)
    if not entry or not entry["string"]:
        await send_msg(ctxi, "❌ Upload failed")
        return
    if not entry["islocal"]:
        try:
            entry["string"] = await download_to_local(entry["string"])
            entry["islocal"] = True
        except Exception as e:
            log.warning("Download for upload failed: %s", e)
            await send_msg(ctxi, f"❌ Download failed: {e}")
            return
    file_path = safe_local_path(entry["string"])
    if file_path and os.path.isfile(file_path):
        file_size = os.path.getsize(file_path)
        size_limit = ctxi.guild.filesize_limit if ctxi.guild else 8 * 1024 * 1024
        if file_size <= size_limit:
            try:
                await ctxi.channel.send(file=discord.File(file_path))
                await send_msg(ctxi, f"✅ Uploaded {entry['string']}", ephemeral=True)
            except discord.HTTPException as e:
                await send_msg(ctxi, f"❌ Upload failed: {e}")
        else:
            await send_msg(ctxi, f"❌ File too large for Discord (max {size_limit // (1024 * 1024)}MB here): {entry['string']}")
    else:
        await send_msg(ctxi, f"❌ File not found: {entry['string']}")


async def download_to_local(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(MUSIC_FOLDER, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True
    }

    def blocking_download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    full_path = await asyncio.to_thread(blocking_download)
    return os.path.basename(full_path)


async def tts_logic(ctxi, text, lang=DEFAULT_TTS_LANGUAGE, keepfile=False):
    guild_id = ctxi.guild.id
    if len(text) > 500:
        await send_msg(ctxi, "❌ TTS string too long (>500 chars).")
        return
    vc = ctxi.guild.voice_client
    if not vc:
        await send_msg(ctxi, "❌ Bot not connected to voice channel.")
        return
    if not lang:
        lang = DEFAULT_TTS_LANGUAGE
    if lang not in tts_langs():
        await send_msg(ctxi, f"❌ Unsupported language `{lang}`. Try one of: {', '.join(tts_langs().keys())}")
        return
    await send_msg(ctxi, "🤖 TTS Enabled. 🔊")
    snippet = re.sub(r'[^a-zA-Z0-9_-]', '_', text[:10])
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    tts_file = os.path.join(
        MUSIC_FOLDER,
        f"tts{lang}_{snippet}_{timestamp}_{guild_id}.mp3"
    )
    loop = asyncio.get_running_loop()

    def create_tts():
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(tts_file)
    try:
        await loop.run_in_executor(None, create_tts)
    except Exception as e:
        log.warning("gTTS generation failed: %s", e)
        await send_msg(ctxi, f"❌ TTS generation failed (network issue?): {e}")
        return
    original_track = now_playings.get(guild_id)
    current_track_data = None
    if original_track:
        current_track_data = {
            "title": original_track.get("title"),
            "url": original_track.get("url"),
            "local": original_track.get("local"),
            "position": original_track.get("position", 0)
        }
        original_volume = getattr(vc.source, "volume", get_volume(guild_id))
    else:
        original_volume = get_volume(guild_id)
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
        # runs on the voice playback thread; asyncio.Event is not thread-safe
        bot.loop.call_soon_threadsafe(done.set)
    try:
        source = FFmpegPCMAudio(tts_file, before_options='-nostdin')
        tts_audio = discord.PCMVolumeTransformer(source, volume=get_volume(guild_id))
        vc.play(tts_audio, after=after_playing)
        await done.wait()
    except discord.ClientException as e:
        await send_msg(ctxi, f"❌ Could not play TTS: {e}")
    finally:
        if not keepfile:
            try:
                os.remove(tts_file)
            except OSError:
                pass
    if current_track_data:
        now_playings[guild_id] = current_track_data
        try:
            pos = current_track_data.get("position", 0)
            if current_track_data.get("local"):
                filepath = current_track_data["url"]
                source = FFmpegPCMAudio(filepath, before_options=f"-ss {int(pos)} -nostdin", options="-vn")
            else:
                def fetch_url():
                    with yt_dlp.YoutubeDL(YTDL_STREAM_OPTS) as ydl:
                        info = ydl.extract_info(current_track_data["url"], download=False)
                        return info.get("url", current_track_data["url"])
                audio_url = await asyncio.to_thread(fetch_url)
                source = FFmpegPCMAudio(
                    audio_url,
                    before_options=f"-ss {int(pos)} {FFMPEG_RECONNECT}",
                    options="-vn"
                )
            resumed = discord.PCMVolumeTransformer(source, volume=get_volume(guild_id))

            def after_resumed(error):
                if error:
                    log.warning("Resumed track ended with error: %s", error)
                try:
                    asyncio.run_coroutine_threadsafe(play_next(ctxi), bot.loop)
                except RuntimeError:
                    pass
            vc.play(resumed, after=after_resumed)
            await asyncio.sleep(0.1)
            now_playings[guild_id]["start_time"] = time.time()
            for v in [original_volume * i / 10 for i in range(11)]:
                resumed.volume = v
                await asyncio.sleep(0.1)
        except Exception as e:
            log.warning("Could not resume track after TTS: %s", e)
            await send_msg(ctxi, f"⚠️ Could not resume track: {e}")


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
    await update_control_embed(ctxi.guild)


@tasks.loop(seconds=60)
async def idle_check():
    # Disconnect from voice after a period of inactivity - on a phone an idle
    # voice connection needlessly burns battery and data.
    if IDLE_DISCONNECT_MINUTES <= 0:
        return
    now = time.time()
    for vc in list(bot.voice_clients):
        guild = vc.guild
        active = vc.is_playing() or vc.is_paused() or queues.get(guild.id)
        if active or guild.id in autoplay_guilds:
            idle_since.pop(guild.id, None)
            continue
        started = idle_since.setdefault(guild.id, now)
        if now - started >= IDLE_DISCONNECT_MINUTES * 60:
            log.info("Disconnecting from %s after %d idle minutes.", guild.name, IDLE_DISCONNECT_MINUTES)
            try:
                await vc.disconnect(force=True)
            except discord.HTTPException as e:
                log.warning("Idle disconnect failed: %s", e)
            idle_since.pop(guild.id, None)
            now_playings[guild.id] = None
            await update_control_embed(guild)


@idle_check.before_loop
async def before_idle_check():
    await bot.wait_until_ready()


class MusicBot(commands.Bot):
    async def setup_hook(self):
        # Re-register the control panel so its buttons keep working on
        # messages that were sent before a restart.
        self.add_view(ControlPanelView())
        try:
            await self.tree.sync()
            log.info("Slash commands synced.")
        except discord.HTTPException as e:
            log.warning("Slash command sync failed: %s", e)
        idle_check.start()


bot = MusicBot(command_prefix="!", intents=intents)
tree = bot.tree


def guild_only_prefix(ctx):
    return ctx.guild is not None


@bot.command(name="controls")
@commands.check(guild_only_prefix)
async def controls_command(ctx):
    result = await send_control_embed_to_discord_chat(ctx)
    if result is None:
        await send_msg(ctx, "Something went wrong")


@bot.command(name="join")
@commands.check(guild_only_prefix)
async def join_command(ctx, clearqueue: bool = True):
    await join_logic(ctx, clearqueue)


@bot.command(name="leave")
@commands.check(guild_only_prefix)
async def leave_command(ctx):
    await leave_logic(ctx)


@bot.command(name="play")
@commands.check(guild_only_prefix)
async def play(ctx, url: str):
    await play_logic(ctx, url)


@bot.command(name="local")
@commands.check(guild_only_prefix)
async def listlocal(ctx):
    await list_local_files(ctx)


@bot.command(name="skip")
@commands.check(guild_only_prefix)
async def skip(ctx):
    await skip_logic(ctx)


@bot.command(name="pause")
@commands.check(guild_only_prefix)
async def pause(ctx):
    await pause_logic(ctx)


@bot.command(name="resume")
@commands.check(guild_only_prefix)
async def resume(ctx):
    await resume_logic(ctx)


@bot.command(name="volume")
@commands.check(guild_only_prefix)
async def volume_command(ctx, percent: int):
    await volume_logic(ctx, percent)


@bot.command(name="download")
@commands.check(guild_only_prefix)
async def download_command(ctx, arg: str = None):
    await download_logic(ctx, arg)


@bot.command(name="clear")
@commands.check(guild_only_prefix)
async def clearqueue_command(ctx):
    await clearqueue_logic(ctx)


@bot.command(name="tts")
@commands.check(guild_only_prefix)
async def tts_command(ctx, text: str, lang: str = None, keepfile: bool = False):
    await tts_logic(ctx, text, lang, keepfile)


@bot.command(name="autoplay")
@commands.check(guild_only_prefix)
async def autoplay_command(ctx):
    await autoplay_logic(ctx)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, (commands.CommandNotFound, commands.CheckFailure)):
        return
    if isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
        await send_msg(ctx, f"❌ {error}")
        return
    log.error("Command %s failed: %s", ctx.command, error)


@tree.command(name="controls", description="Show the music control embed")
@app_commands.guild_only()
async def controls_slash(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    result = await send_control_embed_to_discord_chat(interaction)
    if result is None:
        await send_msg(interaction, "Something went wrong")


@tree.command(name="join", description="Bot joins voice channel")
@app_commands.guild_only()
@app_commands.describe(clearqueue="Optional: leave empty for clear queue before joining")
async def join_slash(interaction: discord.Interaction, clearqueue: bool = True):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await join_logic(interaction, clearqueue)


@tree.command(name="leave", description="Bot leaves the voice channel")
@app_commands.guild_only()
async def leave_slash(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await leave_logic(interaction)


@tree.command(name="play", description="Play a YouTube video")
@app_commands.guild_only()
@app_commands.describe(url="YouTube video URL or: 🆕 https://www.youtube.com/playlist?list=LIST_ID")
async def play_slash(interaction: discord.Interaction, url: str):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await play_logic(interaction, url)


@tree.command(name="local", description="List all local music files available")
@app_commands.guild_only()
async def listlocal_slash(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await list_local_files(interaction)


@tree.command(name="skip", description="Skip the current song")
@app_commands.guild_only()
async def skip_slash(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await skip_logic(interaction)


@tree.command(name="pause", description="Pause playback")
@app_commands.guild_only()
async def pause_slash(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await pause_logic(interaction)


@tree.command(name="resume", description="Resume playback")
@app_commands.guild_only()
async def resume_slash(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await resume_logic(interaction)


@tree.command(name="volume", description="Set playback volume (0-100)")
@app_commands.guild_only()
@app_commands.describe(percent="Volume in percent (0-100)")
async def volume_slash(interaction: discord.Interaction, percent: app_commands.Range[int, 0, 100]):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await volume_logic(interaction, percent)


@tree.command(name="download", description="Download the currently playing song or choose from queue/local")
@app_commands.guild_only()
@app_commands.describe(arg="Optional: leave empty for current song, or 'queue' or 'local'")
async def download_slash(interaction: discord.Interaction, arg: Optional[str] = None):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await download_logic(interaction, arg)


@tree.command(name="clearqueue", description="Clears the song queue")
@app_commands.guild_only()
async def clearqueue_slash(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await clearqueue_logic(interaction)


@tree.command(name="tts", description="Send a text-to-speech message in voice channel")
@app_commands.guild_only()
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
@app_commands.guild_only()
async def autoplay_slash(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await autoplay_logic(interaction)


@tree.command(name="__clear_channel__", description="Deletes all messages in this channel")
@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_messages=True)
async def clear_channel(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    channel = interaction.channel
    try:
        deleted = await channel.purge(limit=1000)
        await send_msg(interaction, f"✅ Cleared {len(deleted)} messages.", ephemeral=True)
    except discord.HTTPException as e:
        await send_msg(interaction, f"❌ Failed to clear messages: {e}", ephemeral=True)


@bot.event
async def on_ready():
    log.info("Logged in as %s", bot.user)
    for guild in bot.guilds:
        if guild.voice_client:
            try:
                await guild.voice_client.disconnect(force=True)
            except discord.HTTPException:
                pass


def main():
    load_opus()
    try:
        bot.run(BOT_TOKEN, log_handler=None)
    except discord.PrivilegedIntentsRequired:
        log.critical(
            "The Message Content intent is not enabled for this bot. Go to "
            "https://discord.com/developers/applications -> Your Application -> Bot -> "
            "Privileged Gateway Intents and enable MESSAGE CONTENT INTENT, then restart."
        )
        sys.exit(EXIT_FATAL_SETUP)
    except discord.LoginFailure:
        log.critical("Discord rejected the bot token. Check BOT_TOKEN in config.json (and reset the token in the developer portal if unsure).")
        sys.exit(EXIT_FATAL_SETUP)


if __name__ == "__main__":
    main()
