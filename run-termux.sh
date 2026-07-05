#!/data/data/com.termux/files/usr/bin/bash
#
# Start discord-musicbot on Android via Termux and keep it running.
#
# Usage (inside Termux, from the repo folder):
#   bash run-termux.sh            # start the bot
#   bash run-termux.sh --update   # update yt-dlp first (fixes most "YouTube
#                                 # stopped working" problems), then start
#
# Setting AUTO_UPDATE_YTDLP=1 in the environment also triggers the update.
#
# Holds a Termux wake-lock so the bot keeps running while the phone's screen is
# off, restarts the bot automatically if it crashes (with increasing backoff so
# a broken install can't drain the battery), and mirrors all output to bot.log.
# Stop it with Ctrl+C.

cd "$(dirname "$0")"

LOG_FILE="bot.log"
# Keep one previous log so a crash before a restart stays diagnosable.
if [ -f "$LOG_FILE" ] && [ "$(wc -c < "$LOG_FILE")" -gt 1048576 ]; then
    mv -f "$LOG_FILE" "$LOG_FILE.1"
fi

if [ "$1" = "--update" ] || [ "${AUTO_UPDATE_YTDLP:-0}" = "1" ]; then
    echo ">> Updating yt-dlp..."
    pip install -U yt-dlp || echo ">> yt-dlp update failed (offline?). Starting anyway."
fi

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

echo ">> Starting discord-musicbot. Press Ctrl+C to stop. (log: $LOG_FILE)"
backoff=5
while true; do
    start_ts=$(date +%s)
    python discordmusicbot.py 2>&1 | tee -a "$LOG_FILE"
    code=${PIPESTATUS[0]}
    # Exit code 0 = clean shutdown. Exit code 2 = unrecoverable setup problem
    # (bad token / bad config) — restarting would just crash-loop.
    if [ "$code" -eq 0 ]; then
        echo ">> Bot exited cleanly. Not restarting."
        break
    fi
    if [ "$code" -eq 2 ]; then
        echo ">> Bot reported a configuration problem (see messages above). Fix it and rerun."
        break
    fi
    # Reset the backoff after a healthy run; otherwise keep doubling up to 60s
    # so a persistent crash doesn't hot-loop on the phone.
    uptime=$(( $(date +%s) - start_ts ))
    if [ "$uptime" -ge 300 ]; then
        backoff=5
    fi
    echo ">> Bot exited with code $code. Restarting in ${backoff}s... (Ctrl+C to stop)"
    sleep "$backoff"
    backoff=$(( backoff * 2 ))
    if [ "$backoff" -gt 60 ]; then
        backoff=60
    fi
done

cleanup
