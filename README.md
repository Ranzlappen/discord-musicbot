# discord-musicbot
lightweight discord music bot for youtube and local music

⚠️ Attention! Using this bot extremely heavily (multiple youtube calls per second) might not be a good idea, since YouTube does not like bots, making too many calls might get your youtube account suspended. 
Using this privately shouldn't be a problem at all though. 
Use this at your own risk.

<details>
<summary> I HAVE READ THE ABOVE AND KNOW THE RISK.</summary>

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
	"EMBED_TITLE": "Music Controls",
	"EMBED_DESCRIPTION": "Use the buttons below to control music.",
	"EMBED_ANIMATION_URL": "https://fonts.gstatic.com/s/e/notoemoji/latest/1f916/512.webp"
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
```
/join - connects the bot the Users current Voice Channel
/controls - shows some buttons. one shows current song, one shows the song queue
/local - shows the user a selection of files in your root/music folder, this folder will be created automatically if it doesnt exist next to your discordmusicbot.py, selecting a song will append it to the playback queue
/pause - pauses current track
/play <url> - appends the song in the url to the playback queue
/resume - resumes current track
/skip - skips corrent track
```
</details>
