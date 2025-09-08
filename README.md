# discord-musicbot
lightweight discord music bot for youtube and local music

<img width="921" height="553" alt="image" src="https://github.com/user-attachments/assets/67482351-269a-45eb-9c87-4f7b588c2d4e" />


⚠️ Attention! Using this bot extremely heavily (multiple youtube calls per second) might not be a good idea, since YouTube does not like bots, making too many calls might get your youtube account suspended. 
Using this privately shouldn't be a problem at all though. 
Use this at your own risk.

<details>
	
<summary>I HAVE READ THE ABOVE AND KNOW THE RISK.</summary>

# Getting Started / Installation for Windows:

## 1. ⚠️Required: Download and Install https://ffmpeg.org/

## 2. on windows:
- 1. search for "Environment Variables" or "Edit the system environment variables", 
- 2. click "Environment Variables", 
- 3. select the "Path" variable under "System Variables",
- 4. click "Edit," 
- 5. and then click "New". 
- 6. Then add your new path "C:\your\install\path\ffmpeg-...full_build\bin"
- 7. finally hit OK on all 3 popups.

<img width="1842" height="898" alt="image" src="https://github.com/user-attachments/assets/2788cef1-d37c-41d4-b202-8222cf3c4866" />

## 3. Required file Structure for this Project
```
└── C:\your\path\your-folder
    ├── discordmusicbot.py
    ├── config.json
    └── music
        ├── song1.mp3
        ├── song2.mp3
        └── ...
```
## 4. Install the following dependencies with CMD.exe, Download Python from python.org, During installation, check ✅ “Add Python to PATH.” This will also install pip by default.

(Indepth Guide: https://packaging.python.org/en/latest/tutorials/installing-packages/)

```
python -m ensurepip --upgrade
```
```
pip --version
```
```
pip install -U discord.py yt-dlp gTTS
```

## 5. Create an Application here https://discord.com/developers/applications/

## 6. on that Page go to -> YOUR APPLICATION -> Bot -> RESET TOKEN, copy this token and paste it into the config.json File. (⚠️NEVER COMMIT A CONFIG.JSON with YOUR TOKEN to github, and in general don't share your token)
```
{
	"BOT_TOKEN": "YOUR TOKEN GOES HERE"
}
```

## 7. on that Page go to -> Installation
   - Installation Contexts: Guild Install
   - Default Install Settings -> Scopes: applications.commands, bot
   - Default Install Settings -> Permissions: Connect, Embed Links, Manage Messages, Send Messages, Speak, Use Embedded Activities, Use External Apps, Use Slash Commands, View Channels (If you’re testing, Admin is easiest, but for production, use least privileges.)

## 8. in Installations -> Install Link -> Discord Provided Link -> Open the Link in your browser -> Add the Bot to one of your Servers.

# Using the Bot

## 1. Start the Bot Client by opening CMD, navigate to your root folder of: discordmusicbot.py and run this command
```
python discordmusicbot.py
```
Alternatively you can create a name.bat file that contains the command "python discordmusicbot2.py"

## 2. Once the cmd runs without errors, your bot should appear as Online in your Server. ⚠️ If this command doesn't work go back up, to: [Install 4](https://github.com/Ranzlappen/discord-musicbot/edit/main/README.md#4-install-the-following-dependencies-with-cmdexe-download-python-from-pythonorg-during-installation-check--add-python-to-path-this-will-also-install-pip-by-default)

## 3. Commands are the following and can be used with either ! or / as prefix:

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

### Main Commit 3

- New Command /autoplay - toggle - plays random local files if the queue is empty 

- attempt at fixing skip logic (needs further testing, but shouldn't double skip anymore)

- download_to_local now returns only the filename to avoid doubling the folder path

- upload_from_queue dropdown now shows song titles instead of indices.

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
