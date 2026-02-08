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


def main() -> None:
    cfg = load_config()
    lookahead_days = int(cfg.get("lookahead_days", 7))

    rankings = fetch_ncaa_d1baseball_top25()
    by_day: dict[str, list[dict]] = {}

    today_mt = datetime.now(MT_TZ).replace(hour=0, minute=0, second=0, microsecond=0)

    for i in range(lookahead_days):
        day_mt = today_mt + timedelta(days=i)
        date_param = yyyymmdd(day_mt)
        day_key = day_mt.strftime("%Y-%m-%d")

        events = fetch_espn_scoreboard(date_param)

        eligible = []
        for ev in events:
            away = ev["away"]
            home = ev["home"]

            away_rank = rankings.get(norm_team_name(away))
            home_rank = rankings.get(norm_team_name(home))

            # Rankings-driven eligibility: at least one ranked team
            if away_rank is None and home_rank is None:
                continue

            eligible.append({
                "away": away,
                "home": home,
                "away_rank": away_rank,
                "home_rank": home_rank,
                "start_utc": ev["start_utc"],
                "watch": ev["watch"],
                "event_id": ev["event_id"],
            })

        by_day[day_key] = eligible

    payload = {
        "generated_at_utc": iso_utc_now(),
        "config": {
            "default_favorite_team": cfg.get("default_favorite_team", "Virginia"),
            "favorite_team_bump": int(cfg.get("favorite_team_bump", 4)),
            "both_ranked_bonus": int(cfg.get("both_ranked_bonus", 12)),
            "top10_vs_ranked_bonus": int(cfg.get("top10_vs_ranked_bonus", 6)),
            "broadcast_bonus": int(cfg.get("broadcast_bonus", 2)),
            "top_n": int(cfg.get("top_n", 3)),
        },
        "by_day": by_day,
    }

    os.makedirs("docs/data", exist_ok=True)
    with open("docs/data/games_by_day.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    # Render a simple HTML shell that loads + renders client-side
    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(build_html_shell())


def build_html_shell() -> str:
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
    .controls { display: flex; gap: 10px; align-items: center; margin: 14px 0 24px 0; }
    select { padding: 8px 10px; border-radius: 10px; border: 1px solid #ccc; }
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
    <button id="resetBtn" type="button">Reset to default</button>
  </div>

  <div id="content"></div>

  <div class="footer">
    Rankings-driven MVP. Favorite-team bump is applied client-side and persists in your browser.
  </div>

<script>
const DATA_URL = "./data/games_by_day.json";
const STORAGE_KEY = "cbw_favorite_team";

function normTeamName(name) {
  return (name || "")
    .trim()
    .toLowerCase()
    .replace(/[\\.,'"()]/g, "")
    .replace(/\\s+/g, " ");
}

function rankPoints(rank) {
  if (rank === null || rank === undefined) return 0;
  if (rank >= 1 && rank <= 25) return 26 - rank;
  return 0;
}

function hasTeam(game, favorite) {
  const fav = normTeamName(favorite);
  return normTeamName(game.away) === fav || normTeamName(game.home) === fav;
}

function scoreGame(game, cfg, favorite) {
  let s = rankPoints(game.away_rank) + rankPoints(game.home_rank);

  const awayRanked = game.away_rank !== null && game.away_rank !== undefined;
  const homeRanked = game.home_rank !== null && game.home_rank !== undefined;

  if (awayRanked && homeRanked) {
    s += cfg.both_ranked_bonus;

    const top10vsRanked =
      (game.away_rank <= 10 && homeRanked) || (game.home_rank <= 10 && awayRanked);
    if (top10vsRanked) s += cfg.top10_vs_ranked_bonus;
  }

  if (game.watch && game.watch.length > 0) s += cfg.broadcast_bonus;

  if (favorite && hasTeam(game, favorite)) s += cfg.favorite_team_bump;

  return s;
}

function buildReason(game) {
  const awayRanked = game.away_rank != null;
  const homeRanked = game.home_rank != null;

  let base = "";
  if (awayRanked && homeRanked) {
    if (game.away_rank <= 10 && game.home_rank <= 10) base = "Top-10 showdown — this is the headline game on the slate.";
    else base = "Top-25 matchup — two ranked teams, strong chance this stays meaningful late.";
  } else {
    const rankedTeam = awayRanked ? game.away : game.home;
    base = `Ranked team watch — ${rankedTeam} is ranked, and this one has upset potential.`;
  }

  if (game.watch) base += ` Available on: ${game.watch}.`;
  return base;
}

function fmtTimeMT(startIso) {
  // Convert ISO string -> display in America/Denver
  const dt = new Date(startIso);
  // Use Intl for timezone formatting
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Denver",
    hour: "numeric",
    minute: "2-digit"
  }).format(dt) + " MT";
}

function showTeam(name, rank) {
  return (rank != null) ? `#${rank} ${name}` : name;
}

function uniqueTeamsFromData(byDay) {
  const set = new Set();
  Object.values(byDay).forEach(games => {
    games.forEach(g => {
      set.add(g.away);
      set.add(g.home);
    });
  });
  return Array.from(set).sort((a,b) => a.localeCompare(b));
}

function populateSelector(selectEl, teams, defaultTeam) {
  selectEl.innerHTML = "";
  // Put default team at top (if present), then the rest.
  const normDefault = normTeamName(defaultTeam);
  const ordered = [];
  if (teams.some(t => normTeamName(t) === normDefault)) ordered.push(defaultTeam);
  teams.forEach(t => {
    if (normTeamName(t) !== normDefault) ordered.push(t);
  });

  ordered.forEach(t => {
    const opt = document.createElement("option");
    opt.value = t;
    opt.textContent = t;
    selectEl.appendChild(opt);
  });
}

function render(byDay, cfg, favorite) {
  const content = document.getElementById("content");
  content.innerHTML = "";

  const days = Object.keys(byDay).sort();
  days.forEach(day => {
    const games = byDay[day] || [];
    if (games.length === 0) {
      const sec = document.createElement("section");
      sec.className = "day";
      sec.innerHTML = `<h2>${day}</h2><div class="empty">No ranked games found.</div>`;
      content.appendChild(sec);
      return;
    }

    // Score all eligible games, pick top N
    const scored = games.map(g => ({...g, _score: scoreGame(g, cfg, favorite)}));
    scored.sort((a,b) => b._score - a._score);
    const top = scored.slice(0, cfg.top_n);

    const sec = document.createElement("section");
    sec.className = "day";
    sec.innerHTML = `<h2>${day}</h2>`;

    top.forEach(g => {
      const card = document.createElement("div");
      card.className = "card";
      const matchup = `${showTeam(g.away, g.away_rank)} @ ${showTeam(g.home, g.home_rank)}`;
      const time = fmtTimeMT(g.start_utc);
      const reason = buildReason(g);

      card.innerHTML = `
        <div class="matchup">${matchup}</div>
        <div class="meta">${time}</div>
        <div class="reason">${reason}</div>
      `;
      sec.appendChild(card);
    });

    content.appendChild(sec);
  });
}

async function init() {
  const res = await fetch(DATA_URL, { cache: "no-store" });
  const payload = await res.json();

  const cfg = payload.config;
  const byDay = payload.by_day;
  const generated = payload.generated_at_utc;

  const defaultFav = payload.config.default_favorite_team || "Virginia";
  const savedFav = localStorage.getItem(STORAGE_KEY);
  const favorite = savedFav || defaultFav;

  document.getElementById("subline").textContent =
    `Generated ${generated} • Times shown in Mountain Time • Favorite bump enabled`;

  const teams = uniqueTeamsFromData(byDay);
  const select = document.getElementById("favoriteSelect");
  populateSelector(select, teams, defaultFav);

  // If the exact saved favorite isn't in the list, fall back to default.
  const inList = teams.some(t => normTeamName(t) === normTeamName(favorite));
  select.value = inList ? favorite : defaultFav;
  if (!inList) localStorage.setItem(STORAGE_KEY, defaultFav);

  select.addEventListener("change", () => {
    const newFav = select.value;
    localStorage.setItem(STORAGE_KEY, newFav);
    render(byDay, cfg, newFav);
  });

  document.getElementById("resetBtn").addEventListener("click", () => {
    localStorage.setItem(STORAGE_KEY, defaultFav);
    select.value = defaultFav;
    render(byDay, cfg, defaultFav);
  });

  render(byDay, cfg, select.value);
}

init().catch(err => {
  document.getElementById("subline").textContent = "Error loading data.";
  document.getElementById("content").innerHTML = `<pre>${String(err)}</pre>`;
});
</script>
</body>
</html>
"""
