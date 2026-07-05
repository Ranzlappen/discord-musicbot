<p align="center">
  <img src="assets/logo.png" width="128" height="128" alt="discord-musicbot logo">
</p>

# discord-musicbot
lightweight discord music bot for youtube and local music

> The logo in `assets/logo.png` (512×512) is part of the shared "icon
> universe". Use it as the bot's avatar (Discord Developer Portal → Bot →
> Icon) and, if you want it in the now-playing embed, point
> `EMBED_IMAGE_URL` in `config.json` at its raw URL once this lands on the
> default branch.

<img width="921" height="553" alt="image" src="https://github.com/user-attachments/assets/67482351-269a-45eb-9c87-4f7b588c2d4e" />


⚠️ Attention! Using this bot extremely heavily (multiple youtube calls per second) might not be a good idea, since YouTube does not like bots, making too many calls might get your youtube account suspended. 
Using this privately shouldn't be a problem at all though. 
Use this at your own risk.

<details>
	
<summary>I HAVE READ THE ABOVE AND KNOW THE RISK.</summary>



first experimental pre-release https://github.com/Ranzlappen/discord-musicbot/releases/tag/pre


if you use this, you can skip part 1,2,3,4 of the installation, and 1,2 of the use guide.

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
└── C:\your\path\your-folder
├── discordmusicbot.py
├── config.json
└── music
├── song1.mp3
├── song2.mp3
└── ...
## 4. Install the following dependencies with CMD.exe, Download Python from python.org, During installation, check ✅ "Add Python to PATH." This will also install pip by default.

