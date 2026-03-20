#!/usr/bin/env python3
"""
Levitask Team Availability Dashboard Ã¢ÂÂ Cloud Refresh Script

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
    ":car:": "Ã°ÂÂÂ", ":bus:": "Ã°ÂÂÂ", ":airplane:": "Ã¢ÂÂÃ¯Â¸Â", ":train:": "Ã°ÂÂÂ", ":bike:": "Ã°ÂÂÂ²",
    ":walking:": "Ã°ÂÂÂ¶", ":house:": "Ã°ÂÂÂ ", ":house_with_garden:": "Ã°ÂÂÂ¡", ":coffee:": "Ã¢ÂÂ",
    ":tea:": "Ã°ÂÂÂµ", ":lunch:": "Ã°ÂÂÂ±", ":fork_and_knife:": "Ã°ÂÂÂ´", ":headphones:": "Ã°ÂÂÂ§",
    ":computer:": "Ã°ÂÂÂ»", ":desktop_computer:": "Ã°ÂÂÂ¥Ã¯Â¸Â", ":no_entry:": "Ã¢ÂÂ",
    ":no_entry_sign:": "Ã°ÂÂÂ«", ":red_circle:": "Ã°ÂÂÂ´", ":red_square:": "Ã°ÂÂÂ¥",
    ":large_red_square:": "Ã°ÂÂÂ¥", ":orange_square:": "Ã°ÂÂÂ§", ":yellow_square:": "Ã°ÂÂÂ¨",
    ":green_square:": "Ã°ÂÂÂ©", ":blue_square:": "Ã°ÂÂÂ¦", ":purple_square:": "Ã°ÂÂÂª",
    ":brown_square:": "Ã°ÂÂÂ«", ":black_large_square:": "Ã¢Â¬Â", ":orange_circle:": "Ã°ÂÂÂ ",
    ":yellow_circle:": "Ã°ÂÂÂ¡", ":green_circle:": "Ã°ÂÂÂ¢", ":blue_circle:": "Ã°ÂÂÂµ",
    ":purple_circle:": "Ã°ÂÂÂ£", ":brown_circle:": "Ã°ÂÂÂ¤", ":calendar:": "Ã°ÂÂÂ",
    ":spiral_calendar_pad:": "Ã°ÂÂÂÃ¯Â¸Â", ":clock1:": "Ã°ÂÂÂ", ":rocket:": "Ã°ÂÂÂ",
    ":dart:": "Ã°ÂÂÂ¯", ":palm_tree:": "Ã°ÂÂÂ´", ":beach_with_umbrella:": "Ã°ÂÂÂÃ¯Â¸Â",
    ":globe_with_meridians:": "Ã°ÂÂÂ", ":earth_asia:": "Ã°ÂÂÂ", ":earth_americas:": "Ã°ÂÂÂ",
    ":thermometer:": "Ã°ÂÂÂ¡Ã¯Â¸Â", ":mask:": "Ã°ÂÂÂ·", ":face_with_thermometer:": "Ã°ÂÂ¤Â",
    ":zzz:": "Ã°ÂÂÂ¤", ":sleeping:": "Ã°ÂÂÂ´", ":phone:": "Ã°ÂÂÂ", ":telephone_receiver:": "Ã°ÂÂÂ",
    ":pencil:": "Ã¢ÂÂÃ¯Â¸Â", ":pencil2:": "Ã¢ÂÂÃ¯Â¸Â", ":book:": "Ã°ÂÂÂ", ":books:": "Ã°ÂÂÂ",
    ":tada:": "Ã°ÂÂÂ", ":sparkles:": "Ã¢ÂÂ¨", ":fire:": "Ã°ÂÂÂ¥", ":star:": "Ã¢Â­Â",
    ":white_check_mark:": "Ã¢ÂÂ", ":x:": "Ã¢ÂÂ", ":warning:": "Ã¢ÂÂ Ã¯Â¸Â", ":mega:": "Ã°ÂÂÂ£",
    ":loudspeaker:": "Ã°ÂÂÂ¢", ":speech_balloon:": "Ã°ÂÂÂ¬", ":construction:": "Ã°ÂÂÂ§",
    ":hammer:": "Ã°ÂÂÂ¨", ":wrench:": "Ã°ÂÂÂ§", ":seedling:": "Ã°ÂÂÂ±", ":sunny:": "Ã¢ÂÂÃ¯Â¸Â",
    ":umbrella:": "Ã¢ÂÂÃ¯Â¸Â", ":muscle:": "Ã°ÂÂÂª", ":raising_hand:": "Ã°ÂÂÂ", ":wave:": "Ã°ÂÂÂ",
    ":brain:": "Ã°ÂÂ§Â ", ":bulb:": "Ã°ÂÂÂ¡", ":technologist:": "Ã°ÂÂ§ÂÃ¢ÂÂÃ°ÂÂÂ»", ":nerd_face:": "Ã°ÂÂ¤Â",
    ":monocle_face:": "Ã°ÂÂ§Â", ":thinking_face:": "Ã°ÂÂ¤Â", ":male-technologist:": "Ã°ÂÂÂ¨Ã¢ÂÂÃ°ÂÂÂ»",
    ":female-technologist:": "Ã°ÂÂÂ©Ã¢ÂÂÃ°ÂÂÂ»", ":eyes:": "Ã°ÂÂÂ", ":writing_hand:": "Ã¢ÂÂÃ¯Â¸Â",
    ":memo:": "Ã°ÂÂÂ", ":mag:": "Ã°ÂÂÂ", ":chart_with_upwards_trend:": "Ã°ÂÂÂ",
    ":bar_chart:": "Ã°ÂÂÂ", ":pushpin:": "Ã°ÂÂÂ", ":paperclip:": "Ã°ÂÂÂ",
    ":inbox_tray:": "Ã°ÂÂÂ¥", ":outbox_tray:": "Ã°ÂÂÂ¤", ":email:": "Ã°ÂÂÂ§",
    ":bell:": "Ã°ÂÂÂ", ":no_bell:": "Ã°ÂÂÂ", ":mute:": "Ã°ÂÂÂ", ":microphone:": "Ã°ÂÂÂ¤",
    ":hourglass:": "Ã¢ÂÂ", ":hourglass_flowing_sand:": "Ã¢ÂÂ³", ":stopwatch:": "Ã¢ÂÂ±Ã¯Â¸Â",
    ":flag-th:": "Ã°ÂÂÂ¹Ã°ÂÂÂ­", ":flag-fr:": "Ã°ÂÂÂ«Ã°ÂÂÂ·", ":flag-be:": "Ã°ÂÂÂ§Ã°ÂÂÂª",
    ":flag-es:": "Ã°ÂÂÂªÃ°ÂÂÂ¸", ":flag-us:": "Ã°ÂÂÂºÃ°ÂÂÂ¸", ":flag-gb:": "Ã°ÂÂÂ¬Ã°ÂÂÂ§",
    ":raised_hands:": "Ã°ÂÂÂ", ":clap:": "Ã°ÂÂÂ", ":pray:": "Ã°ÂÂÂ", ":ok_hand:": "Ã°ÂÂÂ",
    ":thumbsup:": "Ã°ÂÂÂ", ":thumbsdown:": "Ã°ÂÂÂ", ":slightly_smiling_face:": "Ã°ÂÂÂ",
    ":blush:": "Ã°ÂÂÂ", ":sweat_smile:": "Ã°ÂÂÂ", ":cityscape:": "Ã°ÂÂÂÃ¯Â¸Â",
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
        display = (emoji_unicode + " " + status_text).strip() if status_text else emoji_unicode
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
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="logo">L</div>
      <div><h1>LEVITASK <span>TEAM</span></h1><div class="subtitle">Availability Dashboard</div></div>
    </div>
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
  <footer>Levitask HQ &nbsp;ÃÂ·&nbsp; Slack + Google Calendar</footer>

  <div class="modal-backdrop" id="modal-backdrop" onclick="closeModal(event)">
    <div class="modal">
      <div class="modal-header">
        <div class="modal-person">
          <div class="modal-avatar" id="modal-avatar">-</div>
          <div><div class="modal-name" id="modal-name">-</div><div class="modal-subtitle">This week's calendar</div></div>
        </div>
        <button class="modal-close" onclick="document.getElementById('modal-backdrop').classList.remove('open')">ÃÂ</button>
      </div>
      <div class="modal-body" id="modal-body"></div>
    </div>
  </div>

  <script>
    const UPDATED_AT="%%UPDATED_AT%%";
    const TEAM=%%TEAM_DATA%%;
    const DAYS=["Mon","Tue","Wed","Thu","Fri"];
    const DAY_LABELS={Mon:"Monday",Tue:"Tuesday",Wed:"Wednesday",Thu:"Thursday",Fri:"Friday"};

    function bkkNow(){return new Date(new Date().toLocaleString("en-US",{timeZone:"Asia/Bangkok"}))}
    function parseHHMM(s){const[h,m]=s.split(":").map(Number),d=bkkNow();d.setHours(h,m,0,0);return d}
    function minsUntil(s){return Math.round((parseHHMM(s)-bkkNow())/60000)}
    function localTime(tz){return new Date().toLocaleString("en-GB",{hour:"2-digit",minute:"2-digit",hour12:false,timeZone:tz})}

    function getTimeBadge(p){
      if(p.status==="busy"||p.status==="away"){
        const a=p.todayEvents.find(e=>e.active);
        if(a){const m=minsUntil(a.end);return{text:m>0?"Free in "+m+"m":"Finishing up",cls:"badge-busy"}}
        return{text:"Busy",cls:"badge-busy"}
      }
      const n=p.todayEvents.find(e=>!e.past&&!e.active);
      if(n){const m=minsUntil(n.start);if(m>0&&m<=60)return{text:"Meeting in "+m+"m",cls:"badge-soon"}}
      return{text:"Free",cls:"badge-free"}
    }

    function buildEventsHtml(ev){
      if(!ev||!ev.length)return'<div class="no-events">No meetings today</div>';
      return'<div class="events-divider"></div><div class="events-list">'+ev.map(e=>{
        const c=e.active?"active":e.past?"past":"upcoming";
        return'<div class="event-item '+c+'"><div class="event-dot"></div><span class="event-time">'+e.start+'-'+e.end+'</span><span class="event-title">'+e.title+'</span></div>'
      }).join("")+'</div>'
    }

    function buildCard(p){
      const b=getTimeBadge(p);
      const focus=p.focusText?'<div class="focus-block"><div class="focus-label">Working on</div><div class="focus-text">'+p.focusText+'</div></div>':"";
      const slack=p.slackStatus?'<div class="slack-status">'+p.slackStatus+'</div>':"";
      const _h=parseInt(localTime(p.timezone||'Asia/Bangkok'));const offHours=!isNaN(_h)&&(_h<9||_h>=19);
      return'<div class="card '+p.status+(offHours?' offhours':'')+'">'+
        '<button class="week-btn" onclick="openWeekModal(\''+p.userId+'\')">SHOW WEEK</button>'+
        '<div class="card-header">'+
        '<div class="avatar avatar-'+p.status+'" id="av-'+p.userId+'">'+p.initials+'</div>'+
        '<div class="info"><div class="name">'+p.name+'</div><div class="status-text status-'+p.status+'">'+p.statusText+'</div>'+slack+'</div>'+
        '</div>'+
        '<div class="time-indicator"><span class="local-time">'+localTime(p.timezone)+'</span><span class="time-badge '+b.cls+'">'+b.text+'</span></div>'+
        buildEventsHtml(p.todayEvents)+focus+
        '</div>'
    }

    function render(){
      const av=TEAM.filter(p=>p.status==="available"),bu=TEAM.filter(p=>p.status!=="available");
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
          (i===todayI?"Today ÃÂ· ":"")+key+'</span><span class="week-day-date">'+dt+'</span></div>'+
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
        print(f"\nÃ¢ÂÂ Ã¯Â¸Â  Errors encountered: {json.dumps(errors, indent=2)}")
    print(f"\nÃ¢ÂÂ calendar_cache.json written ({len(cache['people'])} people)")


# Slack mode
def run_slack_mode(slack_token: str, creds_file: str = None):
    print("\nMode: SLACK - fetching Slack statuses + weekly focus")

    # Load calendar cache
    cache_path = Path(__file__).parent / "calendar_cache.json"
    cal_cache  = {}
    if cache_path.exists():
        try:
            cal_cache = json.loads(cache_path.read_text(encoding="utf-8")).get("people", {})
            print(f"Ã¢ÂÂ Calendar cache loaded ({len(cal_cache)} people)")
        except Exception as e:
            print(f"Warning: Could not read calendar cache: {e}")
    else:
        print("Warning: No calendar_cache.json found - run calendar mode first")

    from slack_sdk import WebClient
    slack_client = WebClient(token=slack_token)
    print("Ã¢ÂÂ Slack connected")

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
        busy = cached.get("busyStatus", {})
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
        print(f"  {'Ã¢ÂÂ' if p['status']=='available' else 'Ã¢ÂÂ'} {p['name']}: {p['status']} - {p['statusText'] or '-'}")

    out = Path(__file__).parent / "index.html"
    out.write_text(generate_html(team_data), encoding="utf-8")
    print(f"\nÃ¢ÂÂ index.html written ({len(team_data)} people)")


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
        print("Ã¢ÂÂ Google credentials loaded")
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
