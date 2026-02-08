import re

ALIASES = {
    "uva": "virginia",
    "virginia cavaliers": "virginia",
    "miami (fl)": "miami",
    "ole miss": "mississippi"
}


def norm_team_name(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[\.\,\'\"\(\)]", "", s)
    s = re.sub(r"\s+", " ", s)
    return ALIASES.get(s, s)


def team_matches(team_name: str, favorite_name: str) -> bool:
    return norm_team_name(team_name) == norm_team_name(favorite_name)
