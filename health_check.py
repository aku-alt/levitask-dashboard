#!/usr/bin/env python3
"""
Levitask Dashboard - Daily Bot Health Check
Sends a DM to Aku from the Levitask bot every weekday at 9am BKK.
Triggered by .github/workflows/healthcheck.yml
"""
import os
from datetime import datetime, timezone, timedelta
from slack_sdk import WebClient

SLACK_BOT_TOKEN = os.environ['SLACK_BOT_TOKEN']
AKU_USER_ID = 'U08SCGWD2P4'
BKK = timezone(timedelta(hours=7))


def send_bot_dm(client, user_id, text):
    resp = client.conversations_open(users=[user_id])
    channel = resp['channel']['id']
    client.chat_postMessage(channel=channel, text=text)


def main():
    client = WebClient(token=SLACK_BOT_TOKEN)

    last_commit_str = os.environ.get('LAST_COMMIT_TIME', '').strip()
    now = datetime.now(timezone.utc)
    now_bkk = now.astimezone(BKK).strftime('%a %d %b, %H:%M')

    if last_commit_str:
        try:
            last_commit = datetime.fromisoformat(last_commit_str)
            age_h = (now - last_commit).total_seconds() / 3600
            last_bkk = last_commit.astimezone(BKK).strftime('%a %d %b, %H:%M')
            if age_h < 1:
                freshness = f":white_check_mark: Fresh - last update {last_bkk} BKK ({age_h*60:.0f} min ago)"
            elif age_h < 3:
                freshness = f":white_check_mark: Fresh - last update {last_bkk} BKK ({age_h:.1f}h ago)"
            else:
                freshness = f":warning: Stale - last update {last_bkk} BKK ({age_h:.1f}h ago) - workflow may be stuck"
        except Exception as e:
            freshness = f":question: Could not parse commit time: {e}"
    else:
        freshness = ":question: Commit time unavailable"

    text = (
        f":eyes: *Dashboard health check - {now_bkk} BKK*\n"
        f"- Data freshness: {freshness}\n"
        f"- Live site: https://aku-alt.github.io/levitask-dashboard/\n"
        f"- Workflow runs: https://github.com/aku-alt/levitask-dashboard/actions/workflows/slack.yml"
    )

    send_bot_dm(client, AKU_USER_ID, text)
    print(f"Health check sent to Aku at {now_bkk} BKK.")


if __name__ == '__main__':
    main()
