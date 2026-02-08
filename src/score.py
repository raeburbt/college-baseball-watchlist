from normalize import team_matches


def rank_points(rank: int | None) -> int:
    if rank is None:
        return 0
    if 1 <= rank <= 25:
        return 26 - rank
    return 0


def score_game(
    away_rank: int | None,
    home_rank: int | None,
    has_broadcast: bool,
    cfg: dict,
    away: str,
    home: str,
) -> int:
    score = rank_points(away_rank) + rank_points(home_rank)

    if away_rank is not None and home_rank is not None:
        score += int(cfg.get("both_ranked_bonus", 12))

        if (away_rank <= 10 and home_rank is not None) or (home_rank <= 10 and away_rank is not None):
            score += int(cfg.get("top10_vs_ranked_bonus", 6))

    if has_broadcast:
        score += int(cfg.get("broadcast_bonus", 2))

    favs = cfg.get("favorite_teams", [])
    bump = int(cfg.get("favorite_team_bump", 0))
    if bump and any(team_matches(away, f) or team_matches(home, f) for f in favs):
        score += bump

    return score


def build_reason(away: str, home: str, away_rank: int | None, home_rank: int | None, watch: str, cfg: dict) -> str:
    if away_rank is not None and home_rank is not None:
        if away_rank <= 10 and home_rank <= 10:
            base = "Top-10 showdown — this is the headline game on the slate."
        else:
            base = "Top-25 matchup — two ranked teams, strong chance this stays meaningful late."
    else:
        ranked_team = away if away_rank is not None else home
        base = f"Ranked team watch — {ranked_team} is ranked, and this one has upset potential."

    if watch:
        base += f" Available on: {watch}."
    return base