(Indepth Guide: https://packaging.python.org/en/latest/tutorials/installing-packages/)
python -m ensurepip --upgrade

pip --version

pip install -U discord.py yt-dlp gTTS
## 5. Create an Application here https://discord.com/developers/applications/

## 6. on that Page go to -> YOUR APPLICATION -> Bot -> RESET TOKEN, copy this token and paste it into the config.json File. (⚠️NEVER COMMIT A CONFIG.JSON with YOUR TOKEN to github, and in general don't share your token)

⚠️ On the same **Bot** page, under **Privileged Gateway Intents**, enable
**MESSAGE CONTENT INTENT**. The bot needs it for the `!` prefix commands and
will exit at startup with an explanatory message if it is missing.

(right now the .exe will crash if there is no valid bot token in the config)
{
"BOT_TOKEN": "YOUR TOKEN GOES HERE"
}
## 7. on that Page go to -> Installation
   - Installation Contexts: Guild Install
   - Default Install Settings -> Scopes: applications.commands, bot
   - Default Install Settings -> Permissions: Connect, Embed Links, Manage Messages, Send Messages, Speak, Use Embedded Activities, Use External Apps, Use Slash Commands, View Channels (If you're testing, Admin is easiest, but for production, use least privileges.)

## 8. in Installations -> Install Link -> Discord Provided Link -> Open the Link in your browser -> Add the Bot to one of your Servers.

# Run on Android (Termux)

You can host the bot directly on an Android phone with [Termux](https://termux.dev).
This is the only phone-native way to run it — the bot needs an always-on process
(it holds a live connection to Discord and stays in voice channels), so it can't
run on services like GitHub Actions. Still create your Discord application and bot
token first (steps 5–8 above).

### 1. Install Termux
Install **Termux from [F-Droid](https://f-droid.org/en/packages/com.termux/)**
(the Google Play version is deprecated and broken). Optionally also install
**[Termux:Boot](https://f-droid.org/en/packages/com.termux.boot/)** if you want
the bot to auto-start when the phone reboots.

### 2. Get the code and run the setup script
Open Termux and run:
```sh
pkg install -y git
git clone https://github.com/Ranzlappen/discord-musicbot
cd discord-musicbot
bash setup-termux.sh
```
`setup-termux.sh` installs Python, FFmpeg, **Opus** (discord.py cannot find
Android's opus library on its own — the bot loads it from Termux's lib folder),
and all Python dependencies (including **PyNaCl**, which voice playback
requires), then creates a `config.json` for you and smoke-tests the installed
packages.

### 3. Add your bot token
Edit the generated `config.json` and paste your token into `BOT_TOKEN`:
```sh
nano config.json
```
(In nano: paste the token, then `Ctrl+O`, `Enter` to save, `Ctrl+X` to exit.)
⚠️ Never commit a `config.json` containing your real token.

### 4. Start the bot
```sh
bash run-termux.sh
```
This holds a **wake-lock** so the bot keeps running while the screen is off,
restarts it automatically if it crashes (with increasing backoff, and it will
NOT restart-loop on a bad token/config), and mirrors all output to `bot.log`
for diagnosing crashes that happen while the phone is in your pocket.
Press `Ctrl+C` to stop.

### 5. Optional: auto-start on boot (Termux:Boot)
Install **Termux:Boot** from F-Droid, open it once, then:
```sh
mkdir -p ~/.termux/boot
cp termux-boot-start.sh ~/.termux/boot/
```
The bot now starts automatically after every phone reboot. If the repo is not
in `~/discord-musicbot`, edit `BOT_DIR` in the copied script.

### When YouTube stops working
YouTube changes constantly and old `yt-dlp` versions break — this is the most
common reason a long-running install suddenly can't play URLs. Fix it with:
```sh
bash run-termux.sh --update
```
(updates yt-dlp, then starts the bot as usual).

### Caveats
- Exempt Termux from **battery optimization** (Android Settings → Apps → Termux →
  Battery → Unrestricted), or the system may kill it.
- If you force-close Termux or the phone runs out of battery, the bot stops.
  For truly reliable 24/7 uptime, a small always-on host (VPS / Raspberry Pi) is
  better — but Termux works well for personal use.
- To save battery and data, the bot leaves the voice channel after 10 idle
  minutes by default (configurable via `IDLE_DISCONNECT_MINUTES` in
  `config.json`, `0` disables it).
- Heavy YouTube usage still carries the risks noted at the top of this README.

> On desktop/server (Linux/macOS/Windows) you can install the Python
> dependencies the same way with `pip install -U -r requirements.txt`, plus
> FFmpeg from [ffmpeg.org](https://ffmpeg.org/). Note this list adds **PyNaCl**,
> which the old `pip install -U discord.py yt-dlp gTTS` line above omits and
> which is required for voice.

# Using the Bot

## 1. Start the Bot Client by opening CMD, navigate to your root folder of: discordmusicbot.py and run this command
python discordmusicbot.py
Alternatively you can create a name.bat file that contains the command "python discordmusicbot2.py"

## 2. Once the cmd runs without errors, your bot should appear as Online in your Server. ⚠️ If this command doesn't work go back up, to: [Install 4](https://github.com/Ranzlappen/discord-musicbot/edit/main/README.md#4-install-the-following-dependencies-with-cmdexe-download-python-from-pythonorg-during-installation-check--add-python-to-path-this-will-also-install-pip-by-default)

## 2.5 if you are using the 7z file, just unpack it and launch the .exe (note that the program will instantly crash if no valid bot token is inside of the config)

## 3. Commands are the following and can be used with either ! or / as prefix:

### Music Controls
- **`/controls`** - Show the music control embed with color-coded buttons, now-playing footer, and queue count.

### Voice Channel
- **`/join [clearqueue]`** - Bot joins your voice channel.
  Optional parameter: `clearqueue` (default: `True`) – clears the queue before joining.

- **`/leave`** - Bot leaves the voice channel. (It also leaves on its own after
  `IDLE_DISCONNECT_MINUTES` of inactivity — default 10, set `0` in `config.json`
  to disable.)

### Playback
- **`/play <url>`** - Play a YouTube video or playlist.
  Parameter: `url` – YouTube video URL or playlist URL (`https://www.youtube.com/playlist?list=LIST_ID`).

- **`/local`** - List all local music files available.

- **`/skip`** - Skip the current song.

- **`/pause`** - Pause playback.

- **`/resume`** - Resume playback.

- **`/autoplay`** - Toggle autoplay mode (per server). Plays random local files when the queue is empty.

- **`/volume <percent>`** - Set playback volume (0–100). The value is remembered per server for the next songs.

- **`/clearqueue`** - Clears the song queue (shows how many songs were removed).

### Downloads
- **`/download [arg]`** - Download the currently playing song or choose from queue/local.
  Optional parameter: `arg` – leave empty for current song, or `'queue'` / `'local'`.

### Text-to-Speech
- **`/tts <text> [lang] [keepfile]`** - Send a text-to-speech message in the voice channel.
  Parameters:
  - `text` (max 500 chars) – text to speak
  - `lang` – optional, TTS model: `'en'`, `'de'`, `'com'`
  - `keepfile` – `True` or `False`
<details>
	<summary>All languages for lang parameter</summary>
	
	af, am, ar, bg, bn, bs, ca, cs, cy, da, de, el, en, es, et, eu, fi, fr, fr-CA, gl, gu, ha, hi, hr, hu, id, is, it, iw, ja, jw, km, kn, ko, la, lt, lv, ml, mr, ms, my, ne, nl, no, pa, pl, pt, pt-PT, ro, ru, si, sk, sq, sr, su, sv, sw, ta, te, th, tl, tr, uk, ur, vi, yue, zh-CN, zh-TW, zh
</details>


### Control Panel Buttons

The `/controls` embed provides these interactive buttons:

| Button | Color | Action |
|--------|-------|--------|
| ⏯ Play/Pause | Green | Toggle pause/resume |
| ⏭ Skip | Blue | Skip current song |
| 🔀 Autoplay ON/OFF | Green | Toggle autoplay (label reflects state) |
| 📃 Queue | Blue | Show queue with current track at top |
| 🗑️ Clear Queue | Red | Clear queue (shows count) |
| ℹ️ Now Playing | Blue | Show current track with elapsed time |
| 🎵 Play Local | Grey | Browse and play local files |
| 🔉 / 🔊 | Grey | Volume down / up (±5%) |
| 📤 Upload Current | Grey | Upload currently playing song |
| 📤 From Queue | Grey | Upload a song from the queue |
| 📤 From Local | Grey | Upload a local file |

### Administration
- **`/__clear_channel__`** - Deletes all messages in the current channel.
  Requires **Manage Messages** permission.

</details>

<details>
	
<summary>changelog</summary>

### Main Commit 5 — hardening + Termux compatibility

**Security:**
- Dropdown selections (play local / upload local / upload from queue) are now
  validated server-side — malformed clients can no longer request files outside
  the `music/` folder
- `/__clear_channel__` purges at most 1000 messages per invocation

**Bug fixes & robustness:**
- Songs that repeatedly fail to start are skipped instead of retrying forever
- TTS no longer risks hanging forever (playback-finished signal was not thread-safe)
- Control panel buttons are handled by a persistent view (no more race with
  dropdown menus; buttons keep working after a bot restart)
- Commands no longer stall for the message-cleanup delay before finishing
- Slash commands sync once at startup instead of on every reconnect
- Playlists with private/deleted videos no longer crash `/play` (they're skipped and counted)
- Voice connects retry once and report failures instead of failing silently
- Upload size limit follows the server's actual Discord limit instead of a hardcoded 8MB
- Friendly startup errors for bad tokens, missing Message Content intent, and broken config
- Proper logging (also to `bot.log` via run-termux.sh) instead of prints
- Control embed refreshes its queue count / now-playing footer as playback progresses

**New:**
- `/leave` command
- Idle auto-disconnect after `IDLE_DISCONNECT_MINUTES` (default 10, `0` = off) — saves phone battery/data
- `/volume <0-100>` with per-server volume memory
- `run-termux.sh --update` refreshes yt-dlp; crash restarts now back off; output logged to `bot.log`
- `termux-boot-start.sh` for auto-start via Termux:Boot
- Opus library is loaded explicitly (fixes silent voice failure on Termux/Android)
- requirements.txt pins minimum versions (discord.py ≥ 2.4 for Python 3.13 support)

### Main Commit 4

**Bug Fixes:**
- Fixed skip button firing twice (skipping two songs instead of one)
- Fixed control panel buttons dying after 180 seconds
- Fixed crash when playing local files without bot being in a voice channel
- Fixed pagination prev/next buttons failing (interaction not deferred)
- Fixed autoplay being global instead of per-server
- Fixed `/play` command blocking the bot during YouTube info extraction
- Fixed cooldown fallback defaulting to 100s instead of 10s
- Fixed hardcoded "once per minute" cooldown error message

**UI Enhancements:**
- Color-coded control panel buttons (green = playback, blue = info, red = destructive, grey = utility)
- Now Playing track shown in control embed footer
- Queue count displayed in embed description
- Autoplay button label shows current ON/OFF state
- Volume control buttons (🔉/🔊) on the control panel
- Now Playing display shows elapsed time (e.g. "2:34 elapsed")
- Queue display shows current track at the top
- Clear queue confirms how many songs were removed

### Main Commit 3

- New Command /autoplay - toggle - plays random local files if the queue is empty 

- attempt at fixing skip logic (fully fixed in Commit 4)

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
