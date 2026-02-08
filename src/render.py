from datetime import datetime
from zoneinfo import ZoneInfo

MT_TZ = ZoneInfo("America/Denver")


def fmt_time_mt(start_iso: str) -> str:
    s = start_iso.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    mt = dt.astimezone(MT_TZ)
    return mt.strftime("%-I:%M %p MT")


def render_html(by_day: dict[str, list[dict]], generated_at_utc: str) -> str:
    sections = []
    for day, games in by_day.items():
        if not games:
            sections.append(f"""
              <section class="day">
                <h2>{day}</h2>
                <div class="empty">No ranked games found (or rankings didn&apos;t match).</div>
              </section>
            """)
            continue

        cards = []
        for g in games:
            away = g["away"]
            home = g["home"]
            away_rank = g["away_rank"]
            home_rank = g["home_rank"]

            def show_team(name: str, rank: int | None) -> str:
                return f"#{rank} {name}" if rank is not None else name

            matchup = f'{show_team(away, away_rank)} @ {show_team(home, home_rank)}'
            time_mt = fmt_time_mt(g["start_utc"])
            reason = g["reason"]

            cards.append(f"""
              <div class="card">
                <div class="matchup">{matchup}</div>
                <div class="meta">{time_mt}</div>
                <div class="reason">{reason}</div>
              </div>
            """)

        sections.append(f"""
          <section class="day">
            <h2>{day}</h2>
            {''.join(cards)}
          </section>
        """)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>College Baseball Watchlist</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; max-width: 980px; }}
    h1 {{ margin: 0 0 8px 0; }}
    .sub {{ color: #444; margin-bottom: 18px; }}
    .day {{ margin: 24px 0 34px 0; }}
    h2 {{ margin: 0 0 12px 0; padding-top: 8px; border-top: 1px solid #eee; }}
    .card {{ border: 1px solid #ddd; border-radius: 12px; padding: 14px 16px; margin: 12px 0; }}
    .matchup {{ font-size: 18px; font-weight: 700; }}
    .meta {{ margin-top: 6px; color: #333; }}
    .reason {{ margin-top: 10px; color: #222; line-height: 1.35; }}
    .empty {{ color: #666; }}
    .footer {{ margin-top: 26px; color: #666; font-size: 12px; }}
  </style>
</head>
<body>
  <h1>Top Ranked College Baseball Games (7-Day Lookahead)</h1>
  <div class="sub">Generated {generated_at_utc} • Times shown in Mountain Time</div>
  {''.join(sections)}
  <div class="footer">
    Rankings-driven MVP. Favorite-team bump enabled. Only games with at least one ranked team are eligible.
  </div>
</body>
</html>
"""
