#!/data/data/com.termux/files/usr/bin/bash
#
# One-time setup for running discord-musicbot on Android via Termux.
#
# Usage (inside Termux, from the repo folder):
#   bash setup-termux.sh
#
# Installs Python, FFmpeg, Opus and the Python dependencies (including PyNaCl
# for voice, built against Termux's system libsodium), then creates config.json
# from config.example.json if it does not already exist.

set -e

cd "$(dirname "$0")"

echo ">> Updating Termux packages..."
# --force-confnew answers apt's conffile prompts automatically so the script
# can never hang waiting for input on a phone.
pkg update -y
pkg upgrade -y -o Dpkg::Options::=--force-confnew

echo ">> Installing system packages (python, ffmpeg, opus, git, libsodium, clang)..."
# - opus: discord.py needs libopus for voice; the bot loads it from $PREFIX/lib.
# - libsodium + clang let PyNaCl build against the system library instead of
#   failing to compile its bundled copy on Android.
pkg install -y python ffmpeg opus git libsodium clang

echo ">> Installing Python dependencies from requirements.txt..."
# SODIUM_INSTALL=system tells PyNaCl to link against the libsodium installed
# above rather than compiling its vendored source (the reliable path on Termux).
export SODIUM_INSTALL=system
pip install -U pip
pip install -U -r requirements.txt

echo ">> Verifying the Python dependencies import cleanly..."
python - <<'EOF'
import sys
print(f"   Python {sys.version.split()[0]}")
import discord, nacl, yt_dlp, gtts
print(f"   discord.py {discord.__version__}, yt-dlp {yt_dlp.version.__version__}")
EOF

if [ ! -f config.json ]; then
    echo ">> Creating config.json from config.example.json..."
    cp config.example.json config.json
    echo ""
    echo "   config.json created. You MUST now edit it and set your BOT_TOKEN."
    echo "   Get a token at https://discord.com/developers/applications"
    echo "   Edit with:   nano config.json"
else
    echo ">> config.json already exists — leaving it untouched."
fi

echo ""
echo ">> Setup complete."
echo "   1. Make sure your BOT_TOKEN is set in config.json"
echo "   2. In the Discord developer portal, under Bot -> Privileged Gateway"
echo "      Intents, enable MESSAGE CONTENT INTENT (the bot exits at startup"
echo "      without it)."
echo "   3. Start the bot with:   bash run-termux.sh"
echo ""
echo "   Optional: auto-start on boot with the Termux:Boot app —"
echo "   mkdir -p ~/.termux/boot && cp termux-boot-start.sh ~/.termux/boot/"
