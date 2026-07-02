#!/data/data/com.termux/files/usr/bin/bash
#
# One-time setup for running discord-musicbot on Android via Termux.
#
# Usage (inside Termux, from the repo folder):
#   bash setup-termux.sh
#
# Installs Python, FFmpeg and the Python dependencies (including PyNaCl for
# voice, built against Termux's system libsodium), then creates config.json
# from config.example.json if it does not already exist.

set -e

cd "$(dirname "$0")"

echo ">> Updating Termux packages..."
pkg update -y && pkg upgrade -y

echo ">> Installing system packages (python, ffmpeg, git, libsodium, clang)..."
# libsodium + clang let PyNaCl build against the system library instead of
# failing to compile its bundled copy on Android.
pkg install -y python ffmpeg git libsodium clang

echo ">> Installing Python dependencies from requirements.txt..."
# SODIUM_INSTALL=system tells PyNaCl to link against the libsodium installed
# above rather than compiling its vendored source (the reliable path on Termux).
export SODIUM_INSTALL=system
pip install -U pip
pip install -U -r requirements.txt

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
echo "   2. Start the bot with:   bash run-termux.sh"
