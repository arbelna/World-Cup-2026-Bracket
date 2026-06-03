from __future__ import annotations

import re
import unicodedata
from datetime import datetime

ALIASES: dict[str, str] = {
    "usa": "unitedstates",
    "u.s.a.": "unitedstates",
    "us": "unitedstates",
    "england": "england",
    "southkorea": "korearepublic",
    "korea": "korearepublic",
    "republicofkorea": "korearepublic",
    "iriran": "iran",
    "cotedivoire": "ivorycoast",
    "czechrepublic": "czechia",
    "bosniaherzegovina": "bosniaandherzegovina",
    "trinidadtobago": "trinidadandtobago",
}


def _normalize_token(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-z0-9]+", "", ascii_value.lower())
    return ALIASES.get(clean, clean)


def normalize_team_name(name: str) -> str:
    return _normalize_token(name.strip())


def normalize_date(date_utc: str | None) -> str:
    if not date_utc:
        return "unknown-date"
    try:
        return datetime.fromisoformat(date_utc.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return date_utc[:10]


def normalized_team_pair(home_team: str, away_team: str) -> tuple[str, str]:
    home = normalize_team_name(home_team)
    away = normalize_team_name(away_team)
    return tuple(sorted([home, away]))
