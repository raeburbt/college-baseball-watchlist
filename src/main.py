import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fetch_espn import fetch_espn_scoreboard
from fetch_rankings import fetch_ncaa_d1baseball_top25
from normalize import norm_team_name
from score import score_game, build_reason
from render import render_html


MT_TZ = ZoneInfo("America/Denver")


def load_config() -> dict:
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def yyyymmdd(dt: datetime) -> str:
    return dt.strftime("%Y%m%d")


def iso_utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def main() -> None:
    cfg = load_config()
    lookahead_days = int(cfg.get("lookahead_days", 7))
    top_n = int(cfg.get("top_n", 3))

    rankings = fetch_ncaa_d1baseball_top25()

    # Group results by local (MT) date string: YYYY-MM-DD
    by_day: dict[str, list[dict]] = {}

    today_mt = datetime.now(MT_TZ).replace(hour=0, minute=0, second=0, microsecond=0)

    for i in range(lookahead_days):
        day_mt = today_mt + timedelta(days=i)
        date_param = yyyymmdd(day_mt)

        events = fetch_espn_scoreboard(date_param)

        scored = []
        for ev in events:
            away = ev["away"]
            home = ev["home"]

            away_rank = rankings.get(norm_team_name(away))
            home_rank = rankings.get(norm_team_name(home))

            # Rankings-driven MVP: only games where at least one team is ranked
            if away_rank is None and home_rank is None:
                continue

            s = score_game(
                away_rank=away_rank,
                home_rank=home_rank,
                has_broadcast=bool(ev["watch"]),
                cfg=cfg,
                away=away,
                home=home,
            )

            reason = build_reason(away, home, away_rank, home_rank, ev["watch"], cfg)

            scored.append({
                "away": away,
                "home": home,
                "away_rank": away_rank,
                "home_rank": home_rank,
                "start_utc": ev["start_utc"],
                "watch": ev["watch"],
                "score": s,
                "reason": reason,
                "event_id": ev["event_id"],
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        top = scored[:top_n]

        day_key = day_mt.strftime("%Y-%m-%d")
        by_day[day_key] = top

    html = render_html(
        by_day=by_day,
        generated_at_utc=iso_utc_now()
    )

    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)

    # Optional debug output
    os.makedirs("docs/data", exist_ok=True)
    with open("docs/data/top_games_by_day.json", "w", encoding="utf-8") as f:
        json.dump(by_day, f, indent=2)


if __name__ == "__main__":
    main()
