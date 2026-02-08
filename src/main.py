import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fetch_espn import fetch_espn_scoreboard
from fetch_rankings import fetch_ncaa_d1baseball_top25
from normalize import norm_team_name

MT_TZ = ZoneInfo("America/Denver")


def load_config() -> dict:
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def yyyymmdd(dt: datetime) -> str:
    return dt.strftime("%Y%m%d")


def iso_utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def build_html_shell() -> str:
    # This HTML loads ./data/games_by_day.json and renders client-side,
    # including a persistent Favorite Team selector (localStorage).
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>College Baseball Watchlist</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; max-width: 980px; }
    h1 { margin: 0 0 8px 0; }
    .sub { color: #444; margin-bottom: 18px; }
    .controls { display: flex; gap: 10px; align-items: center; margin: 14px 0 24px 0; flex-wrap: wrap; }
    select { padding: 8px 10px; border-radius: 10px; border: 1px solid #ccc; }
    button { padding: 8px 10px; border-radius: 10px; border: 1px solid #ccc; background: #fff; cursor: pointer; }
    .day { margin: 24px 0 34px 0; }
    h2 { margin: 0 0 12px 0; padding-top: 8px; border-top: 1px solid #eee; }
    .card { border: 1px solid #ddd; border-radius: 12px; padding: 14px 16px; margin: 12px 0; }
    .matchup { font-size: 18px; font-weight: 700; }
    .meta { margin-top: 6px; color: #333; }
    .reason { margin-top: 10px; color: #222; line-height: 1.35; }
    .empty { color: #666; }
    .footer { margin-top: 26px; color: #666; font-size: 12px; }
  </style>
</head>
<body>
  <h1>Top Ranked College Baseball Games (7-Day Lookahead)</h1>
  <div class="sub" id="subline">Loading…</div>

  <div class="controls">
    <label for="favoriteSelect"><strong>Favorite team:</strong></label>
    <select id="favoriteSelect"></select>
    <button id="resetBtn" type="button">Reset to default (UVA)</button>
  </div>

  <div id="content"></div>

  <div class="footer">
    Rankings-driven MVP. Favorite-team bump persists in your browser and only changes v
