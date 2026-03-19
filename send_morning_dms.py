#!/usr/bin/env python3
"""
Levitask — Morning Focus DMs
Sends a daily DM to each team member asking what they're working on.
Run once daily at 10am BKK (scheduled via cron-job.org → GitHub Actions).
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from slack_sdk import WebClient

BKK_TZ = timezone(timedelta(hours=7))

TEAM = [
    {"name": "Mikhael",  "userId": "U08S47DCMDZ"},
    {"name": "Aku",      "userId": "U08SCGWD2P4"},
    {"name": "GB",       "userId": "U0AM6QK3W1E"},
    {"name": "Terapat",  "userId": "U08TPARPY2F"},
    {"name": "Nico",     "userId": "U0AHKPKGSD9"},
    {"name": "Veronika", "userId": "U0A5L102GBG"},
    {"name": "Pierre",   "userId": "U0A2PBKKS95"},
    {"name": "Bastien",  "userId": "U0A957P6U02"},
    {"name": "Nacho",    "userId": "U0A92TC4V9U"},
]

MESSAGE = (
    "Hey! 👋 What's your main focus today?\n"
    "Just reply to this message with one line — it'll show up on the team dashboard."
)


def send_morning_dms():
    token = os.environ.get("SLACK_TOKEN", "")
    if not token:
        print("✗ No SLACK_TOKEN found")
        sys.exit(1)

    client = WebClient(token=token)
    now_bkk = datetime.now(BKK_TZ)
    today_start = now_bkk.replace(hour=0, minute=0, second=0, microsecond=0)

    print(f"\n{'='*50}")
    print(f"Morning Focus DMs — {now_bkk.strftime('%Y-%m-%d %H:%M BKK')}")
    print(f"{'='*50}\n")

    sent = 0
    skipped = 0

    for person in TEAM:
        user_id = person["userId"]
        name    = person["name"]
        try:
            # Open (or retrieve) the DM channel with this user
            dm_resp    = client.conversations_open(users=user_id)
            channel_id = dm_resp["channel"]["id"]

            # Check if we already sent a message today
            history = client.conversations_history(
                channel=channel_id,
                oldest=str(today_start.timestamp()),
                limit=20,
            )
            already_sent = any(
                msg.get("bot_id") or msg.get("subtype") == "bot_message"
                for msg in history.get("messages", [])
            )

            if already_sent:
                print(f"  {name}: already sent today — skipping")
                skipped += 1
                continue

            client.chat_postMessage(channel=channel_id, text=MESSAGE)
            print(f"  {name}: ✓ sent")
            sent += 1

        except Exception as e:
            print(f"  {name}: ✗ error — {e}")

    print(f"\n✓ Done — {sent} sent, {skipped} skipped\n")


if __name__ == "__main__":
    send_morning_dms()
