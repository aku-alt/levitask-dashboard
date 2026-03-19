#!/usr/bin/env python3
"""
Levitask Team Availability Dashboard — Calendar Refresh Script
Reads Google Calendar for each team member and updates team-availability.html
"""

import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ── Config ────────────────────────────────────────────────────────────────────

SCRIPT_DIR   = Path(__file__).parent
CREDS_FILE   = SCRIPT_DIR / "levitask-credentials.json"
DASHBOARD    = SCRIPT_DIR / "team-availability.html"

SCOPES       = ["https://www.googleapis.com/auth/calendar.readonly"]
BKK_TZ       = timezone(timedelta(hours=7))

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

# ── Google Calendar helpers ───────────────────────────────────────────────────

def get_calendar_status(email: str) -> dict:
    """Returns {busy, event_title, until} for the given user right now."""
    try:
        creds = service_account.Credentials.from_service_account_file(
            str(CREDS_FILE), scopes=SCOPES
        ).with_subject(email)

        service = build("calendar", "v3", credentials=creds, cache_discovery=False)

        now     = datetime.now(timezone.utc)
        now_str = now.isoformat()
        end_str = (now + timedelta(minutes=1)).isoformat()

        result = service.events().list(
            calendarId="primary",
            timeMin=now_str,
            timeMax=(now + timedelta(hours=8)).isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=5,
        ).execute()

        events = result.get("items", [])

        for event in events:
            # Skip declined events
            attendees = event.get("attendees", [])
            declined = any(
                a.get("email") == email and a.get("responseStatus") == "declined"
                for a in attendees
            )
            if declined:
                continue

            start = event.get("start", {})
            end   = event.get("end",   {})

            # Parse start/end
            start_dt = _parse_dt(start)
            end_dt   = _parse_dt(end)

            if start_dt is None or end_dt is None:
                continue

            # Check if happening right now
            if start_dt <= now <= end_dt:
                title    = event.get("summary", "In a meeting")
                until    = end_dt.astimezone(BKK_TZ).strftime("%H:%M")
                return {"busy": True, "event": title, "until": until}

            # Check if starting within 5 minutes
            if now < start_dt <= now + timedelta(minutes=5):
                title = event.get("summary", "Meeting starting soon")
                at    = start_dt.astimezone(BKK_TZ).strftime("%H:%M")
                return {"busy": False, "upcoming": title, "at": at}

        return {"busy": False}

    except HttpError as e:
        print(f"  Calendar API error for {email}: {e}")
        return {"busy": False, "error": str(e)}
    except Exception as e:
        print(f"  Error for {email}: {e}")
        return {"busy": False, "error": str(e)}


def _parse_dt(dt_dict: dict):
    """Parse a Google Calendar datetime or date dict into an aware datetime."""
    if "dateTime" in dt_dict:
        s = dt_dict["dateTime"]
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None
    elif "date" in dt_dict:
        # All-day event — treat as start of day UTC
        try:
            d = datetime.strptime(dt_dict["date"], "%Y-%m-%d")
            return d.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


# ── HTML update ───────────────────────────────────────────────────────────────

def build_team_js(results: list) -> str:
    lines = []
    for r in results:
        status      = r["status"]
        status_text = r["statusText"]
        slack_status = r.get("slackStatus", "")
        lines.append(
            f'    {{ name: "{r["name"]}", initials: "{r["initials"]}", '
            f'userId: "{r["userId"]}", status: "{status}", '
            f'statusText: "{status_text}", '
            f'timezone: "{r["timezone"]}", slackStatus: "{slack_status}" }},'
        )
    return "[\n" + "\n".join(lines) + "\n  ]"


def update_html(team_data: list):
    if not DASHBOARD.exists():
        print(f"Dashboard not found at {DASHBOARD}")
        return

    html = DASHBOARD.read_text(encoding="utf-8")

    # Update timestamp
    now_str = datetime.now(BKK_TZ).isoformat(timespec="seconds")
    html = re.sub(
        r'const UPDATED_AT = "[^"]*"',
        f'const UPDATED_AT = "{now_str}"',
        html
    )

    # Update TEAM array
    new_team_js = build_team_js(team_data)
    html = re.sub(
        r'const TEAM = \[[\s\S]*?\];',
        f'const TEAM = {new_team_js};',
        html
    )

    DASHBOARD.write_text(html, encoding="utf-8")
    print(f"Dashboard updated at {now_str}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*50}")
    print(f"Levitask Dashboard Refresh — {datetime.now(BKK_TZ).strftime('%Y-%m-%d %H:%M:%S BKK')}")
    print(f"{'='*50}")

    team_data = []

    for person in TEAM:
        print(f"\nChecking {person['name']} ({person['email']})...")
        cal = get_calendar_status(person["email"])

        entry = {**person}

        if cal.get("busy"):
            event = cal.get("event", "In a meeting")
            until = cal.get("until", "")
            entry["status"]      = "busy"
            entry["statusText"]  = f"Until {until}" if until else "In a meeting"
            entry["slackStatus"] = f"📅 {event}" + (f" until {until}" if until else "")
            print(f"  → BUSY: {event}" + (f" until {until}" if until else ""))
        elif cal.get("upcoming"):
            entry["status"]      = "available"
            entry["statusText"]  = "Available"
            entry["slackStatus"] = f"⏰ {cal['upcoming']} at {cal.get('at','')}"
            print(f"  → Available (upcoming: {cal['upcoming']} at {cal.get('at','')})")
        elif cal.get("error"):
            # Fall back to available if calendar can't be read
            entry["status"]      = "available"
            entry["statusText"]  = "Available"
            entry["slackStatus"] = ""
            print(f"  → Available (calendar unavailable)")
        else:
            entry["status"]      = "available"
            entry["statusText"]  = "Available"
            entry["slackStatus"] = ""
            print(f"  → Available")

        team_data.append(entry)

    update_html(team_data)
    print(f"\nDone!\n")


if __name__ == "__main__":
    main()
