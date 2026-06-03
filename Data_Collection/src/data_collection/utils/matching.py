from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Iterable

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


def find_fixture_match_id(
    fixtures: list[dict[str, object]],
    home_team: str,
    away_team: str,
    date_utc: str | None,
    tournament_id: str | None = None,
    max_day_delta: int = 1,
) -> str | None:
    pair = tuple(sorted([normalize_team_name(home_team), normalize_team_name(away_team)]))
    odd_date: date | None = None
    if date_utc:
        try:
            odd_date = datetime.fromisoformat(str(date_utc).replace("Z", "+00:00")).date()
        except ValueError:
            odd_date = None
    candidates: list[tuple[str, date, int]] = []
    pair_only_candidates: list[tuple[str, date]] = []
    for fx in fixtures:
        if tournament_id and str(fx.get("tournament_id", "")) != tournament_id:
            continue
        fh = normalize_team_name(str(fx.get("home_team", "")))
        fa = normalize_team_name(str(fx.get("away_team", "")))
        if tuple(sorted([fh, fa])) != pair:
            continue
        raw_date = fx.get("date_utc")
        if not raw_date:
            continue
        try:
            fx_date = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00")).date()
        except ValueError:
            continue
        pair_only_candidates.append((str(fx["match_id"]), fx_date))
        delta = 0 if odd_date is None else abs((fx_date - odd_date).days)
        if odd_date is not None and delta > max_day_delta:
            continue
        candidates.append((str(fx["match_id"]), fx_date, delta))
    if not candidates:
        # Keep deterministic fallback for feeds with unreliable placeholder dates.
        if len(pair_only_candidates) == 1:
            return pair_only_candidates[0][0]
        return None
    if len(candidates) == 1:
        return candidates[0][0]
    if odd_date is None:
        return candidates[0][0]
    candidates.sort(key=lambda item: (item[2], item[1]))
    best = candidates[0]
    if len(candidates) >= 2 and candidates[1][2] == best[2] and candidates[1][1] == best[1]:
        return None
    return best[0]


def build_match_key(home_team: str, away_team: str, date_utc: str | None) -> str:
    ordered = sorted([normalize_team_name(home_team), normalize_team_name(away_team)])
    return f"{ordered[0]}__{ordered[1]}__{normalize_date(date_utc)}"


def ensure_unique_match_ids(records: Iterable[dict]) -> None:
    seen: set[str] = set()
    for record in records:
        match_id = str(record.get("match_id", ""))
        if match_id in seen:
            raise ValueError(f"Duplicate match_id detected: {match_id}")
        seen.add(match_id)
