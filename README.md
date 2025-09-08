# discord-musicbot
lightweight discord music bot for youtube and local music

⚠️ Attention! Using this bot extremely heavily (multiple youtube calls per second) might not be a good idea, since YouTube does not like bots, making too many calls might get your youtube account suspended. 
Using this privately shouldn't be a problem at all though. 
Use this at your own risk.

<details>
	
<summary>I HAVE READ THE ABOVE AND KNOW THE RISK.</summary>

# Getting Started / Installation for Windows:

1. ⚠️Required: Download and Install https://ffmpeg.org/

2. on windows search for "Environment Variables" or "Edit the system environment variables," click "Environment Variables," select the "Path" variable under "System Variables," click "Edit," and then click "New". Then add this new path "C:\your\install\path\ffmpeg-...\bin" at the bottom

3. Required file Structure for this Project
```
└── C:\your\path\your-folder
    ├── discordmusicbot.py
    ├── config.json
    └── music
        ├── song1.mp3
        ├── song2.mp3
        └── ...
```
4. Install the following dependencies with CMD.exe, Download Python from python.org, During installation, check ✅ “Add Python to PATH.” This will also install pip by default.
    (Indepth Guide: https://packaging.python.org/en/latest/tutorials/installing-packages/)
```
python -m ensurepip --upgrade //run this command if python is installed but pip isn't
pip --version //checks if pip is installed
pip install -U discord.py yt-dlp
```

5. Create an Application here https://discord.com/developers/applications/

6. on that Page go to -> YOUR APPLICATION -> Bot -> RESET TOKEN, copy this token and paste it into the config.json File
```
{
	"BOT_TOKEN": "YOUR TOKEN GOES HERE",
	...
	...
}
```

7. on that Page go to -> Installation
   - Installation Contexts: Guild Install
   - Default Install Settings -> Scopes: applications.commands, bot
   - Default Install Settings -> Permissions: Connect, Embed Links, Manage Messages, Send Messages, Speak, Use Embedded Activities, Use External Apps, Use Slash Commands, View Channels (or if you are lazy Admin)

8. in Installations -> Install Link -> Discord Provided Link -> Open the Link in your browser -> Add the Bot to one of your Servers.

# Using the Bot

1. Start the Bot Client by opening CMD, navigate to your root folder of: discordmusicbot.py and run this command
```
python discordmusicbot.py
Alternatively if you want an .exe use
pyinstaller --noconsole --onefile discordmusicbot.py
```
3. Once the cmd runs without errors, your bot should appear as Online in your Server. ⚠️ If this command doesn't work go back up, to: "Install 4"

4. Commands are the following and can be used with either ! or / as prefix:
# Bot Slash Commands

### Music Controls
- **`/controls`** - Show the music control embed.

### Voice Channel
- **`/join [clearqueue]`** - Bot joins your voice channel.  
  Optional parameter: `clearqueue` (default: `True`) – clears the queue before joining.

### Playback
- **`/play <url>`** - Play a YouTube video or playlist.  
  Parameter: `url` – YouTube video URL or playlist URL (`https://www.youtube.com/playlist?list=LIST_ID`).

- **`/local`** - List all local music files available.

- **`/skip`** - Skip the current song.

- **`/pause`** - Pause playback.

- **`/resume`** - Resume playback.

- **`/clearqueue`** - Clears the song queue.

### Downloads
- **`/download [arg]`** - Download the currently playing song or choose from queue/local.  
  Optional parameter: `arg` – leave empty for current song, or `'queue'` / `'local'`.

### Text-to-Speech
- **`/tts <text> [lang] [keepfile]`** - Send a text-to-speech message in the voice channel.  
  Parameters:  
  - `text` (max 500 chars) – text to speak  
  - `lang` – optional, TTS model: `'en'`, `'de'`, `'com'`  
  - `keepfile` – `True` or `False`

### Administration
- **`/__clear_channel__`** - Deletes all messages in the current channel.  
  Requires **Manage Messages** permission.

</details>

<details>
	
<summary>changelog</summary>
	
### Main Commit 2
	
- New Command: Clear Queue

- New Command: Upload file to discord chat (from queue/from local/from currently playing youtube)

- New Command: TTS that pauses playback of music and can optionally be downloaded as sound file, optional parameter for language, default language can be set in config

- play command now accepts youtube playlists in the form of: https://www.youtube.com/playlist?list=YOUR_LIST_ID

- new config data like max queue size, cooldown for uploads, default tts language, message clutter removal delay 

- some config validations to reduce errors

- some minor fixes/improvements/edge cases

- accounted for some discord limitations like 2000char limit in messages, 100char limit in dropdown options, 25option limit in dropdowns

### Main Commit 1

- Initial Version.

</details>
