#!/data/data/com.termux/files/usr/bin/bash
#
# Auto-start discord-musicbot when the phone boots, via the Termux:Boot app.
#
# Install:
#   1. Install Termux:Boot from F-Droid and open it once.
#   2. mkdir -p ~/.termux/boot
#   3. cp termux-boot-start.sh ~/.termux/boot/
#   4. Reboot the phone to test. Output lands in the repo's bot.log.
#
# If the repo lives somewhere other than ~/discord-musicbot, set BOT_DIR in
# ~/.termux/boot/termux-boot-start.sh accordingly.

BOT_DIR="${BOT_DIR:-$HOME/discord-musicbot}"

cd "$BOT_DIR" || exit 1

# run-termux.sh acquires the wake-lock, handles restarts and writes bot.log.
exec bash run-termux.sh
