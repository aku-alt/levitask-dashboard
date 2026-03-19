#!/usr/bin/env python3
"""
Levitask Team Availability Dashboard — Cloud Refresh Script
Runs in GitHub Actions: fetches Slack statuses + Google Calendar, writes index.html
"""

import json
import os
import re
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

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

# ── Slack ─────────────────────────────────────────────────────────────────────

def get_slack_status(user_id: str, client) -> dict:
    try:
        resp = client.users_info(user=user_id)
        profile = resp["user"]["profile"]
        status_text  = profile.get("status_text", "").strip()
        status_emoji = profile.get("status_emoji", "").strip()
        return {"text": status_text, "emoji": status_emoji}
    except Exception as e:
        print(f"  Slack error for {user_id}: {e}")
        return {"text": "", "emoji": ""}


# ── Google Calendar ───────────────────────────────────────────────────────────

def get_calendar_info(email: str, creds_file: str) -> dict:
    """Returns current status + all of today's events."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_file(
            creds_file,
            scopes=["https://www.googleapis.com/auth/calendar.readonly"]
        ).with_subject(email)

        service = build("calendar", "v3", credentials=creds, cache_discovery=False)

        now = datetime.now(timezone.utc)

        # Fetch from start of today to end of today (BKK time)
        today_bkk    = now.astimezone(BKK_TZ)
        start_of_day = today_bkk.replace(hour=0,  minute=0,  second=0,  microsecond=0)
        end_of_day   = today_bkk.replace(hour=23, minute=59, second=59, microsecond=0)

        result = service.events().list(
            calendarId="primary",
            timeMin=start_of_day.isoformat(),
            timeMax=end_of_day.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=20,
        ).execute()

        events = result.get("items", [])
        today_events   = []
        current_status = {"busy": False}

        for event in events:
            # Skip declined events
            attendees = event.get("attendees", [])
            declined = any(
                a.get("email") == email and a.get("responseStatus") == "declined"
                for a in attendees
            )
            if declined:
                continue

            # Skip all-day events (no dateTime)
            start_raw = event.get("start", {})
            end_raw   = event.get("end",   {})
            if "dateTime" not in start_raw:
                continue

            start_dt = _parse_dt(start_raw)
            end_dt   = _parse_dt(end_raw)
            if not start_dt or not end_dt:
                continue

            title     = event.get("summary", "Meeting")
            start_str = start_dt.astimezone(BKK_TZ).strftime("%H:%M")
            end_str   = end_dt.astimezone(BKK_TZ).strftime("%H:%M")
            is_active = start_dt <= now <= end_dt
            is_past   = end_dt < now

            today_events.append({
                "title":  title,
                "start":  start_str,
                "end":    end_str,
                "active": is_active,
                "past":   is_past,
            })

            # Determine current status from first matching window
            if is_active and not current_status.get("busy"):
                current_status = {"busy": True, "event": title, "until": end_str}
            elif not current_status.get("busy") and not current_status.get("upcoming"):
                if now < start_dt <= now + timedelta(minutes=5):
                    current_status = {"busy": False, "upcoming": title, "at": start_str}

        return {**current_status, "todayEvents": today_events}

    except Exception as e:
        print(f"  Calendar error for {email}: {e}")
        return {"busy": False, "todayEvents": [], "error": str(e)}


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


# ── Status classification ─────────────────────────────────────────────────────

BUSY_KEYWORDS = {"meeting", "busy", "call", "unavailable", "lunch", "brb",
                 "ooo", "out of office", "vacation", "sick", "dnd", "do not disturb"}
AWAY_KEYWORDS = {"commuting", "away", "transit"}

def classify_slack(slack: dict) -> tuple[str, str]:
    """Returns (status_class, display_text)"""
    text  = slack["text"].lower()
    emoji = slack["emoji"]
    raw   = slack["text"]

    if not raw:
        return "available", ""

    if any(k in text for k in AWAY_KEYWORDS) or emoji in (":car:", ":bus:", ":train:", ":airplane:"):
        return "away", f"{emoji} {raw}".strip()

    if any(k in text for k in BUSY_KEYWORDS) or emoji in (":no_entry:", ":x:", ":red_circle:"):
        return "busy", f"{emoji} {raw}".strip()

    return "busy", f"{emoji} {raw}".strip()


# ── HTML generation ───────────────────────────────────────────────────────────

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="refresh" content="60">
  <title>Levitask – Team Availability</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f1117; color: #e8eaf0; min-height: 100vh; padding: 32px 24px; }
    header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 36px; border-bottom: 1px solid #1e2130; padding-bottom: 20px; }
    .brand { display: flex; align-items: center; gap: 14px; }
    .logo { width: 40px; height: 40px; background: linear-gradient(135deg, #4f8ef7, #7b61ff); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 18px; color: #fff; }
    h1 { font-size: 22px; font-weight: 600; color: #fff; } h1 span { color: #4f8ef7; }
    .meta { text-align: right; font-size: 12px; color: #5a6075; line-height: 1.7; }
    .meta #clock { font-size: 16px; font-weight: 500; color: #9aa3b8; }
    .summary { display: flex; gap: 16px; margin-bottom: 28px; }
    .summary-pill { display: flex; align-items: center; gap: 8px; background: #161b27; border: 1px solid #1e2130; border-radius: 30px; padding: 8px 18px; font-size: 13px; font-weight: 500; }
    .dot { width: 8px; height: 8px; border-radius: 50%; }
    .dot-available { background: #2dd4a0; box-shadow: 0 0 6px #2dd4a066; }
    .dot-busy { background: #f87171; box-shadow: 0 0 6px #f8717166; }
    .summary-count { font-size: 18px; font-weight: 700; }
    .count-available { color: #2dd4a0; } .count-busy { color: #f87171; }
    .section-label { font-size: 11px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: #3d4460; margin-bottom: 14px; margin-top: 28px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px; }

    /* Card — vertical layout */
    .card { background: #161b27; border: 1px solid #1e2130; border-radius: 14px; padding: 18px 20px; display: flex; flex-direction: column; gap: 0; transition: border-color 0.2s, transform 0.15s; text-decoration: none; color: inherit; }
    .card:hover { border-color: #2a3050; transform: translateY(-2px); }
    .card:hover .dm-icon { opacity: 1; }
    .card.available { border-left: 3px solid #2dd4a0; }
    .card.busy      { border-left: 3px solid #f87171; }
    .card.away      { border-left: 3px solid #fbbf24; }

    /* Card header row */
    .card-header { display: flex; align-items: center; gap: 14px; }
    .dm-icon { font-size: 15px; opacity: 0; transition: opacity 0.15s; flex-shrink: 0; margin-left: auto; }

    /* Avatar — bigger */
    .avatar { width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: 700; flex-shrink: 0; position: relative; }
    .avatar-available { background: #0f2a22; color: #2dd4a0; }
    .avatar-busy      { background: #2a1111; color: #f87171; }
    .avatar-away      { background: #2a2011; color: #fbbf24; }
    .avatar::after { content: ''; position: absolute; bottom: 2px; right: 2px; width: 13px; height: 13px; border-radius: 50%; border: 2px solid #161b27; }
    .available .avatar::after { background: #2dd4a0; }
    .busy .avatar::after      { background: #f87171; }
    .away .avatar::after      { background: #fbbf24; }

    .info { flex: 1; min-width: 0; }
    .name { font-size: 15px; font-weight: 600; color: #e8eaf0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .status-text { font-size: 12px; margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .status-available { color: #2dd4a0; } .status-busy { color: #f87171; } .status-away { color: #fbbf24; }

    /* Today's events */
    .events-divider { height: 1px; background: #1e2130; margin: 14px 0 10px; }
    .events-list { display: flex; flex-direction: column; gap: 5px; }
    .event-item { display: flex; align-items: baseline; gap: 8px; font-size: 11.5px; }
    .event-time { color: #5a6075; flex-shrink: 0; font-variant-numeric: tabular-nums; min-width: 42px; }
    .event-title { color: #9aa3b8; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .event-item.active .event-time  { color: #f87171; font-weight: 600; }
    .event-item.active .event-title { color: #e8eaf0; font-weight: 500; }
    .event-item.past  .event-time  { color: #343a52; }
    .event-item.past  .event-title { color: #343a52; }

    footer { margin-top: 44px; text-align: center; font-size: 11px; color: #2a3050; border-top: 1px solid #1e2130; padding-top: 16px; }
  </style>
</head>
<body>
<header>
  <div class="brand"><div class="logo">L</div><div><h1>Levitask <span>Team</span></h1><div style="font-size:12px;color:#3d4460;margin-top:2px;">Availability Dashboard</div></div></div>
  <div class="meta"><div id="clock">–</div><div>Last updated: <span id="last-updated">–</span></div><div>Auto-refreshes every 60 s</div></div>
</header>
<div class="summary">
  <div class="summary-pill"><div class="dot dot-available"></div><span class="summary-count count-available" id="count-available">–</span><span>Available</span></div>
  <div class="summary-pill"><div class="dot dot-busy"></div><span class="summary-count count-busy" id="count-busy">–</span><span>Busy / DND</span></div>
</div>
<div class="section-label">✅ Available</div>
<div class="grid" id="grid-available"></div>
<div class="section-label">🔴 Busy / Do Not Disturb</div>
<div class="grid" id="grid-busy"></div>
<footer>Levitask HQ · Slack + Google Calendar · Auto-refreshes every minute</footer>
<script>
  const UPDATED_AT = "%%UPDATED_AT%%";
  const TEAM = %%TEAM_DATA%%;

  function buildEventsHtml(events) {
    if (!events || events.length === 0) return "";
    const rows = events.map(e => {
      const cls = e.active ? " active" : (e.past ? " past" : "");
      return "<div class=\\"event-item" + cls + "\\">" +
        "<span class=\\"event-time\\">" + e.start + "</span>" +
        "<span class=\\"event-title\\">" + e.title + "</span></div>";
    }).join("");
    return "<div class=\\"events-divider\\"></div><div class=\\"events-list\\">" + rows + "</div>";
  }

  function buildCard(p) {
    const href = "https://levitaskworkspace.slack.com/messages/" + p.userId;
    return "<a class=\\"card " + p.status + "\\" href=\\"" + href + "\\" target=\\"_blank\\" rel=\\"noopener\\">" +
      "<div class=\\"card-header\\">" +
      "<div class=\\"avatar avatar-" + p.status + "\\">" + p.initials + "</div>" +
      "<div class=\\"info\\"><div class=\\"name\\">" + p.name + "</div>" +
      "<div class=\\"status-text status-" + p.status + "\\">" + p.statusText + "</div></div>" +
      "<div class=\\"dm-icon\\">💬</div></div>" +
      buildEventsHtml(p.todayEvents) +
      "</a>";
  }

  function render() {
    const avail = TEAM.filter(p => p.status === "available");
    const busy  = TEAM.filter(p => p.status !== "available");
    document.getElementById("count-available").textContent = avail.length;
    document.getElementById("count-busy").textContent = busy.length;
    document.getElementById("grid-available").innerHTML = avail.map(buildCard).join("");
    document.getElementById("grid-busy").innerHTML = busy.map(buildCard).join("");
    const d = new Date(UPDATED_AT);
    document.getElementById("last-updated").textContent = d.toLocaleString("en-GB", {weekday:"short",day:"numeric",month:"short",year:"numeric",hour:"2-digit",minute:"2-digit",hour12:false,timeZone:"Asia/Bangkok"});
  }

  function updateClock() {
    document.getElementById("clock").textContent = new Date().toLocaleString("en-GB", {weekday:"short",hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:false,timeZone:"Asia/Bangkok"}) + " BKK";
  }

  render(); updateClock(); setInterval(updateClock, 10000);
</script>
</body>
</html>'''


def generate_html(team_data: list) -> str:
    now_str = datetime.now(BKK_TZ).isoformat(timespec="seconds")

    rows = []
    for p in team_data:
        rows.append({
            "name":        p["name"],
            "initials":    p["initials"],
            "userId":      p["userId"],
            "status":      p["status"],
            "statusText":  p["statusText"],
            "todayEvents": p.get("todayEvents", []),
        })

    html = HTML_TEMPLATE
    html = html.replace("%%UPDATED_AT%%", now_str)
    html = html.replace("%%TEAM_DATA%%", json.dumps(rows, ensure_ascii=False))
    return html


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*50}")
    print(f"Levitask Dashboard — {datetime.now(BKK_TZ).strftime('%Y-%m-%d %H:%M BKK')}")
    print(f"{'='*50}\n")

    slack_token      = os.environ.get("SLACK_TOKEN", "")
    google_creds_raw = os.environ.get("GOOGLE_CREDENTIALS", "")

    slack_client = None
    if slack_token:
        from slack_sdk import WebClient
        slack_client = WebClient(token=slack_token)
        print("✓ Slack connected")
    else:
        print("⚠ No SLACK_TOKEN — skipping Slack statuses")

    creds_file = None
    if google_creds_raw:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp.write(google_creds_raw)
        tmp.close()
        creds_file = tmp.name
        print("✓ Google credentials loaded")
    else:
        print("⚠ No GOOGLE_CREDENTIALS — skipping calendar")

    team_data = []

    for person in TEAM:
        print(f"\n→ {person['name']}")
        entry = {**person, "status": "available", "statusText": "Available", "todayEvents": []}

        # 1. Google Calendar (highest priority)
        if creds_file:
            cal = get_calendar_info(person["email"], creds_file)
            entry["todayEvents"] = cal.get("todayEvents", [])

            if cal.get("busy"):
                event = cal.get("event", "In a meeting")
                until = cal.get("until", "")
                entry["status"]     = "busy"
                entry["statusText"] = f"📅 {event}" + (f" until {until}" if until else "")
                print(f"  Calendar: BUSY — {event}" + (f" until {until}" if until else ""))
            elif cal.get("upcoming"):
                entry["statusText"] = f"⏰ {cal['upcoming']} at {cal['at']}"
                print(f"  Calendar: free (upcoming {cal['upcoming']} at {cal['at']})")
            else:
                n = len(entry["todayEvents"])
                print(f"  Calendar: free ({n} event{'s' if n != 1 else ''} today)")

        # 2. Slack status (only if calendar says available)
        if slack_client and entry["status"] == "available":
            slack = get_slack_status(person["userId"], slack_client)
            if slack["text"]:
                status_class, display = classify_slack(slack)
                entry["status"]     = status_class
                entry["statusText"] = display
                print(f"  Slack: {status_class} — {display}")
            else:
                print(f"  Slack: no status")

        team_data.append(entry)

    out_path = Path(__file__).parent / "index.html"
    out_path.write_text(generate_html(team_data), encoding="utf-8")
    print(f"\n✓ index.html written ({len(team_data)} people)")

    if creds_file:
        os.unlink(creds_file)


if __name__ == "__main__":
    main()
