#!/usr/bin/env python3
"""
Levitask Team Availability Dashboard ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ Cloud Refresh Script

Two modes:
  --mode calendar   Fetch Google Calendar -> writes calendar_cache.json
  --mode slack      Read cache + fetch Slack statuses -> writes index.html (default)
"""

import argparse
import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Config
BKK_TZ = timezone(timedelta(hours=7))

TEAM = [
    {"name": "Mikhael",  "initials": "M",  "userId": "U08S47DCMDZ", "email": "michael@levitask.com",  "timezone": "Asia/Bangkok"},
    {"name": "Aku",      "initials": "A",  "userId": "U08SCGWD2P4", "email": "aku@levitask.com",      "timezone": "Asia/Bangkok"},
    {"name": "GB",       "initials": "GB", "userId": "U0AM6QK3W1E", "email": "gabriel@levitask.com",  "timezone": "Asia/Bangkok"},
    {"name": "Terapat",  "initials": "T",  "userId": "U08TPARPY2F", "email": "terapat@levitask.com",  "timezone": "Asia/Bangkok"},
    {"name": "Nico",     "initials": "Nc", "userId": "U0AHKPKGSD9", "email": "nicolas@levitask.com",  "timezone": "Europe/Brussels"},
    {"name": "Veronika", "initials": "V",  "userId": "U0A5L102GBG", "email": "veronika@levitask.com", "timezone": "Asia/Bangkok"},
    {"name": "Pierre",   "initials": "P",  "userId": "U0A2PBKKS95", "email": "pierre@levitask.com",   "timezone": "Asia/Bangkok"},
    {"name": "Bastien",  "initials": "B",  "userId": "U0A957P6U02", "email": "bastien@levitask.com",  "timezone": "Asia/Bangkok"},
    {"name": "Nacho",    "initials": "Na", "userId": "U0A92TC4V9U", "email": "nacho@levitask.com",    "timezone": "Asia/Bangkok"},
]

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]

# Slack
EMOJI_MAP = {
    ":car:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":bus:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":airplane:": "ÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂ¸ÃÂÃÂ", ":train:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":bike:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ²",
    ":walking:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¶", ":house:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ ", ":house_with_garden:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¡", ":coffee:": "ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ",
    ":tea:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂµ", ":lunch:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ±", ":fork_and_knife:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ´", ":headphones:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ§",
    ":computer:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ»", ":desktop_computer:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¥ÃÂÃÂ¯ÃÂÃÂ¸ÃÂÃÂ", ":no_entry:": "ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ",
    ":no_entry_sign:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ«", ":red_circle:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ´", ":red_square:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¥",
    ":large_red_square:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¥", ":orange_square:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ§", ":yellow_square:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¨",
    ":green_square:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ©", ":blue_square:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¦", ":purple_square:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂª",
    ":brown_square:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ«", ":black_large_square:": "ÃÂÃÂ¢ÃÂÃÂ¬ÃÂÃÂ", ":orange_circle:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ ",
    ":yellow_circle:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¡", ":green_circle:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¢", ":blue_circle:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂµ",
    ":purple_circle:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ£", ":brown_circle:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¤", ":calendar:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ",
    ":spiral_calendar_pad:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂ¸ÃÂÃÂ", ":clock1:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":rocket:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ",
    ":dart:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¯", ":palm_tree:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ´", ":beach_with_umbrella:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂ¸ÃÂÃÂ",
    ":globe_with_meridians:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":earth_asia:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":earth_americas:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ",
    ":thermometer:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂ¯ÃÂÃÂ¸ÃÂÃÂ", ":mask:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ·", ":face_with_thermometer:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂ¤ÃÂÃÂ",
    ":zzz:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¤", ":sleeping:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ´", ":phone:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":telephone_receiver:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ",
    ":pencil:": "ÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂ¸ÃÂÃÂ", ":pencil2:": "ÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂ¸ÃÂÃÂ", ":book:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":books:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ",
    ":tada:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":sparkles:": "ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ¨", ":fire:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¥", ":star:": "ÃÂÃÂ¢ÃÂÃÂ­ÃÂÃÂ",
    ":white_check_mark:": "ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ", ":x:": "ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ", ":warning:": "ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ ÃÂÃÂ¯ÃÂÃÂ¸ÃÂÃÂ", ":mega:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ£",
    ":loudspeaker:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¢", ":speech_balloon:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¬", ":construction:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ§",
    ":hammer:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¨", ":wrench:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ§", ":seedling:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ±", ":sunny:": "ÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂ¸ÃÂÃÂ",
    ":umbrella:": "ÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂ¸ÃÂÃÂ", ":muscle:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂª", ":raising_hand:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":wave:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ",
    ":brain:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂ§ÃÂÃÂ ", ":bulb:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¡", ":technologist:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂ§ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ»", ":nerd_face:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂ¤ÃÂÃÂ",
    ":monocle_face:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂ§ÃÂÃÂ", ":thinking_face:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂ¤ÃÂÃÂ", ":male-technologist:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¨ÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ»",
    ":female-technologist:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ©ÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ»", ":eyes:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":writing_hand:": "ÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂ¸ÃÂÃÂ",
    ":memo:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":mag:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":chart_with_upwards_trend:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ",
    ":bar_chart:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":pushpin:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":paperclip:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ",
    ":inbox_tray:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¥", ":outbox_tray:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¤", ":email:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ§",
    ":bell:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":no_bell:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":mute:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":microphone:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¤",
    ":hourglass:": "ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ", ":hourglass_flowing_sand:": "ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ³", ":stopwatch:": "ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ±ÃÂÃÂ¯ÃÂÃÂ¸ÃÂÃÂ",
    ":flag-th:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¹ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ­", ":flag-fr:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ«ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ·", ":flag-be:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ§ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂª",
    ":flag-es:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂªÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¸", ":flag-us:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂºÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¸", ":flag-gb:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ¬ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ§",
    ":raised_hands:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":clap:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":pray:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":ok_hand:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ",
    ":thumbsup:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":thumbsdown:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":slightly_smiling_face:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ",
    ":blush:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":sweat_smile:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ", ":cityscape:": "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂ¸ÃÂÃÂ",
}


def slack_emoji_to_unicode(code: str) -> str:
    return EMOJI_MAP.get(code, "")


def get_slack_status(user_id: str, client) -> dict:
    try:
        resp    = client.users_info(user=user_id)
        profile = resp["user"]["profile"]
        status_text  = profile.get("status_text",  "").strip()
        status_emoji = profile.get("status_emoji", "").strip()
        photo        = (profile.get("image_72") or profile.get("image_48") or "").strip()
        emoji_unicode = slack_emoji_to_unicode(status_emoji) if status_emoji else ""
        try:
            emoji_unicode = emoji_unicode.encode('latin-1').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
        display = status_text.strip()
        return {"text": status_text, "emoji": status_emoji, "display": display, "photo": photo}
    except Exception as e:
        print(f"  Slack error for {user_id}: {e}")
        return {"text": "", "emoji": "", "display": "", "photo": ""}


