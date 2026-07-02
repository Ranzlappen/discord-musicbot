#!/data/data/com.termux/files/usr/bin/bash
#
# Start discord-musicbot on Android via Termux and keep it running.
#
# Usage (inside Termux, from the repo folder):
#   bash run-termux.sh
#
# Holds a Termux wake-lock so the bot keeps running while the phone's screen is
# off, and restarts the bot automatically if it crashes. Stop it with Ctrl+C.

cd "$(dirname "$0")"

# Prevent Android from suspending the CPU (which would freeze the bot / drop
# it from voice). termux-wake-lock is provided by Termux itself.
if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock
    echo ">> Wake-lock acquired (phone will not sleep the bot)."
fi

# Release the wake-lock when this script exits, however it exits.
cleanup() {
    echo ""
    echo ">> Shutting down, releasing wake-lock..."
    if command -v termux-wake-unlock >/dev/null 2>&1; then
        termux-wake-unlock
    fi
    exit 0
}
trap cleanup INT TERM

echo ">> Starting discord-musicbot. Press Ctrl+C to stop."
while true; do
    python discordmusicbot.py
    code=$?
    # Exit code 0 = clean shutdown; anything else = crash, so restart.
    if [ "$code" -eq 0 ]; then
        echo ">> Bot exited cleanly. Not restarting."
        break
    fi
    echo ">> Bot exited with code $code. Restarting in 5s... (Ctrl+C to stop)"
    sleep 5
done

cleanup
