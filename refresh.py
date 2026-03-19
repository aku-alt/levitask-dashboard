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

EMOJI_MAP = {
    ":car:": "🚗", ":bus:": "🚌", ":airplane:": "✈️", ":train:": "🚆",
    ":bike:": "🚲", ":walking:": "🚶", ":house:": "🏠", ":house_with_garden:": "🏡",
    ":coffee:": "☕", ":tea:": "🍵", ":lunch:": "🍱", ":fork_and_knife:": "🍴",
    ":headphones:": "🎧", ":computer:": "💻", ":desktop_computer:": "🖥️",
    ":no_entry:": "⛔", ":no_entry_sign:": "🚫", ":red_circle:": "🔴",
    ":calendar:": "📅", ":spiral_calendar_pad:": "🗓️", ":clock1:": "🕐",
    ":rocket:": "🚀", ":dart:": "🎯", ":palm_tree:": "🌴", ":beach_with_umbrella:": "🏖️",
    ":globe_with_meridians:": "🌍", ":earth_asia:": "🌏", ":earth_americas:": "🌎",
    ":thermometer:": "🌡️", ":mask:": "😷", ":face_with_thermometer:": "🤒",
    ":zzz:": "💤", ":sleeping:": "😴", ":phone:": "📞", ":telephone_receiver:": "📞",
    ":pencil:": "✏️", ":pencil2:": "✏️", ":book:": "📖", ":books:": "📚",
    ":tada:": "🎉", ":sparkles:": "✨", ":fire:": "🔥", ":star:": "⭐",
    ":white_check_mark:": "✅", ":x:": "❌", ":warning:": "⚠️",
    ":mega:": "📣", ":loudspeaker:": "📢", ":speech_balloon:": "💬",
    ":construction:": "🚧", ":hammer:": "🔨", ":wrench:": "🔧",
    ":seedling:": "🌱", ":sunny:": "☀️", ":umbrella:": "☂️",
    ":muscle:": "💪", ":raising_hand:": "🙋", ":wave:": "👋",
}

def slack_emoji_to_unicode(code: str) -> str:
    """Convert a Slack :emoji: code to a unicode character, or return the code as-is."""
    return EMOJI_MAP.get(code, code)


def get_slack_status(user_id: str, client) -> dict:
    try:
        resp = client.users_info(user=user_id)
        profile = resp["user"]["profile"]
        status_text  = profile.get("status_text", "").strip()
        status_emoji = profile.get("status_emoji", "").strip()
        photo = (profile.get("image_72") or profile.get("image_48") or "").strip()
        # Convert :emoji: code to unicode for display
        emoji_unicode = slack_emoji_to_unicode(status_emoji) if status_emoji else ""
        slack_status_display = (emoji_unicode + " " + status_text).strip() if status_text else emoji_unicode
        return {"text": status_text, "emoji": status_emoji, "display": slack_status_display, "photo": photo}
    except Exception as e:
        print(f"  Slack error for {user_id}: {e}")
        return {"text": "", "emoji": "", "display": "", "photo": ""}


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

