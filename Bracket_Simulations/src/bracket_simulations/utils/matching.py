from __future__ import annotations

import re
import unicodedata

ALIASES: dict[str, str] = {
    "usa": "unitedstates",
    "u.s.a.": "unitedstates",
    "us": "unitedstates",
    "southkorea": "korearepublic",
    "korea": "korearepublic",
    "republicofkorea": "korearepublic",
    "iriran": "iran",
    "cotedivoire": "ivorycoast",
    "czechrepublic": "czechia",
    "bosniaherzegovina": "bosniaandherzegovina",
    "trinidadtobago": "trinidadandtobago",
}


def normalize_team_name(name: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-z0-9]+", "", ascii_value.lower())
    return ALIASES.get(clean, clean)


def normalized_team_pair(team_a: str, team_b: str) -> frozenset[str]:
    return frozenset({normalize_team_name(team_a), normalize_team_name(team_b)})
