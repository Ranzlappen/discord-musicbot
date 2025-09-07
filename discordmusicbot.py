import discord
import yt_dlp
import asyncio
import os
import json
import warnings
from discord import app_commands, SelectOption, Interaction, ButtonStyle
from discord.ext import commands, tasks
from discord.ui import View, Button, Select
from discord import Embed
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
EMBED_ANIMATION_URL = config.get("EMBED_ANIMATION_URL")
PAGE_SIZE = 25
if not BOT_TOKEN or BOT_TOKEN.strip() == "":
    raise ValueError("❌ No bot token provided in config.json You can get your individual Bot Token by going to https://discord.com/developers/applications -> Your Application -> BOT -> TOKEN -> (RESET TOKEN)")
if not EMBED_TITLE:
    EMBED_TITLE = "Music Controls"
    warnings.warn("EMBED_NAME missing or empty in config. Using default value.")
if not EMBED_DESCRIPTION:
    EMBED_DESCRIPTION = "Use the buttons below to control music."
    warnings.warn("EMBED_DESCRIPTION missing or empty in config. Using default value.")
if not EMBED_ANIMATION_URL:
    EMBED_ANIMATION_URL = "https://fonts.gstatic.com/s/e/notoemoji/latest/1f916/512.webp"
    warnings.warn("EMBED_ANIMATION_URL missing or empty in config. Using default value.")

async def send_msg(ctxi, content, ephemeral: bool = True, view=None, delete_after: int = 5):
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
    embed = discord.Embed(
        title=EMBED_TITLE,
        description=EMBED_DESCRIPTION,
        color=0x1DB954
    )
    embed.set_image(url=EMBED_ANIMATION_URL)
    view = View()
    view.add_item(Button(label="⏯ Play/Pause", custom_id="play_pause"))
    view.add_item(Button(label="⏭ Skip", custom_id="skip"))
    view.add_item(Button(label="📃 Queue", custom_id="queue"))
    view.add_item(Button(label="ℹ️ Now Playing", custom_id="nowplaying"))
    view.add_item(Button(label="🎵 Play Local", custom_id="play_local"))
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
        if item.get("local"):
            source = discord.FFmpegPCMAudio(url, before_options='-nostdin', options='-vn')
            now_playings[guild.id] = {"title": title, "url": url}
        else:
            async def fetch_info():
                def blocking():
                    ydl_opts = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        return ydl.extract_info(url, download=False)
                return await asyncio.to_thread(blocking)
            info = await fetch_info()
            audio_url = info.get('url', url)
            now_playings[guild.id] = {"title": info.get("title", title), "url": url}
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
    except:
        queues.setdefault(guild.id, []).insert(0, item)
        await asyncio.sleep(1)
        await play_next(ctxi)
async def join_logic(ctxi):
    guild = ctxi.guild
    channel = ctxi_helper(ctxi, "voice_channel")
    if not channel:
        await send_msg(ctxi, "❌ You are not in a voice channel.")
        return
    if not guild.voice_client:
        await channel.connect()
        await send_control_embed_to_discord_chat(ctxi)
async def play_logic(ctxi, url):
    guild_id = ctxi.guild.id
    if guild_id not in queues:
        queues[guild_id] = []
    try:
        with yt_dlp.YoutubeDL({'format':'bestaudio','noplaylist':True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get("title", "Unknown Title")
    except:
        title = "Unknown Title"
    queues[guild_id].append({"url": url, "title": title})
    await send_msg(ctxi, f"🎶 Added to queue: {title}")
    vc = ctxi.guild.voice_client
    if vc and not vc.is_playing():
        await play_next(ctxi)
async def play_local_logic(ctxi, filename):
    filepath = os.path.join(MUSIC_FOLDER, filename)
    if not os.path.isfile(filepath):
        await send_msg(ctxi, f"❌ File not found: {filename}")
        return
    guild_id = ctxi.guild.id
    if guild_id not in queues:
        queues[guild_id] = []
    queues[guild_id].append({"url": filepath, "title": filename, "local": True})
    vc = ctxi.guild.voice_client
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
class PaginatedFileSelect(View):
    def __init__(self, files, ctx):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.files = files
        self.page = 0
        self.select = Select(placeholder="Select a file to play", options=[])
        self.select.callback = self.select_callback
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
        self.select.options = [
            SelectOption(label=f, description=f"Queue {f}") for f in page_files
        ]
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
        if self.page > 0:
            self.page -= 1
            self.update_options()
            await interaction.response.edit_message(view=self)
    async def next_page(self, interaction: Interaction):
        if (self.page + 1) * PAGE_SIZE < len(self.files):
            self.page += 1
            self.update_options()
            await interaction.response.edit_message(view=self)
async def skip_logic(ctxi):
    vc = ctxi.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await send_msg(ctxi, "⏭ Skipped current song.")
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

# Discord !Prefix Commands
@bot.command(name="controls")
async def controls_command(ctx):
    result = await send_control_embed_to_discord_chat(ctx)
    if result is None:
        await send_msg(ctx, "Something went wrong")
@bot.command(name="join")
async def join_command(ctx): 
    await join_logic(ctx)
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
# Discord /Slash Commands
@tree.command(name="controls", description="Show the music control embed")
async def controls_slash(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    result = await send_control_embed_to_discord_chat(interaction)
    if result is None:
        await send_msg(interaction, "Something went wrong")
@tree.command(name="join", description="Bot joins voice channel")
async def join_slash(interaction: discord.Interaction): 
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    await join_logic(interaction)
@tree.command(name="play", description="Play a YouTube video")
@app_commands.describe(url="YouTube video URL")
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
@bot.event #Handling buttons
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
        if vc and vc.is_playing():
            await skip_logic(interaction)
            response_sent = True
        else:
            await send_msg(interaction, "❌ Nothing is playing to skip.", ephemeral=True)
            response_sent = True
    elif custom_id == "queue":
        qlist = queues.get(interaction.guild.id, [])
        text = "\n".join([f"{i+1}. {item['title']}" for i, item in enumerate(qlist)]) or "Queue is empty."
        await send_msg(interaction, f"📕 Queue:\n{text}", ephemeral=True)
        response_sent = True
        return
    elif custom_id == "nowplaying":
        np = now_playings.get(interaction.guild.id)
        text = np['title'] if np else "Nothing is playing."
        await send_msg(interaction, f"ℹ️ Now Playing: {text}", ephemeral=True)
        response_sent = True
        return
    elif custom_id == "play_local":
        await list_local_files(interaction)
        response_sent = True
    if not response_sent and not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
@bot.event #Handling Startup
async def on_ready():
    await tree.sync()
    print(f"[DEBUG] Logged in as {bot.user}")
    for guild in bot.guilds:
        for channel in guild.voice_channels:
            for member in channel.members:
                if member.id == bot.user.id and not guild.voice_client:
                    try:
                        vc = await channel.connect()
                        await member.disconnect(force=True)
                    except:
                        pass
bot.run(BOT_TOKEN)