def classify_slack(slack: dict) -> str:
    """Returns status_class: available / busy / away"""
    text  = slack["text"].lower()
    emoji = slack["emoji"]
    raw   = slack["text"]

    if not raw:
        return "available"

    if any(k in text for k in AWAY_KEYWORDS) or emoji in (":car:", ":bus:", ":train:", ":airplane:"):
        return "away"

    if any(k in text for k in BUSY_KEYWORDS) or emoji in (":no_entry:", ":x:", ":red_circle:"):
        return "busy"

    return "available"


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
    body { font-family: "Avenir Next", "Avenir", -apple-system, BlinkMacSystemFont, sans-serif; background: #0b0b0b; color: #e8e6e1; min-height: 100vh; padding: 36px 28px; }

    header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 40px; padding-bottom: 24px; border-bottom: 1px solid #1c1c1c; }
    .brand { display: flex; align-items: center; gap: 16px; }
    .logo { width: 38px; height: 38px; background: #ffffff; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 17px; color: #0b0b0b; }
    h1 { font-size: 20px; font-weight: 600; color: #ffffff; letter-spacing: 0.08em; text-transform: uppercase; }
    h1 span { font-weight: 300; }
    .subtitle { font-size: 11px; color: #5c5a57; margin-top: 3px; letter-spacing: 0.12em; text-transform: uppercase; }
    .meta { text-align: right; font-size: 11px; color: #5c5a57; line-height: 1.8; letter-spacing: 0.04em; }
    .meta .clock { font-size: 15px; font-weight: 500; color: #a8a49e; letter-spacing: 0.06em; }

    .summary { display: flex; gap: 12px; margin-bottom: 32px; }
    .summary-pill { display: flex; align-items: center; gap: 9px; background: #111111; border: 1px solid #1c1c1c; border-radius: 4px; padding: 8px 20px; font-size: 12px; font-weight: 500; letter-spacing: 0.06em; }
    .dot { width: 7px; height: 7px; border-radius: 50%; }
    .dot-available { background: #34d399; box-shadow: 0 0 7px #34d39955; }
    .dot-busy      { background: #ef4444; box-shadow: 0 0 7px #ef444455; }
    .summary-count { font-size: 17px; font-weight: 700; }
    .count-available { color: #34d399; }
    .count-busy      { color: #ef4444; }

    .section-label { font-size: 11px; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; margin-bottom: 14px; margin-top: 32px; }
    .section-label.available { color: #34d399; }
    .section-label.busy      { color: #ef4444; }

    .grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
    @media (max-width: 1200px) { .grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
    @media (max-width: 800px)  { .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    @media (max-width: 500px)  { .grid { grid-template-columns: 1fr; } }

    .card { background: #111111; border: 1px solid #1c1c1c; border-radius: 6px; padding: 18px 20px; display: flex; flex-direction: column; transition: border-color 0.2s, transform 0.15s, box-shadow 0.2s; text-decoration: none; color: inherit; cursor: pointer; }
    .card:hover { border-color: #2a2a2a; transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
    .card.available { border-left: 2px solid #34d399; }
    .card.busy      { border-left: 2px solid #ef4444; }
    .card.away      { border-left: 2px solid #c9a050; }
    .card.imminent  { border-left: 2px solid #f59e0b; }
    .card.imminent .avatar-available { background: #1a1508; color: #f59e0b; }
    .card.imminent .avatar::after    { background: #f59e0b; }
    .card.imminent .status-available { background: #f59e0b; color: #0b0b0b; }

    .card-header { display: flex; align-items: center; gap: 14px; }

    .avatar { width: 56px; height: 56px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 700; flex-shrink: 0; position: relative; }
    .avatar img { width: 100%; height: 100%; object-fit: cover; border-radius: 50%; display: block; }
    .avatar-available { background: #0d2018; color: #34d399; }
    .avatar-busy      { background: #1a0808; color: #ef4444; }
    .avatar-away      { background: #191508; color: #c9a050; }
    .avatar::after { content: ""; position: absolute; bottom: 2px; right: 2px; width: 12px; height: 12px; border-radius: 50%; border: 2px solid #111111; z-index: 1; }
    .available .avatar::after { background: #34d399; }
    .busy      .avatar::after { background: #ef4444; }
    .away      .avatar::after { background: #c9a050; }

    .info { flex: 1; min-width: 0; }
    .name { font-size: 16px; font-weight: 600; color: #e8e6e1; letter-spacing: 0.03em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .status-text { display: inline-block; font-size: 10px; font-weight: 800; margin-top: 6px; padding: 3px 9px; border-radius: 4px; letter-spacing: 0.08em; text-transform: uppercase; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .status-available { background: #34d399; color: #052010; }
    .status-busy      { background: #ef4444; color: #ffffff; }
    .status-away      { background: #c9a050; color: #0b0b0b; }
    .slack-status { display: block; margin-top: 5px; font-size: 11.5px; color: #6a6866; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-family: "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", sans-serif; }

    .events-divider { height: 1px; background: #1c1c1c; margin: 14px 0 10px; }
    .events-list { display: flex; flex-direction: column; gap: 5px; }
    .event-item { display: flex; align-items: center; gap: 8px; padding: 2px 0; }
    .event-dot { width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; background: #2a2a2a; }
    .event-time { flex-shrink: 0; font-variant-numeric: tabular-nums; font-size: 11px; min-width: 86px; }
    .event-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; font-size: 11.5px; }
    .event-item.upcoming .event-dot   { background: #3a3835; }
    .event-item.upcoming .event-time  { color: #8a8680; }
    .event-item.upcoming .event-title { color: #ffffff; font-weight: 600; }
    .event-item.active .event-dot     { background: #34d399; box-shadow: 0 0 5px #34d39966; }
    .event-item.active .event-time    { color: #34d399; font-weight: 600; }
    .event-item.active .event-title   { color: #ffffff; font-weight: 700; }
    .event-item.past .event-dot       { background: #2e2e2c; }
    .event-item.past .event-time      { color: #4a4846; }
    .event-item.past .event-title     { color: #4a4846; font-weight: 400; }
    .no-events { font-size: 10.5px; color: #6a6866; font-weight: 700; margin-top: 12px; letter-spacing: 0.08em; text-transform: uppercase; }

    .hover-bar { display: flex; align-items: center; justify-content: space-between; border-top: 1px solid #1c1c1c; max-height: 0; overflow: hidden; opacity: 0; transition: max-height 0.22s ease, opacity 0.2s ease, padding-top 0.22s ease, margin-top 0.22s ease; }
    .card:hover .hover-bar { max-height: 36px; opacity: 1; padding-top: 11px; margin-top: 13px; }
    .hover-left { display: flex; align-items: center; gap: 10px; }
    .hover-localtime { font-size: 11px; color: #5c5a57; letter-spacing: 0.03em; }
    .hover-badge { font-size: 10.5px; font-weight: 700; padding: 2px 8px; border-radius: 3px; letter-spacing: 0.05em; text-transform: uppercase; }
    .hover-badge.free     { color: #34d399; background: #0d2018; }
    .hover-badge.soon     { color: #f59e0b; background: #1a1508; }
    .hover-badge.meeting  { color: #ef4444; background: #1a0808; }
    .hover-badge.imminent { color: #0b0b0b; background: #f59e0b; font-weight: 800; }
    .hover-actions { display: flex; align-items: center; gap: 10px; }
    .hover-msg { font-size: 11px; font-weight: 600; letter-spacing: 0.06em; color: #3a3835; text-decoration: none; text-transform: uppercase; transition: color 0.15s; }
    .hover-msg:hover { color: #e8e6e1; }
    .hover-schedule { font-size: 10.5px; font-weight: 700; letter-spacing: 0.06em; color: #5c5a57; text-decoration: none; text-transform: uppercase; border: 1px solid #2a2a2a; border-radius: 3px; padding: 2px 8px; transition: border-color 0.15s, color 0.15s, background 0.15s; }
    .hover-schedule:hover { color: #e8e6e1; border-color: #4a4a4a; background: #1a1a1a; }

    footer { margin-top: 48px; text-align: center; font-size: 10px; color: #2a2a28; border-top: 1px solid #1c1c1c; padding-top: 18px; letter-spacing: 0.1em; text-transform: uppercase; }
  </style>
</head>
<body>
<header>
  <div class="brand">
    <div class="logo">L</div>
    <div>
      <h1>LEVITASK <span>TEAM</span></h1>
      <div class="subtitle">Availability Dashboard</div>
    </div>
  </div>
  <div class="meta">
    <div class="clock" id="clock">–</div>
    <div>Last updated: <span id="last-updated">–</span></div>
    <div>Auto-refreshes every 60 s</div>
  </div>
</header>
<div class="summary">
  <div class="summary-pill"><div class="dot dot-available"></div><span class="summary-count count-available" id="count-available">–</span><span>Available</span></div>
  <div class="summary-pill"><div class="dot dot-busy"></div><span class="summary-count count-busy" id="count-busy">–</span><span>Busy / DND</span></div>
</div>
<div class="section-label available">Available</div>
<div class="grid" id="grid-available"></div>
<div class="section-label busy">Busy / Do Not Disturb</div>
<div class="grid" id="grid-busy"></div>
<footer>Levitask HQ &nbsp;·&nbsp; Slack + Google Calendar &nbsp;·&nbsp; Auto-refreshes every minute</footer>
<script>
  const UPDATED_AT = "%%UPDATED_AT%%";
  const TEAM = %%TEAM_DATA%%;

  // ── Time helpers ────────────────────────────────────────────────────────────
  function bkkNow() {
    return new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Bangkok" }));
  }
  function addMins(d, m) { return new Date(d.getTime() + m * 60000); }
  function fmtHHMM(d) { return String(d.getHours()).padStart(2,"0") + ":" + String(d.getMinutes()).padStart(2,"0"); }
  function parseHHMM(str) {
    const now = bkkNow();
    const [h, m] = str.split(":").map(Number);
    const d = new Date(now); d.setHours(h, m, 0, 0); return d;
  }
  function minsUntil(str) { return Math.round((parseHHMM(str) - bkkNow()) / 60000); }
  function localTime(tz) {
    return new Date().toLocaleString("en-GB", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: tz });
  }

  // ── Build card HTML ─────────────────────────────────────────────────────────
  function buildEventsHtml(events) {
    if (!events || events.length === 0) {
      return "<div class=\\"no-events\\">No meetings today</div>";
    }
    const rows = events.map(e => {
      const cls = e.active ? " active" : (e.past ? " past" : " upcoming");
      return "<div class=\\"event-item" + cls + "\\">" +
        "<div class=\\"event-dot\\"></div>" +
        "<span class=\\"event-time\\">" + e.start + "\\u2013" + e.end + "</span>" +
        "<span class=\\"event-title\\">" + e.title + "</span></div>";
    }).join("");
    return "<div class=\\"events-divider\\"></div><div class=\\"events-list\\">" + rows + "</div>";
  }

  function buildCard(p) {
    const eventsJson = JSON.stringify(p.todayEvents).replace(/"/g, "&quot;");
    const slackAttr  = p.slackStatus ? " data-slack-status=\\"" + p.slackStatus.replace(/"/g, "&quot;") + "\\"" : "";
    const photoAttr  = p.photo       ? " data-photo=\\""        + p.photo + "\\"" : "";
    const href = "https://levitaskworkspace.slack.com/messages/" + p.userId;
    return "<a class=\\"card " + p.status + "\\" href=\\"" + href + "\\" target=\\"_blank\\" rel=\\"noopener\\"" +
      " data-timezone=\\"" + (p.timezone || "Asia/Bangkok") + "\\"" +
      " data-userid=\\"" + p.userId + "\\"" +
      " data-events=\\"" + eventsJson + "\\"" +
      slackAttr + photoAttr + ">" +
      "<div class=\\"card-header\\">" +
      "<div class=\\"avatar avatar-" + p.status + "\\">" + p.initials + "</div>" +
      "<div class=\\"info\\"><div class=\\"name\\">" + p.name + "</div>" +
      "<div class=\\"status-text status-" + p.status + "\\">" + p.statusText + "</div></div></div>" +
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
    document.getElementById("last-updated").textContent = d.toLocaleString("en-GB", {
      weekday:"short", day:"numeric", month:"short", year:"numeric",
      hour:"2-digit", minute:"2-digit", hour12:false, timeZone:"Asia/Bangkok"
    });
  }

  function updateClock() {
    document.getElementById("clock").textContent = new Date().toLocaleString("en-GB", {
      weekday:"short", hour:"2-digit", minute:"2-digit", second:"2-digit",
      hour12:false, timeZone:"Asia/Bangkok"
    }) + " BKK";
  }

  // ── Hover bars ──────────────────────────────────────────────────────────────
  function initHoverBars() {
    document.querySelectorAll(".card").forEach(card => {
      const tz     = card.dataset.timezone || "Asia/Bangkok";
      const userId = card.dataset.userid   || "";
      const isBusy = card.classList.contains("busy") || card.classList.contains("away");
      let events = [];
      try { events = JSON.parse(card.dataset.events || "[]"); } catch(e) {}

      const bar   = document.createElement("div");
      bar.className = "hover-bar";
      const left  = document.createElement("div");
      left.className = "hover-left";

      const timeSpan = document.createElement("span");
      timeSpan.className = "hover-localtime";
      timeSpan.textContent = "\\uD83D\\uDD50 " + localTime(tz);
      left.appendChild(timeSpan);

      let badgeText = "", badgeClass = "";
      if (isBusy) {
        const active = events.find(e => e.active);
        if (active) {
          const mins = minsUntil(active.end);
          badgeText  = mins > 0 ? "Free in " + mins + "m" : "Finishing up";
          badgeClass = "meeting";
        }
      } else {
        const next = events.find(e => !e.past && !e.active);
        if (next) {
          const mins = minsUntil(next.start);
          if (mins > 0 && mins <= 60) {
            if (mins <= 15) {
              badgeText  = "In a meeting soon";
              badgeClass = "imminent";
              card.classList.add("imminent");
              const st = card.querySelector(".status-text");
              if (st) st.textContent = "In a meeting soon";
            } else {
              badgeText  = "Meeting in " + mins + "m";
              badgeClass = "soon";
            }
          }
        }
      }

      if (badgeText) {
        const badge = document.createElement("span");
        badge.className = "hover-badge " + badgeClass;
        badge.textContent = badgeText;
        left.appendChild(badge);
      }

      const actions = document.createElement("div");
      actions.className = "hover-actions";

      const nameEl = card.querySelector(".name");
      const personName = nameEl ? nameEl.textContent.trim() : "Meeting";
      const calUrl = "https://calendar.google.com/calendar/render?action=TEMPLATE" +
        "&text=" + encodeURIComponent("Meeting with " + personName) +
        "&add=" + encodeURIComponent("aku@levitask.com");
      const schedule = document.createElement("a");
      schedule.className = "hover-schedule";
      schedule.href = calUrl; schedule.target = "_blank";
      schedule.textContent = "\\uD83D\\uDCC5 Schedule";
      schedule.addEventListener("click", e => e.stopPropagation());
      actions.appendChild(schedule);

      const msg = document.createElement("a");
      msg.className = "hover-msg";
      msg.href = "https://levitaskworkspace.slack.com/messages/" + userId;
      msg.target = "_blank";
      msg.textContent = "\\uD83D\\uDCAC Message";
      msg.addEventListener("click", e => e.stopPropagation());
      actions.appendChild(msg);

      bar.appendChild(left); bar.appendChild(actions);
      card.appendChild(bar);
    });
  }

  // ── Slack status lines ──────────────────────────────────────────────────────
  function initSlackStatus() {
    document.querySelectorAll(".card[data-slack-status]").forEach(card => {
      const raw = card.dataset.slackStatus.trim();
      if (!raw) return;
      const el = document.createElement("div");
      el.className = "slack-status";
      el.textContent = raw;
      const info = card.querySelector(".info");
      if (info) info.appendChild(el);
    });
  }

  // ── Profile photos ──────────────────────────────────────────────────────────
  function initPhotos() {
    document.querySelectorAll(".card[data-photo]").forEach(card => {
      const url = card.dataset.photo;
      if (!url) return;
      const avatar = card.querySelector(".avatar");
      if (!avatar) return;
      const initials = avatar.textContent.trim();
      avatar.textContent = "";
      const img = document.createElement("img");
      img.src = url; img.alt = initials;
      img.onerror = () => { avatar.removeChild(img); avatar.textContent = initials; };
      avatar.appendChild(img);
    });
  }

  render();
  updateClock(); setInterval(updateClock, 1000);
  initHoverBars();
  initSlackStatus();
  initPhotos();
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
            "timezone":    p.get("timezone", "Asia/Bangkok"),
            "status":      p["status"],
            "statusText":  p["statusText"],
            "slackStatus": p.get("slackStatus", ""),
            "photo":       p.get("photo", ""),
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
        entry = {
            **person,
            "status":      "available",
            "statusText":  "Available",
            "slackStatus": "",
            "photo":       "",
            "todayEvents": [],
        }

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
            else:
                n = len(entry["todayEvents"])
                print(f"  Calendar: free ({n} event{'s' if n != 1 else ''} today)")

        # 2. Slack (always fetch for photo + status display)
        if slack_client:
            slack = get_slack_status(person["userId"], slack_client)
            entry["photo"] = slack.get("photo", "")
            if slack["text"]:
                entry["slackStatus"] = slack["display"]
                # Only override availability state if calendar hasn't marked them busy
                if entry["status"] == "available":
                    status_class = classify_slack(slack)
                    entry["status"] = status_class
                    if status_class != "available":
                        entry["statusText"] = slack["display"]
                print(f"  Slack: {entry['status']} — {slack['display']}")
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
