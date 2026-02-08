import requests

SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/baseball/college-baseball/scoreboard"


def fetch_espn_scoreboard(datestr_yyyymmdd: str) -> list[dict]:
    resp = requests.get(
        SCOREBOARD_URL,
        params={"dates": datestr_yyyymmdd},
        timeout=20,
        headers={"User-Agent": "college-baseball-watchlist/1.0"},
    )
    resp.raise_for_status()
    data = resp.json()

    events = []

    for ev in data.get("events", []):
        competitions = ev.get("competitions", [])
        if not competitions:
            continue

        comp = competitions[0]
        competitors = comp.get("competitors", [])
        if len(competitors) < 2:
            continue

        home_team = None
        away_team = None

        for c in competitors:
            team_obj = c.get("team", {}) or {}

            # Use shortDisplayName first (clean school name)
            team = team_obj.get("shortDisplayName") or team_obj.get("displayName")

            if not team:
                continue

            if c.get("homeAway") == "home":
                home_team = team
            elif c.get("homeAway") == "away":
                away_team = team

        if not home_team or not away_team:
            continue

        start = comp.get("date") or ev.get("date")
