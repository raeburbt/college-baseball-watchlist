import requests
from bs4 import BeautifulSoup
from normalize import norm_team_name

NCAA_D1BASEBALL_TOP25_URL = "https://www.ncaa.com/rankings/baseball/d1/d1baseballcom-top-25"


def fetch_ncaa_d1baseball_top25() -> dict[str, int]:
    resp = requests.get(
        NCAA_D1BASEBALL_TOP25_URL,
        timeout=20,
        headers={"User-Agent": "college-baseball-watchlist/1.0"},
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    rankings: dict[str, int] = {}

    for row in soup.select("table tr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
        if len(cells) < 2:
            continue

        try:
            rank = int(cells[0])
        except Exception:
            continue

        school = cells[1]
        if 1 <= rank <= 25 and school:
            rankings[norm_team_name(school)] = rank

    return rankings