def get_weekly_focus_from_dm(user_id: str, client) -> dict:
    """
    Returns {day_abbr: latest_message} for Mon-today of the current week.
    Resets naturally every Monday - no messages from a new week until people reply.
    """
    try:
        dm_resp    = client.conversations_open(users=user_id)
        channel_id = dm_resp["channel"]["id"]
        now_bkk    = datetime.now(BKK_TZ)

        # Monday 00:00 BKK of the current week
        monday = (now_bkk - timedelta(days=now_bkk.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        history = client.conversations_history(
            channel=channel_id,
            oldest=str(monday.timestamp()),
            latest=str(now_bkk.timestamp()),
            limit=50,
        )

        result = {}
        for msg in history.get("messages", []):
            if msg.get("user") == user_id and not msg.get("bot_id"):
                text = msg.get("text", "").strip()
                if text:
                    ts      = float(msg.get("ts", 0))
                    msg_dt  = datetime.fromtimestamp(ts, tz=BKK_TZ)
                    weekday = msg_dt.weekday()
                    if weekday < 5:  # Mon-Fri only
                        day_abbr = DAYS[weekday]
                        if day_abbr not in result:  # keep earliest per day
                            result[day_abbr] = text
        return result
    except Exception as e:
        print(f"  Weekly focus DM error for {user_id}: {e}")
        return {}


BUSY_KEYWORDS = {
    "meeting", "busy", "call", "unavailable", "lunch", "brb", "ooo", "out of office",
    "vacation", "sick", "dnd", "do not disturb", "deep work", "focus", "focusing",
    "heads down", "in the zone", "no interruptions", "deep focus", "flow", "working",
    "on a call", "presenting", "recording", "in a meeting",
}
AWAY_KEYWORDS = {"commuting", "away", "transit", "offline", "be right back", "holiday", "on holiday", "on leave"}


def classify_slack(slack: dict) -> str:
    text  = slack["text"].lower()
    emoji = slack["emoji"]
    if not slack["text"]:
        return "available"
    if any(k in text for k in AWAY_KEYWORDS) or emoji in (":car:", ":bus:", ":train:", ":airplane:", ":palm_tree:", ":beach_with_umbrella:"):
        return "away"
    if any(k in text for k in BUSY_KEYWORDS) or emoji in (":no_entry:", ":x:", ":red_circle:", ":red_square:", ":large_red_square:"):
        return "busy"
    return "available"


# Google Calendar
def _parse_dt(dt_dict: dict):
    if "dateTime" in dt_dict:
        try:
            return datetime.fromisoformat(dt_dict["dateTime"])
        except Exception:
            return None
    elif "date" in dt_dict:
        try:
            d = datetime.strptime(dt_dict["date"], "%Y-%m-%d")
            return d.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def get_calendar_info(email: str, creds_file: str) -> dict:
    """
    Fetches today's events + this week's full Mon-Fri events in a single API call.
    Returns busy status, todayEvents list, weekEvents dict.
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_file(
            creds_file,
            scopes=["https://www.googleapis.com/auth/calendar.readonly"],
        ).with_subject(email)
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)

        now     = datetime.now(timezone.utc)
        now_bkk = now.astimezone(BKK_TZ)

        today_start = now_bkk.replace(hour=0,  minute=0,  second=0,  microsecond=0)
        today_end   = now_bkk.replace(hour=23, minute=59, second=59, microsecond=0)

        # Monday to Friday of the current week
        week_mon = (now_bkk - timedelta(days=now_bkk.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        week_fri = (week_mon + timedelta(days=4)).replace(
            hour=23, minute=59, second=59, microsecond=0
        )

        result = service.events().list(
            calendarId="primary",
            timeMin=week_mon.isoformat(),
            timeMax=week_fri.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=50,
        ).execute()

        today_events   = []
        week_events    = {d: [] for d in DAYS}
        current_status = {"busy": False}

        for event in result.get("items", []):
            # Skip declined
            attendees = event.get("attendees", [])
            if any(a.get("email") == email and a.get("responseStatus") == "declined"
                   for a in attendees):
                continue

            start_raw = event.get("start", {})
            end_raw   = event.get("end",   {})
            if "dateTime" not in start_raw:
                continue  # skip all-day

            start_dt = _parse_dt(start_raw)
            end_dt   = _parse_dt(end_raw)
            if not start_dt or not end_dt:
                continue

            start_bkk = start_dt.astimezone(BKK_TZ)
            end_bkk   = end_dt.astimezone(BKK_TZ)
            title     = event.get("summary", "Meeting")
            start_str = start_bkk.strftime("%H:%M")
            end_str   = end_bkk.strftime("%H:%M")
            is_active = start_dt <= now <= end_dt
            is_past   = end_dt < now

            # Week bucket
            if 0 <= start_bkk.weekday() <= 4:
                week_events[DAYS[start_bkk.weekday()]].append({
                    "title": title, "start": start_str, "end": end_str,
                })

            # Today's events
            if today_start <= start_bkk <= today_end or (start_bkk <= today_start and end_bkk >= today_start):
                today_events.append({
                    "title": title, "start": start_str, "end": end_str,
                    "active": is_active, "past": is_past,
                })
                if is_active and not current_status.get("busy"):
                    current_status = {"busy": True, "event": title, "until": end_str}
                elif not current_status.get("busy") and not current_status.get("upcoming"):
                    if now < start_dt <= now + timedelta(minutes=5):
                        current_status = {"busy": False, "upcoming": title, "at": start_str}

        return {**current_status, "todayEvents": today_events, "weekEvents": week_events}

    except Exception as e:
        import traceback
        err = traceback.format_exc()
        print(f"  Calendar error for {email}: {e}")
        print(f"  Traceback: {err}")
        return {"busy": False, "todayEvents": [], "weekEvents": {d: [] for d in DAYS}, "_error": str(e)}


# HTML template
HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="refresh" content="60">
  <title>Levitask - Team Availability</title>
  <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@500;600;700&display=swap" rel="stylesheet">
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:"Avenir Next","Avenir",-apple-system,BlinkMacSystemFont,sans-serif;background:#0b0b0b;color:#e8e6e1;min-height:100vh;padding:36px 28px}
    header{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:40px;padding-bottom:24px;border-bottom:1px solid #1c1c1c}
    .brand{display:flex;align-items:center;gap:16px}
    .logo{width:38px;height:38px;background:#fff;border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:17px;color:#0b0b0b}
    h1{font-size:20px;font-weight:600;color:#fff;letter-spacing:.08em;text-transform:uppercase}
    h1 span{font-weight:300}
    .subtitle{font-size:11px;color:#5c5a57;margin-top:3px;letter-spacing:.12em;text-transform:uppercase}
    .meta{text-align:right;font-size:11px;color:#5c5a57;line-height:1.8;letter-spacing:.04em}
    .meta .clock{font-size:15px;font-weight:500;color:#a8a49e;letter-spacing:.06em}
    .summary{display:flex;gap:12px;margin-bottom:32px}
    .summary-pill{display:flex;align-items:center;gap:9px;background:#111;border:1px solid #1c1c1c;border-radius:4px;padding:8px 20px;font-size:12px;font-weight:500;letter-spacing:.06em}
    .dot{width:7px;height:7px;border-radius:50%}
    .dot-available{background:#34d399;box-shadow:0 0 7px #34d39955}
    .dot-busy{background:#ef4444;box-shadow:0 0 7px #ef444455}
    .summary-count{font-size:17px;font-weight:700}
    .count-available{color:#34d399}
    .count-busy{color:#ef4444}
    .section-label{font-size:11px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;margin-bottom:14px;margin-top:32px}
    .section-label.available{color:#34d399}
    .section-label.busy{color:#ef4444}
    .section-label.achievements{color:#a78bfa}
    .grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
    @media(max-width:1200px){.grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
    @media(max-width:800px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
    @media(max-width:500px){.grid{grid-template-columns:1fr}}
    .card{background:#111;border:1px solid #1c1c1c;border-radius:6px;padding:16px 18px;display:flex;flex-direction:column;position:relative}
    .card.available{border-left:2px solid #34d399}
    .card.busy{border-left:2px solid #ef4444}
    .card.away{border-left:2px solid #c9a050}
    .card.offhours{opacity:0.45;filter:grayscale(0.25);transition:opacity .3s}
    .week-btn{position:absolute;top:12px;right:12px;font-size:9px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:#3a3835;background:transparent;border:1px solid #2a2a2a;border-radius:3px;padding:3px 8px;cursor:pointer;transition:color .15s,border-color .15s,background .15s}
    .week-btn:hover{color:#a8a49e;border-color:#4a4a4a;background:#1a1a1a}
    .card-header{display:flex;align-items:center;gap:12px;padding-right:52px}
    .avatar{width:48px;height:48px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:700;flex-shrink:0;position:relative}
    .avatar img{width:100%;height:100%;object-fit:cover;border-radius:50%;display:block}
    .avatar-available{background:#0d2018;color:#34d399}
    .avatar-busy{background:#1a0808;color:#ef4444}
    .avatar-away{background:#191508;color:#c9a050}
    .avatar::after{content:"";position:absolute;bottom:1px;right:1px;width:11px;height:11px;border-radius:50%;border:2px solid #111;z-index:1}
    .available .avatar::after{background:#34d399}
    .busy .avatar::after{background:#ef4444}
    .away .avatar::after{background:#c9a050}
    .info{flex:1;min-width:0}
    .name{font-size:15px;font-weight:600;color:#e8e6e1;letter-spacing:.03em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .status-text{display:inline-block;font-size:10px;font-weight:800;margin-top:5px;padding:3px 8px;border-radius:4px;letter-spacing:.07em;text-transform:uppercase;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .status-available{background:#34d399;color:#052010}
    .status-busy{background:#ef4444;color:#fff}
    .status-away{background:#c9a050;color:#0b0b0b}
    .slack-status{display:block;margin-top:4px;font-size:11px;color:#6a6866;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .time-indicator{display:flex;align-items:center;gap:8px;margin-top:10px;padding:6px 10px;background:#0e0e0e;border:1px solid #1c1c1c;border-radius:4px}
    .local-time{font-size:11px;color:#4a4846}
    .time-badge{font-size:10px;font-weight:800;padding:2px 7px;border-radius:3px;letter-spacing:.06em;text-transform:uppercase;margin-left:auto}
    .badge-free{color:#34d399;background:#0d2018}
    .badge-soon{color:#f59e0b;background:#1a1508}
    .badge-busy{color:#ef4444;background:#1a0808}
    .badge-offhours{color:#4a4846;background:#161616}
    .events-divider{height:1px;background:#1c1c1c;margin:12px 0 8px}
    .events-list{display:flex;flex-direction:column;gap:4px}
    .event-item{display:flex;align-items:center;gap:7px;padding:1px 0}
    .event-dot{width:5px;height:5px;border-radius:50%;flex-shrink:0}
    .event-time{flex-shrink:0;font-variant-numeric:tabular-nums;font-size:10.5px;min-width:84px}
    .event-title{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;font-size:11px}
    .event-item.upcoming .event-dot{background:#3a3835}
    .event-item.upcoming .event-time{color:#6a6866}
    .event-item.upcoming .event-title{color:#c8c4be;font-weight:500}
    .event-item.active .event-dot{background:#34d399;box-shadow:0 0 5px #34d39966}
    .event-item.active .event-time{color:#34d399;font-weight:600}
    .event-item.active .event-title{color:#fff;font-weight:700}
    .event-item.past .event-dot{background:#2a2a28}
    .event-item.past .event-time{color:#3a3836}
    .event-item.past .event-title{color:#3a3836}
    .no-events{font-size:10px;color:#3a3835;font-weight:600;margin-top:10px;letter-spacing:.08em;text-transform:uppercase}
    .focus-block{margin-top:10px;padding-top:8px;border-top:1px solid #1c1c1c}
    .focus-label{font-size:9px;font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:#3a3835;margin-bottom:3px}
    .focus-text{font-size:11.5px;color:#8a8680;line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
    .achievements-tile{background:#111;border:1px solid #1c1c1c;border-left:2px solid #a78bfa;border-radius:6px;overflow:hidden}
    .achievements-header{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid #1c1c1c}
    .achievements-title{font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#a78bfa}
    .achievements-week{font-size:10px;color:#4a4846;letter-spacing:.06em}
    .achievement-row{display:grid;grid-template-columns:160px 1fr;align-items:start;padding:11px 18px;border-bottom:1px solid #141414;gap:16px}
    .achievement-row:last-child{border-bottom:none}
    .achievement-person{display:flex;align-items:center;gap:9px}
    .ach-avatar{width:28px;height:28px;border-radius:50%;overflow:hidden;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;flex-shrink:0;background:#1a1a1a;color:#6a6866}
    .ach-avatar img{width:100%;height:100%;object-fit:cover}
    .achievement-name{font-size:12px;font-weight:600;color:#a8a49e}
    .achievement-msgs{display:flex;flex-direction:column;gap:4px}
    .achievement-msg{font-size:12px;line-height:1.4;display:flex;align-items:baseline;gap:8px}
    .ach-day{font-size:9px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#3a3835;flex-shrink:0;min-width:28px}
    .ach-text{color:#8a8680}
    .no-achievement{font-size:11px;color:#3a3835;font-style:italic}
    .modal-backdrop{display:none;position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:100;align-items:center;justify-content:center}
    .modal-backdrop.open{display:flex}
    .modal{background:#111;border:1px solid #2a2a2a;border-radius:8px;width:560px;max-width:92vw;max-height:85vh;overflow-y:auto}
    .modal-header{display:flex;align-items:center;justify-content:space-between;padding:18px 22px;border-bottom:1px solid #1c1c1c;position:sticky;top:0;background:#111;z-index:1}
    .modal-person{display:flex;align-items:center;gap:12px}
    .modal-avatar{width:36px;height:36px;border-radius:50%;overflow:hidden;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;background:#1a1a1a;color:#6a6866}
    .modal-avatar img{width:100%;height:100%;object-fit:cover}
    .modal-name{font-size:15px;font-weight:600;color:#e8e6e1}
    .modal-subtitle{font-size:10px;color:#4a4846;margin-top:2px;letter-spacing:.06em;text-transform:uppercase}
    .modal-close{background:none;border:none;color:#4a4846;font-size:22px;cursor:pointer;line-height:1;padding:4px}
    .modal-close:hover{color:#e8e6e1}
    .modal-body{padding:6px 0 16px}
    .week-day{padding:12px 22px}
    .week-day+.week-day{border-top:1px solid #161616}
    .week-day-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}
    .week-day-name{font-size:10px;font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:#4a4846}
    .week-day-name.today{color:#a78bfa}
    .week-day-date{font-size:10px;color:#3a3835}
    .week-events{display:flex;flex-direction:column;gap:4px}
    .week-event{display:flex;align-items:center;gap:8px}
    .week-event-dot{width:5px;height:5px;border-radius:50%;background:#2a2a28;flex-shrink:0}
    .week-event-time{font-size:10.5px;color:#6a6866;min-width:90px;font-variant-numeric:tabular-nums}
    .week-event-title{font-size:11.5px;color:#c8c4be;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .week-no-events{font-size:10.5px;color:#2a2a28;font-style:italic}
    footer{margin-top:48px;text-align:center;font-size:10px;color:#2a2a28;border-top:1px solid #1c1c1c;padding-top:18px;letter-spacing:.1em;text-transform:uppercase}
        .staff-req-btn{display:inline-flex;align-items:center;gap:7px;background:linear-gradient(135deg,#6366f1,#4f46e5);color:#fff;font-family:inherit;font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;text-decoration:none;padding:8px 16px;border-radius:6px;border:1px solid #4338ca;box-shadow:0 0 14px rgba(99,102,241,.3);transition:all .2s;white-space:nowrap}
            .staff-req-btn:hover{background:linear-gradient(135deg,#818cf8,#6366f1);box-shadow:0 0 22px rgba(99,102,241,.55);transform:translateY(-1px)}

    /* ── OVERLORD LOCK SCREEN ── */
    :root{--g:#00ff88;--gd:rgba(0,255,136,.18);--gx:rgba(0,255,136,.06);--r:#ff3355;--a:#ffaa00;--lbg:#03070d;--lpan:#060e16}
    #lock-screen{display:none;position:fixed;inset:0;z-index:9999;background:var(--lbg);font-family:'Share Tech Mono',monospace;align-items:center;justify-content:center;overflow:hidden;color:var(--g)}
    #lock-screen::after{content:'';position:fixed;inset:0;background:repeating-linear-gradient(to bottom,transparent 0px,transparent 3px,rgba(0,0,0,.07) 3px,rgba(0,0,0,.07) 4px);pointer-events:none;z-index:200}
    #lock-screen::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 55% 45% at 50% 50%,rgba(0,255,100,.045) 0%,transparent 70%);pointer-events:none;z-index:0}
    .lk-corner{position:fixed;width:44px;height:44px;opacity:.25;z-index:50}
    .lk-corner-tl{top:18px;left:18px;border-top:1px solid var(--g);border-left:1px solid var(--g)}.lk-corner-tr{top:18px;right:18px;border-top:1px solid var(--g);border-right:1px solid var(--g)}.lk-corner-bl{bottom:18px;left:18px;border-bottom:1px solid var(--g);border-left:1px solid var(--g)}.lk-corner-br{bottom:18px;right:18px;border-bottom:1px solid var(--g);border-right:1px solid var(--g)}
    .lk-bar{position:fixed;top:0;left:0;right:0;padding:7px 24px;border-bottom:1px solid rgba(0,255,136,.08);background:rgba(6,14,22,.85);display:flex;justify-content:space-between;font-size:9px;letter-spacing:.14em;color:rgba(0,255,136,.35);z-index:50}
    .lk-pdot{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--g);margin-right:6px;vertical-align:middle;animation:lk-blink 2s ease-in-out infinite}
    .lk-side{position:fixed;top:50%;transform:translateY(-50%);display:flex;flex-direction:column;gap:18px;font-size:9px;opacity:.22;letter-spacing:.12em;z-index:50}.lk-side.left{left:22px}.lk-side.right{right:22px;text-align:right}.lk-side-item span{display:block}.lk-lbl{color:rgba(0,255,136,.5);font-size:8px}
    .lk-panel{position:relative;z-index:10;width:500px;background:var(--lpan);border:1px solid rgba(0,255,136,.12);box-shadow:0 0 60px rgba(0,255,100,.06),0 0 0 1px rgba(0,0,0,.8),inset 0 0 40px rgba(0,0,0,.4)}
    .lk-ptop{padding:13px 22px;border-bottom:1px solid rgba(0,255,136,.08);display:flex;justify-content:space-between;align-items:center;background:rgba(0,255,136,.02)}.lk-ptop-title{font-family:'Rajdhani',sans-serif;font-size:11px;font-weight:600;letter-spacing:.28em;text-transform:uppercase;opacity:.55}.lk-ptop-id{font-size:9px;color:rgba(0,255,136,.3);letter-spacing:.1em}
    .lk-pbody{padding:28px 32px 24px;display:flex;flex-direction:column;gap:20px}
    .lk-eye-wrap{display:flex;align-items:center;justify-content:center;position:relative;height:100px}
    .lk-ring{position:absolute;border-radius:50%;border:1px solid rgba(0,255,136,.18)}.lk-ring-1{width:96px;height:96px;animation:lk-spin 18s linear infinite}.lk-ring-2{width:76px;height:76px;animation:lk-spin 12s linear infinite reverse;border-style:dashed;border-color:rgba(0,255,136,.1)}
    .lk-ring-1::before,.lk-ring-1::after{content:'';position:absolute;background:var(--g);width:4px;height:1px;top:50%;border-radius:1px}.lk-ring-1::before{left:-1px;transform:translateY(-50%)}.lk-ring-1::after{right:-1px;transform:translateY(-50%)}
    .lk-eye{position:relative;z-index:2;width:44px;height:44px;border-radius:50%;border:1px solid var(--g);background:radial-gradient(circle at 50% 50%,rgba(0,255,136,.08) 0%,transparent 70%);display:flex;align-items:center;justify-content:center;overflow:hidden;box-shadow:0 0 12px rgba(0,255,136,.25),0 0 30px rgba(0,255,136,.08)}
    .lk-iris{position:absolute;border-radius:50%;border:1px solid rgba(0,255,136,.25)}.lk-iris-1{width:34px;height:34px}.lk-iris-2{width:22px;height:22px;border-color:rgba(0,255,136,.15)}
    .lk-pupil{position:relative;z-index:3;width:9px;height:9px;border-radius:50%;background:var(--g);box-shadow:0 0 6px var(--g),0 0 14px rgba(0,255,136,.5);animation:lk-pupil 3.5s ease-in-out infinite}
    .lk-scan-beam{position:absolute;left:0;right:0;height:2px;background:linear-gradient(to right,transparent 0%,rgba(0,255,136,.4) 20%,rgba(0,255,136,.9) 50%,rgba(0,255,136,.4) 80%,transparent 100%);box-shadow:0 0 6px var(--g);top:0;animation:lk-scan 1.3s ease-in-out 2 forwards;display:none}
    .lk-eye-progress{position:absolute;z-index:3;width:52px;height:52px}.lk-eye-progress circle{fill:none;stroke:var(--g);stroke-width:1.5;stroke-linecap:round;stroke-dasharray:163.4;stroke-dashoffset:163.4;transform-origin:50% 50%;transform:rotate(-90deg);transition:stroke-dashoffset .05s linear}
    .lk-ch{position:absolute;opacity:.18}.lk-ch-h{width:110px;height:1px;background:linear-gradient(to right,transparent,var(--g),transparent)}.lk-ch-v{width:1px;height:110px;background:linear-gradient(to bottom,transparent,var(--g),transparent)}
    .lk-etick{position:absolute;width:8px;height:8px;opacity:.4}.lk-etick-tl{top:-14px;left:-14px;border-top:1px solid var(--g);border-left:1px solid var(--g)}.lk-etick-tr{top:-14px;right:-14px;border-top:1px solid var(--g);border-right:1px solid var(--g)}.lk-etick-bl{bottom:-14px;left:-14px;border-bottom:1px solid var(--g);border-left:1px solid var(--g)}.lk-etick-br{bottom:-14px;right:-14px;border-bottom:1px solid var(--g);border-right:1px solid var(--g)}
    .lk-log{display:flex;flex-direction:column;gap:4px;font-size:10px;letter-spacing:.08em;min-height:64px}.lk-log-line{display:flex;gap:10px;align-items:baseline;opacity:0;transform:translateY(4px);transition:opacity .3s,transform .3s}.lk-log-line.show{opacity:1;transform:translateY(0)}.lk-log-time{color:rgba(0,255,136,.35);font-size:9px;min-width:60px}.lk-log-text{color:var(--g)}.lk-log-text.warn{color:var(--a)}.lk-log-text.fail{color:var(--r)}
    .lk-form{display:flex;flex-direction:column;gap:10px;opacity:0;transition:opacity .5s;pointer-events:none}.lk-form.show{opacity:1;pointer-events:all}
    .lk-flbl{font-size:9px;letter-spacing:.18em;color:rgba(0,255,136,.45);text-transform:uppercase;display:flex;align-items:center;gap:6px}.lk-flbl::before{content:'▸';color:var(--g)}
    .lk-irow{position:relative;display:flex;align-items:center}.lk-ipfx{position:absolute;left:11px;font-size:11px;color:rgba(0,255,136,.45);pointer-events:none}
    #lk-pw{width:100%;padding:10px 12px 10px 34px;background:rgba(0,255,136,.025);border:1px solid rgba(0,255,136,.15);border-left:3px solid rgba(0,255,136,.4);color:var(--g);font-family:'Share Tech Mono',monospace;font-size:13px;letter-spacing:.12em;outline:none;caret-color:var(--g);transition:all .15s}#lk-pw:focus{background:rgba(0,255,136,.04);border-color:rgba(0,255,136,.4);border-left-color:var(--g);box-shadow:0 0 0 1px rgba(0,255,136,.08)}#lk-pw::placeholder{color:rgba(0,255,136,.18)}
    .lk-btn{width:100%;padding:10px;background:transparent;border:1px solid rgba(0,255,136,.3);color:var(--g);font-family:'Share Tech Mono',monospace;font-size:11px;letter-spacing:.22em;text-transform:uppercase;cursor:pointer;position:relative;overflow:hidden;transition:border-color .15s}.lk-btn::before{content:'';position:absolute;inset:0;background:var(--g);transform:scaleX(0);transform-origin:left;transition:transform .22s ease}.lk-btn:hover{border-color:var(--g)}.lk-btn:hover::before{transform:scaleX(1)}.lk-btn:hover .lk-btxt{color:var(--lbg)}.lk-btxt{position:relative;z-index:1;transition:color .22s}
    .lk-err{font-size:9px;letter-spacing:.12em;color:var(--r);min-height:12px;display:flex;align-items:center;gap:6px;opacity:0;transition:opacity .3s}.lk-err.show{opacity:1}.lk-err::before{content:'⚠'}
    .lk-hl{text-align:center}.lk-hl-main{font-family:'Rajdhani',sans-serif;font-size:20px;font-weight:700;letter-spacing:.22em;text-transform:uppercase;text-shadow:0 0 18px rgba(0,255,136,.4);opacity:0;transform:translateY(6px);transition:opacity .5s,transform .5s}.lk-hl-main.show{opacity:1;transform:translateY(0)}.lk-hl-sub{font-size:9px;letter-spacing:.18em;color:rgba(0,255,136,.35);margin-top:3px;opacity:0;transition:opacity .5s .2s}.lk-hl-sub.show{opacity:1}
    .lk-pbot{padding:9px 22px;border-top:1px solid rgba(0,255,136,.07);display:flex;justify-content:space-between;font-size:8px;color:rgba(0,255,136,.18);letter-spacing:.1em}
    .lk-ticker{position:fixed;bottom:0;left:0;right:0;padding:5px 0;border-top:1px solid rgba(0,255,136,.07);background:rgba(6,14,22,.9);overflow:hidden;font-size:9px;color:rgba(0,255,136,.28);letter-spacing:.1em;z-index:50;font-family:'Share Tech Mono',monospace}.lk-ticker-inner{display:inline-block;white-space:nowrap;animation:lk-ticker 36s linear infinite}
    #lk-flash{position:fixed;inset:0;background:rgba(0,255,136,.12);pointer-events:none;z-index:150;opacity:0;transition:opacity .08s}
    @keyframes lk-blink{0%,100%{opacity:1}50%{opacity:.25}}@keyframes lk-spin{to{transform:rotate(360deg)}}@keyframes lk-pupil{0%,100%{transform:scale(1);box-shadow:0 0 6px var(--g),0 0 14px rgba(0,255,136,.5)}50%{transform:scale(.65);box-shadow:0 0 3px var(--g)}}@keyframes lk-scan{0%{top:0%;opacity:0}5%{opacity:1}50%{top:100%;opacity:1}95%{opacity:1}100%{top:100%;opacity:0}}@keyframes lk-ticker{from{transform:translateX(100vw)}to{transform:translateX(-100%)}}
    /* ── END OVERLORD LOCK SCREEN ── */
  </style>
</head>
<body>

  <div id="lock-screen" style="display:none;flex-direction:column;">
    <div id="lk-flash"></div>
    <div class="lk-corner lk-corner-tl"></div><div class="lk-corner lk-corner-tr"></div><div class="lk-corner lk-corner-bl"></div><div class="lk-corner lk-corner-br"></div>
    <div class="lk-bar"><span><span class="lk-pdot"></span>SYSTEM NOMINAL</span><span id="lk-clock">--:--:--</span><span>NODE · LVT-HQ-01</span></div>
    <div class="lk-side left"><div class="lk-side-item"><span class="lk-lbl">UPTIME</span><span id="lk-uptime">00:00:00</span></div><div class="lk-side-item"><span class="lk-lbl">MEMBERS ONLINE</span><span>—</span></div><div class="lk-side-item"><span class="lk-lbl">ACCESS LEVEL</span><span>RESTRICTED</span></div><div class="lk-side-item"><span class="lk-lbl">PROTOCOL</span><span>SHA-256</span></div></div>
    <div class="lk-side right"><div class="lk-side-item"><span class="lk-lbl">CLEARANCE</span><span>ALPHA</span></div><div class="lk-side-item"><span class="lk-lbl">LOCATION</span><span>BKK / GLOBAL</span></div><div class="lk-side-item"><span class="lk-lbl">CHANNEL</span><span>ENCRYPTED</span></div><div class="lk-side-item"><span class="lk-lbl">STATUS</span><span>STANDING BY</span></div></div>
    <div class="lk-panel">
      <div class="lk-ptop"><span class="lk-ptop-title">Levitask · Command</span><span class="lk-ptop-id">AUTH · v2.4</span></div>
      <div class="lk-pbody">
        <div class="lk-eye-wrap">
          <div class="lk-ring lk-ring-1"></div><div class="lk-ring lk-ring-2"></div>
          <div class="lk-ch lk-ch-h"></div><div class="lk-ch lk-ch-v"></div>
          <div class="lk-etick lk-etick-tl"></div><div class="lk-etick lk-etick-tr"></div><div class="lk-etick lk-etick-bl"></div><div class="lk-etick lk-etick-br"></div>
          <svg class="lk-eye-progress" viewBox="0 0 52 52"><circle cx="26" cy="26" r="26" id="lk-arc"/></svg>
          <div class="lk-eye"><div class="lk-iris lk-iris-1"></div><div class="lk-iris lk-iris-2"></div><div class="lk-scan-beam" id="lk-beam"></div><div class="lk-pupil" id="lk-pupil"></div></div>
        </div>
        <div class="lk-hl"><div class="lk-hl-main" id="lk-hl-main">Identify Yourself</div><div class="lk-hl-sub" id="lk-hl-sub">Authorised personnel only · All access is logged</div></div>
        <div class="lk-log" id="lk-log"></div>
        <div class="lk-form" id="lk-form">
          <div class="lk-flbl">Passphrase</div>
          <div class="lk-irow"><span class="lk-ipfx">$_</span><input type="password" id="lk-pw" placeholder="enter passphrase" onkeydown="if(event.key==='Enter')lkAuth()" autocomplete="off"/></div>
          <button class="lk-btn" onclick="lkAuth()"><span class="lk-btxt">▶ &nbsp;Authenticate</span></button>
          <div class="lk-err" id="lk-err"></div>
        </div>
      </div>
      <div class="lk-pbot"><span>LEVITASK OPERATIONS CENTER</span><span>UNAUTHORIZED ACCESS WILL BE PROSECUTED</span></div>
    </div>
    <div class="lk-ticker"><span class="lk-ticker-inner">SYSTEM SECURE &nbsp;··· &nbsp;ALL CHANNELS MONITORED &nbsp;··· &nbsp;LEVITASK GLOBAL NETWORK &nbsp;··· &nbsp;TEAM STATUS: NOMINAL &nbsp;··· &nbsp;CLEARANCE REQUIRED FOR ENTRY &nbsp;··· &nbsp;OVERSIGHT PROTOCOLS ACTIVE &nbsp;··· &nbsp;THIS SESSION IS BEING RECORDED &nbsp;··· &nbsp;STAND BY FOR AUTHENTICATION &nbsp;···</span></div>
  </div>
  <div id="app-content" style="display:none;">

    <header>
    <div class="brand">
      <div class="logo">L</div>
      <div><h1>LEVITASK <span>TEAM</span></h1><div class="subtitle">Availability Dashboard</div></div>
    </div>
        <a href="https://gemini.google.com/share/bde5ab570916" target="_blank" class="staff-req-btn">📋 Staff Requests</a>
    <div class="meta">
      <div class="clock" id="clock">-</div>
      <div>Last updated: <span id="last-updated">-</span></div>
    </div>
  </header>
  <div class="summary">
    <div class="summary-pill"><div class="dot dot-available"></div><span class="summary-count count-available" id="count-available">-</span><span>Available</span></div>
    <div class="summary-pill"><div class="dot dot-busy"></div><span class="summary-count count-busy" id="count-busy">-</span><span>Busy / DND</span></div>
  </div>
  <div class="section-label available">Available</div>
  <div class="grid" id="grid-available"></div>
  <div class="section-label busy">Busy / Do Not Disturb</div>
  <div class="grid" id="grid-busy"></div>
  <div class="section-label achievements">This Week's Focus</div>
  <div class="achievements-tile" id="achievements-tile"></div>
  <footer>Levitask HQ &nbsp;ÃÂÃÂÃÂÃÂ·&nbsp; Slack + Google Calendar</footer>
  </div><!-- /app-content -->

  <div class="modal-backdrop" id="modal-backdrop" onclick="closeModal(event)">
    <div class="modal">
      <div class="modal-header">
        <div class="modal-person">
          <div class="modal-avatar" id="modal-avatar">-</div>
          <div><div class="modal-name" id="modal-name">-</div><div class="modal-subtitle">This week's calendar</div></div>
        </div>
        <button class="modal-close" onclick="document.getElementById('modal-backdrop').classList.remove('open')">ÃÂÃÂÃÂÃÂ</button>
      </div>
      <div class="modal-body" id="modal-body"></div>
    </div>
  </div>

  <script>
    // --- Password gate ---
  // ── Clock + uptime ──
  const lkStartT = Date.now();
  setInterval(function(){
    const n = new Date();
    const clk = document.getElementById('lk-clock');
    if(clk) clk.textContent = n.toLocaleTimeString('en-GB',{hour12:false});
    const s=Math.floor((Date.now()-lkStartT)/1000);
    const upt = document.getElementById('lk-uptime');
    if(upt) upt.textContent =
      [Math.floor(s/3600),Math.floor(s%3600/60),s%60].map(function(n){return String(n).padStart(2,'0');}).join(':');
  },1000);

  // ── Progress arc ──
  const lkArc = document.getElementById('lk-arc');
  const LK_CIRC = 2 * Math.PI * 26;
  if(lkArc){ lkArc.style.strokeDasharray = LK_CIRC; lkArc.style.strokeDashoffset = LK_CIRC; }
  function lkSetArc(pct){ if(lkArc) lkArc.style.strokeDashoffset = LK_CIRC*(1-pct/100); }

  // ── Helpers ──
  function lkLogLine(time, text, cls, ms) {
    cls = cls||'ok'; ms = ms||0;
    return new Promise(function(res){
      setTimeout(function(){
        const el=document.createElement('div');
        el.className='lk-log-line';
        el.innerHTML='<span class="lk-log-time">['+time+']</span><span class="lk-log-text lk-'+cls+'">'+text+'</span>';
        const log=document.getElementById('lk-log');
        if(log){ log.appendChild(el); requestAnimationFrame(function(){el.classList.add('show');}); }
        setTimeout(res,120);
      },ms);
    });
  }
  function lkFlash(times,interval){
    times=times||1; interval=interval||80;
    return new Promise(function(res){
      const el=document.getElementById('lk-flash'); let i=0;
      const t=setInterval(function(){
        if(el) el.style.opacity=(i%2===0)?'1':'0';
        i++; if(i>=times*2){clearInterval(t);if(el)el.style.opacity='0';setTimeout(res,100);}
      },interval);
    });
  }
  function lkNow(){ return new Date().toLocaleTimeString('en-GB',{hour12:false}); }
  function lkDelay(ms){ return new Promise(function(r){setTimeout(r,ms);}); }

  // ── Boot sequence ──
  async function lkBoot(){
    const beam=document.getElementById('lk-beam');
    const pupil=document.getElementById('lk-pupil');
    await lkDelay(150);
    if(beam) beam.style.display='block';
    const arcDur=2600, arcStart=Date.now();
    const arcTick=setInterval(function(){
      const pct=Math.min(100,(Date.now()-arcStart)/arcDur*100);
      lkSetArc(pct); if(pct>=100)clearInterval(arcTick);
    },30);
    await lkLogLine(lkNow(),'BIOMETRIC SCAN INITIATED...','ok',0);
    await lkLogLine(lkNow(),'READING RETINA PATTERN...','ok',600);
    await lkLogLine(lkNow(),'MAPPING IRIS GEOMETRY...','ok',1200);
    await lkLogLine(lkNow(),'CROSS-REFERENCING DATABASE...','ok',1900);
    await lkDelay(2600);
    if(beam) beam.style.display='none';
    await lkFlash(2,70);
    await lkLogLine(lkNow(),'RETINA SCAN ··· COMPLETE','ok',0);
    await lkLogLine(lkNow(),'IDENTITY: UNCONFIRMED','warn',0);
    await lkLogLine(lkNow(),'PASSPHRASE REQUIRED TO PROCEED','warn',150);
    if(pupil){
      pupil.style.transition='transform 0.3s ease, box-shadow 0.3s ease';
      pupil.style.animation='none'; pupil.style.transform='scale(1.6)';
      pupil.style.boxShadow='0 0 10px #00ff88, 0 0 24px rgba(0,255,136,0.6)';
      await lkDelay(300); pupil.style.transform='scale(1)';
    }
    await lkDelay(100);
    const hlm=document.getElementById('lk-hl-main');
    const hls=document.getElementById('lk-hl-sub');
    const af=document.getElementById('lk-form');
    if(hlm) hlm.classList.add('show');
    if(hls) hls.classList.add('show');
    await lkDelay(350);
    if(af) af.classList.add('show');
    setTimeout(function(){const pw=document.getElementById('lk-pw');if(pw)pw.focus();},100);
  }

  // ── Auth ──
  const PW_HASH='40c4a34303de2d2edd8538d5d18ec0348850ae3d3e8cc07d947f663e24c08473';
  async function sha256(str){
    const buf=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(str));
    return Array.from(new Uint8Array(buf)).map(function(b){return b.toString(16).padStart(2,'0');}).join('');
  }
  async function lkAuth(){
    const pw=document.getElementById('lk-pw');
    const val=pw?pw.value:'';
    const hash=await sha256(val);
    const err=document.getElementById('lk-err');
    if(hash===PW_HASH){
      await lkFlash(3,60);
      await lkLogLine(lkNow(),'ACCESS GRANTED · WELCOME, OVERLORD','ok',0);
      sessionStorage.setItem('lv_auth','1');
      await lkDelay(600); unlock();
    } else {
      await lkFlash(2,80);
      await lkLogLine(lkNow(),'AUTHENTICATION FAILED','fail',0);
      if(err){ err.textContent='ACCESS DENIED · INVALID PASSPHRASE'; err.classList.add('show'); }
      if(pw) pw.value='';
      setTimeout(function(){const e=document.getElementById('lk-err');if(e)e.classList.remove('show');},3000);
    }
  }
  function unlock(){
    document.getElementById('lock-screen').style.display='none';
    document.getElementById('app-content').style.display='block';
  }
  if(sessionStorage.getItem('lv_auth')==='1'){unlock();}
  else{document.getElementById('lock-screen').style.display='flex';lkBoot();}
// --- End password gate ---

    const UPDATED_AT="%%UPDATED_AT%%";
    const TEAM=%%TEAM_DATA%%;
    const DAYS=["Mon","Tue","Wed","Thu","Fri"];
    const DAY_LABELS={Mon:"Monday",Tue:"Tuesday",Wed:"Wednesday",Thu:"Thursday",Fri:"Friday"};

    function bkkNow(){return new Date(new Date().toLocaleString("en-US",{timeZone:"Asia/Bangkok"}))}
    function parseHHMM(s){const[h,m]=s.split(":").map(Number),d=bkkNow();d.setHours(h,m,0,0);return d}
    function minsUntil(s){return Math.round((parseHHMM(s)-bkkNow())/60000)}
    function localTime(tz){return new Date().toLocaleString("en-GB",{hour:"2-digit",minute:"2-digit",hour12:false,timeZone:tz})}

    function getTimeBadge(p){
      const now=bkkNow();
      // Calendar always wins: find an actively-running event right now
      const a=p.todayEvents.find(e=>{const s=parseHHMM(e.start),en=parseHHMM(e.end);return now>=s&&now<en;});
      if(a){const m=minsUntil(a.end);return{text:m>0?"Free in "+m+"m":"Finishing up",cls:"badge-busy"}}
      // No active calendar event — only trust Slack busy/away if there are NO calendar events
      // (calendar connected but all meetings done means they're free, regardless of stale Slack status)
      if(!p.todayEvents.length&&(p.status==="busy"||p.status==="away")){
        return{text:p.status==="away"?"Away":"Busy",cls:"badge-busy"}
      }
      const n=p.todayEvents.find(e=>now<parseHHMM(e.start));
      if(n){const m=minsUntil(n.start);if(m>0&&m<=60)return{text:"Meeting in "+m+"m",cls:"badge-soon"}}
      return{text:"Free",cls:"badge-free"}
    }

    function buildEventsHtml(ev){
      if(!ev||!ev.length)return'<div class="no-events">No meetings today</div>';
      const now=bkkNow();
      return'<div class="events-divider"></div><div class="events-list">'+ev.map(e=>{
        const s=parseHHMM(e.start),en=parseHHMM(e.end);
        const c=(now>=s&&now<en)?"active":now>=en?"past":"upcoming";
        return'<div class="event-item '+c+'"><div class="event-dot"></div><span class="event-time">'+e.start+'-'+e.end+'</span><span class="event-title">'+e.title+'</span></div>'
      }).join("")+'</div>'
    }

    function buildCard(p){
      const b=getTimeBadge(p);
      const es=b.cls==="badge-busy"?"busy":p.status;
      const est=b.cls==="badge-busy"&&p.status==="available"?"In a meeting":p.statusText;
      const focus=p.focusText?'<div class="focus-block"><div class="focus-label">Working on</div><div class="focus-text">'+p.focusText+'</div></div>':"";
      const slack=p.slackStatus?'<div class="slack-status">'+p.slackStatus+'</div>':"";
      const _h=parseInt(localTime(p.timezone||'Asia/Bangkok'));const offHours=!isNaN(_h)&&(_h<9||_h>=19);
      return'<div class="card '+es+(offHours?' offhours':'')+'">'+
        '<button class="week-btn" onclick="openWeekModal(\''+p.userId+'\')">SHOW WEEK</button>'+
        '<div class="card-header">'+
        '<div class="avatar avatar-'+es+'" id="av-'+p.userId+'">'+p.initials+'</div>'+
        '<div class="info"><div class="name">'+p.name+'</div><div class="status-text status-'+es+'">'+est+'</div>'+slack+'</div>'+
        '</div>'+
        '<div class="time-indicator"><span class="local-time">'+localTime(p.timezone)+'</span><span class="time-badge '+b.cls+'">'+b.text+'</span></div>'+
        buildEventsHtml(p.todayEvents)+focus+
        '</div>'
    }

    function render(){
      const av=TEAM.filter(p=>{const b=getTimeBadge(p);return b.cls!=="badge-busy"&&p.status==="available";}),bu=TEAM.filter(p=>{const b=getTimeBadge(p);return b.cls==="badge-busy"||p.status!=="available";});
      document.getElementById("count-available").textContent=av.length;
      document.getElementById("count-busy").textContent=bu.length;
      document.getElementById("grid-available").innerHTML=av.map(buildCard).join("");
      document.getElementById("grid-busy").innerHTML=bu.map(buildCard).join("");
      const d=new Date(UPDATED_AT);
      document.getElementById("last-updated").textContent=d.toLocaleString("en-GB",{weekday:"short",day:"numeric",month:"short",hour:"2-digit",minute:"2-digit",hour12:false,timeZone:"Asia/Bangkok"});
      loadPhotos();renderAchievements();
    }

    function updateClock(){
      document.getElementById("clock").textContent=new Date().toLocaleString("en-GB",{weekday:"short",hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:false,timeZone:"Asia/Bangkok"})+" BKK"
    }

    function loadPhotos(){
      TEAM.forEach(p=>{
        if(!p.photo)return;
        ["av-","ach-"].forEach(px=>{
          const el=document.getElementById(px+p.userId);
          if(!el||el.querySelector("img"))return;
          const init=el.textContent.trim();el.textContent="";
          const img=document.createElement("img");img.src=p.photo;img.alt=init;
          img.onerror=()=>{el.removeChild(img);el.textContent=init};
          el.appendChild(img);
        });
      });
    }

    function getWeekRange(){
      const now=bkkNow(),day=now.getDay();
      const mon=new Date(now);mon.setDate(now.getDate()-(day===0?6:day-1));
      const fri=new Date(mon);fri.setDate(mon.getDate()+4);
      const fmt=d=>d.toLocaleDateString("en-GB",{day:"numeric",month:"short"});
      return fmt(mon)+" - "+fmt(fri)
    }

    function renderAchievements(){
      const tile=document.getElementById("achievements-tile");
      tile.innerHTML='<div class="achievements-header"><span class="achievements-title">Weekly Wins</span><span class="achievements-week">'+getWeekRange()+'</span></div>';
      TEAM.forEach(p=>{
        const msgs=DAYS.map(d=>({day:d,text:(p.weekMessages||{})[d]})).filter(x=>x.text);
        const row=document.createElement("div");row.className="achievement-row";
        row.innerHTML='<div class="achievement-person"><div class="ach-avatar" id="ach-'+p.userId+'">'+p.initials+'</div><span class="achievement-name">'+p.name+'</span></div>'+
          '<div class="achievement-msgs">'+
          (msgs.length?msgs.map(m=>'<div class="achievement-msg"><span class="ach-day">'+m.day+'</span><span class="ach-text">'+m.text+'</span></div>').join(""):'<div class="no-achievement">No replies this week yet</div>')+
          '</div>';
        tile.appendChild(row);
      });
      loadPhotos();
    }

    function getWeekDates(){
      const now=bkkNow(),day=now.getDay();
      const mon=new Date(now);mon.setDate(now.getDate()-(day===0?6:day-1));
      return DAYS.map((_,i)=>{const d=new Date(mon);d.setDate(mon.getDate()+i);return d});
    }

    function openWeekModal(uid){
      const p=TEAM.find(t=>t.userId===uid);if(!p)return;
      document.getElementById("modal-name").textContent=p.name;
      const av=document.getElementById("modal-avatar");
      av.innerHTML="";
      if(p.photo){const img=document.createElement("img");img.src=p.photo;img.alt=p.initials;img.onerror=()=>{av.textContent=p.initials};av.appendChild(img)}
      else{av.textContent=p.initials}
      const dates=getWeekDates();
      const todayI=(()=>{const d=bkkNow().getDay();return d===0?4:d-1})();
      const body=document.getElementById("modal-body");body.innerHTML="";
      DAYS.forEach((key,i)=>{
        const ev=(p.weekEvents||{})[key]||[];
        const dt=dates[i].toLocaleDateString("en-GB",{day:"numeric",month:"short"});
        const div=document.createElement("div");div.className="week-day";
        div.innerHTML='<div class="week-day-header"><span class="week-day-name'+(i===todayI?" today":"")+'">'+
          (i===todayI?"Today ÃÂÃÂÃÂÃÂ· ":"")+key+'</span><span class="week-day-date">'+dt+'</span></div>'+
          '<div class="week-events">'+
          (ev.length?ev.map(e=>'<div class="week-event"><div class="week-event-dot"></div><span class="week-event-time">'+e.start+'-'+e.end+'</span><span class="week-event-title">'+e.title+'</span></div>').join(""):'<div class="week-no-events">No meetings</div>')+
          '</div>';
        body.appendChild(div);
      });
      document.getElementById("modal-backdrop").classList.add("open");
    }

    function closeModal(e){if(e.target===document.getElementById("modal-backdrop"))document.getElementById("modal-backdrop").classList.remove("open")}

    render();updateClock();setInterval(updateClock,1000);
  </script>
</body>
</html>'''


def generate_html(team_data: list) -> str:
    now_str = datetime.now(BKK_TZ).isoformat(timespec="seconds")
    rows = [{
        "name":         p["name"],
        "initials":     p["initials"],
        "userId":       p["userId"],
        "timezone":     p.get("timezone", "Asia/Bangkok"),
        "status":       p["status"],
        "statusText":   p["statusText"],
        "slackStatus":  p.get("slackStatus", ""),
        "photo":        p.get("photo", ""),
        "todayEvents":  p.get("todayEvents", []),
        "weekEvents":   p.get("weekEvents",  {d: [] for d in DAYS}),
        "weekMessages": p.get("weekMessages", {}),
        "focusText":    p.get("focusText", ""),
    } for p in team_data]
    html = HTML_TEMPLATE.replace("%%UPDATED_AT%%", now_str)
    html = html.replace("%%TEAM_DATA%%", json.dumps(rows, ensure_ascii=False))
    return html.encode("utf-8", errors="replace").decode("utf-8")


# Calendar mode
def run_calendar_mode(creds_file: str):
    print("\nMode: CALENDAR - fetching Google Calendar for all people")
    cache = {"generated_at": datetime.now(BKK_TZ).isoformat(timespec="seconds"), "people": {}}

    for person in TEAM:
        print(f"\n-> {person['name']}")
        cal = get_calendar_info(person["email"], creds_file)
        cache["people"][person["email"]] = {
            "todayEvents": cal.get("todayEvents", []),
            "weekEvents":  cal.get("weekEvents",  {d: [] for d in DAYS}),
            "busyStatus":  {k: v for k, v in cal.items() if k not in ("todayEvents", "weekEvents")},
        }
        n_today = len(cal.get("todayEvents", []))
        n_week  = sum(len(v) for v in cal.get("weekEvents", {}).values())
        print(f"  Today: {n_today} event(s) | Week: {n_week} event(s)")

    out = Path(__file__).parent / "calendar_cache.json"
    out.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    errors = {email: data.get("busyStatus", {}).get("_error") for email, data in cache["people"].items() if data.get("busyStatus", {}).get("_error")}
    if errors:
        print(f"\nÃÂÃÂ¢ÃÂÃÂÃÂÃÂ ÃÂÃÂ¯ÃÂÃÂ¸ÃÂÃÂ  Errors encountered: {json.dumps(errors, indent=2)}")
    print(f"\nÃÂÃÂ¢ÃÂÃÂÃÂÃÂ calendar_cache.json written ({len(cache['people'])} people)")


# Slack mode
def run_slack_mode(slack_token: str, creds_file: str = None):
    print("\nMode: SLACK - fetching Slack statuses + weekly focus")

    # Load calendar cache
    cache_path = Path(__file__).parent / "calendar_cache.json"
    cal_cache  = {}
    if cache_path.exists():
        try:
            cal_cache = json.loads(cache_path.read_text(encoding="utf-8")).get("people", {})
            print(f"ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ Calendar cache loaded ({len(cal_cache)} people)")
        except Exception as e:
            print(f"Warning: Could not read calendar cache: {e}")
    else:
        print("Warning: No calendar_cache.json found - run calendar mode first")

    from slack_sdk import WebClient
    slack_client = WebClient(token=slack_token)
    print("ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ Slack connected")

    today_key = DAYS[datetime.now(BKK_TZ).weekday()] if datetime.now(BKK_TZ).weekday() < 5 else None

    def fetch_person(person):
        entry = {
            **person,
            "status": "available", "statusText": "Available",
            "slackStatus": "", "photo": "",
            "todayEvents": [], "weekEvents": {d: [] for d in DAYS},
            "weekMessages": {}, "focusText": "",
        }

        # 1. Calendar from cache
        cached = cal_cache.get(person["email"], {})
        entry["todayEvents"] = cached.get("todayEvents", [])
        entry["weekEvents"]  = cached.get("weekEvents",  {d: [] for d in DAYS})
        # Recompute live busy status from todayEvents (cache may be stale)
        now_hhmm = datetime.now(BKK_TZ).strftime("%H:%M")
        live_event = next(
            (e for e in entry["todayEvents"] if e["start"] <= now_hhmm < e["end"]),
            None
        )
        busy = {"busy": True, "event": live_event["title"], "until": live_event["end"]} if live_event else {}
        if busy.get("busy"):
            event = busy.get("event", "In a meeting")
            until = busy.get("until", "")
            entry["status"]     = "busy"
            entry["statusText"] = f"\U0001f4c5 {event}" + (f" until {until}" if until else "")

        # 2. Weekly focus DMs (resets every Monday automatically)
        entry["weekMessages"] = get_weekly_focus_from_dm(person["userId"], slack_client)
        if today_key and today_key in entry["weekMessages"]:
            entry["focusText"] = entry["weekMessages"][today_key]

        # 3. Slack status + photo
        slack = get_slack_status(person["userId"], slack_client)
        entry["photo"] = slack.get("photo", "")
        if slack["text"]:
            entry["slackStatus"] = slack["display"]
            if entry["status"] == "available":
                sc = classify_slack(slack)
                entry["status"] = sc
                if sc != "available":
                    entry["statusText"] = slack["display"]

        return entry

    with ThreadPoolExecutor(max_workers=9) as ex:
        team_data = list(ex.map(fetch_person, TEAM))

    for p in team_data:
        print(f"  {'ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ' if p['status']=='available' else 'ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ'} {p['name']}: {p['status']} - {p['statusText'] or '-'}")

    out = Path(__file__).parent / "index.html"
    out.write_text(generate_html(team_data), encoding="utf-8")
    print(f"\nÃÂÃÂ¢ÃÂÃÂÃÂÃÂ index.html written ({len(team_data)} people)")


# Entry point
def main():
    print(f"\n{'='*52}\nLevitask Dashboard - {datetime.now(BKK_TZ).strftime('%Y-%m-%d %H:%M BKK')}\n{'='*52}")
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["calendar", "slack"], default="slack")
    args = parser.parse_args()

    slack_token      = os.environ.get("SLACK_BOT_TOKEN", "")
    google_creds_raw = os.environ.get("GOOGLE_CREDENTIALS", "")

    creds_file = None
    if google_creds_raw:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp.write(google_creds_raw)
        tmp.close()
        creds_file = tmp.name
        print("ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ Google credentials loaded")
    else:
        print("Warning: No GOOGLE_CREDENTIALS")

    try:
        if args.mode == "calendar":
            if not creds_file:
                print("Error: Calendar mode requires GOOGLE_CREDENTIALS")
                return
            run_calendar_mode(creds_file)
        else:
            if not slack_token:
                print("Error: Slack mode requires SLACK_BOT_TOKEN")
                return
            run_slack_mode(slack_token, creds_file)
    finally:
        if creds_file:
            os.unlink(creds_file)


if __name__ == "__main__":
    main()
