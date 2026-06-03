from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

STAGE_HEADER_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"round\s+of\s+16", re.I), "R16"),
    (re.compile(r"quarter[- ]?finals?", re.I), "QF"),
    (re.compile(r"semi[- ]?finals?", re.I), "SF"),
    (re.compile(r"third[- ]place|match\s+for\s+third\s+place", re.I), "third_place"),
    (re.compile(r"^▪\s*final\s*$", re.I), "final"),
    (re.compile(r"^final\s*$", re.I), "final"),
    (re.compile(r"^group\s+[a-z]\b", re.I), "group"),
    (re.compile(r"^▪\s*group\s+[a-z]\b", re.I), "group"),
    (re.compile(r"group\s+phase", re.I), "group"),
    (re.compile(r"knockout\s+phase", re.I), "R16"),
]

def _month_number(token: str) -> int:
    lowered = token.lower()
    if lowered in MONTHS:
        return MONTHS[lowered]
    short = lowered[:3]
    if short in MONTHS:
        return MONTHS[short]
    raise ValueError(f"Unknown month token: {token}")


DATE_ONLY_RE = re.compile(
    r"^\s*(?:(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+)?([A-Za-z]+)\s+(\d{1,2})\s*$",
    re.I,
)

TIME_PREFIX_RE = re.compile(
    r"^\s*(?:\d{1,2}:\d{2})(?:\s+UTC[+-]\d+)?(?:\s+\([^)]+\))?\s+"
)


@dataclass(slots=True)
class OldStatsMatch:
    tournament_id: str
    date: str
    team1: str
    team2: str
    stage: str
    score_90_team1: int
    score_90_team2: int
    score_et_team1: int | None
    score_et_team2: int | None
    went_to_extra_time: bool
    went_to_penalties: bool
    penalty_winner: str | None
    advancing_team: str | None
    source_file: str
    source_line: int


def tournament_id_from_path(path: Path) -> str:
    folder = path.parent.name
    year_match = re.search(r"(\d{4})--", folder)
    if not year_match:
        raise ValueError(f"Cannot infer tournament year from path: {path}")
    folder_year = int(year_match.group(1))
    path_str = str(path).replace("\\", "/")
    if "/worldcup-master/" in path_str:
        return f"world-cup-{folder_year}"
    if "/euro-master/" in path_str:
        if folder_year == 2021:
            return "euro-2020"
        return f"euro-{folder_year}"
    if "/copa-america-master/" in path_str:
        return f"copa-america-{folder_year}"
    raise ValueError(f"Unknown tournament family for path: {path}")


def season_year_from_tournament_id(tournament_id: str) -> int:
    return int(tournament_id.rsplit("-", 1)[-1])


def _detect_stage(line: str) -> str | None:
    stripped = line.strip()
    for pattern, stage in STAGE_HEADER_PATTERNS:
        if pattern.search(stripped):
            return stage
    return None


def _parse_date_from_line(line: str, default_year: int) -> str | None:
    copa_match = re.search(
        r"(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+)?([A-Za-z]+)/(\d{1,2})",
        line,
        re.I,
    )
    if copa_match:
        month = _month_number(copa_match.group(1))
        day = int(copa_match.group(2))
        return f"{default_year:04d}-{month:02d}-{day:02d}"

    inline_match = re.search(
        r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Za-z]+)\s+(\d{1,2})",
        line,
        re.I,
    )
    if inline_match:
        month = _month_number(inline_match.group(1))
        day = int(inline_match.group(2))
        return f"{default_year:04d}-{month:02d}-{day:02d}"

    date_only = DATE_ONLY_RE.match(line.strip())
    if date_only:
        month = _month_number(date_only.group(2))
        day = int(date_only.group(3))
        return f"{default_year:04d}-{month:02d}-{day:02d}"

    return None


def _strip_date_and_time_prefix(text: str) -> str:
    text = re.sub(
        r"^\s*(?:\(\d+\)\s+)?(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+)?[A-Z][a-z]{2}/\d{1,2}\s+\d{1,2}:\d{2}\s+",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"^\s*[A-Z][a-z]{2}/\d{1,2}\s+\d{1,2}:\d{2}\s+",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"^\s*(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+[A-Z][a-z]{2}\s+\d{1,2}\s+\d{1,2}:\d{2}\s+",
        "",
        text,
        flags=re.I,
    )
    text = TIME_PREFIX_RE.sub("", text)
    return text.strip()


def _first_score_pair(text: str) -> tuple[int, int] | None:
    match = re.search(r"(\d+)\s*-\s*(\d+)", text)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _paren_score_pairs(text: str) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    for match in re.finditer(r"\((\d+)\s*-\s*(\d+)(?:,\s*\d+\s*-\s*\d+)?\)", text):
        pairs.append((int(match.group(1)), int(match.group(2))))
    return pairs


def _pen_score_pair(text: str) -> tuple[int, int] | None:
    match = re.search(r"(\d+)\s*-\s*(\d+)\s*pen\.?", text, re.I)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _strip_leading_score_tokens(text: str) -> str:
    cleaned = text.strip()
    while True:
        updated = cleaned
        updated = re.sub(r"^\d+\s*-\s*\d+\s*", "", updated)
        updated = re.sub(r"^pen\.\s*", "", updated, flags=re.I)
        updated = re.sub(r"^a\.e\.t\.?\s*", "", updated, flags=re.I)
        updated = re.sub(r"^\([^)]*\)\s*", "", updated)
        updated = re.sub(r"^,\s*", "", updated)
        updated = updated.strip()
        if updated == cleaned:
            break
        cleaned = updated
    return cleaned


def _split_teams(score_text: str) -> tuple[str, str, str] | None:
    v_match = re.match(
        r"^(?P<t1>.+?)\s+v\s+(?P<t2>.+?)\s+(?P<rest>\d+\s*-\s*\d+.*)$",
        score_text,
        re.I,
    )
    if v_match:
        return (
            " ".join(v_match.group("t1").split()),
            " ".join(v_match.group("t2").split()),
            v_match.group("rest"),
        )

    first_score = re.search(r"\d+\s*-\s*\d+", score_text)
    if not first_score:
        return None

    team1 = " ".join(score_text[: first_score.start()].split())
    tail = score_text[first_score.start() :]
    team2 = " ".join(_strip_leading_score_tokens(tail).split())
    score_fragment = score_text[first_score.start() : score_text.rfind(team2)].strip()
    if not team1 or not team2:
        return None
    return team1, team2, score_fragment


def parse_score_line(score_text: str, stage: str) -> dict[str, object] | None:
    lowered = score_text.lower()
    has_et = "a.e.t" in lowered
    pen_pair = _pen_score_pair(score_text)
    has_pen = pen_pair is not None
    main_pair = _first_score_pair(score_text)
    if main_pair is None:
        return None

    paren_pairs = _paren_score_pairs(score_text)
    pen_pos = lowered.find("pen")
    et_pos = lowered.find("a.e.t")

    if has_pen and pen_pos != -1 and (et_pos == -1 or pen_pos < et_pos):
        # Pen-first formats (Copa / Euro): TeamA X-Y pen. [A-B a.e.t. (HT)] TeamB
        if has_et:
            after_pen = re.sub(r"^.*?pen\.\s*", "", score_text, count=1, flags=re.I)
            et_pair = _first_score_pair(after_pen)
            score_90 = et_pair if et_pair else (paren_pairs[0] if paren_pairs else (0, 0))
            score_et = score_90
        else:
            score_90 = paren_pairs[0] if paren_pairs else (0, 0)
            score_et = None
        pen_winner_idx = 0 if pen_pair[0] > pen_pair[1] else 1
    elif has_et and has_pen:
        # WC style: TeamA 3-3 a.e.t. (2-2, ...), 4-2 pen. TeamB
        score_90 = paren_pairs[0] if paren_pairs else main_pair
        score_et = main_pair
        pen_winner_idx = 0 if pen_pair[0] > pen_pair[1] else 1
    elif has_et and not has_pen:
        # TeamA 1-2 a.e.t. (1-1) TeamB
        score_90 = paren_pairs[0] if paren_pairs else main_pair
        score_et = main_pair
        pen_winner_idx = None
    else:
        # Regular: TeamA 3-1 (1-1) TeamB
        score_90 = main_pair
        score_et = None
        pen_winner_idx = None

    return {
        "score_90": score_90,
        "score_et": score_et,
        "went_to_extra_time": has_et,
        "went_to_penalties": has_pen,
        "pen_winner_idx": pen_winner_idx,
    }


def _parse_match_line(
    line: str,
    *,
    tournament_id: str,
    default_year: int,
    current_date: str | None,
    current_stage: str,
    source_file: str,
    line_no: int,
) -> tuple[OldStatsMatch | None, str | None]:
    stripped = line.strip()
    if not stripped or "@" not in stripped:
        parsed_date = _parse_date_from_line(stripped, default_year)
        return None, parsed_date or current_date

    before_venue, _venue = stripped.split("@", 1)
    before_venue = _strip_date_and_time_prefix(before_venue.strip())

    inline_date = _parse_date_from_line(stripped, default_year)
    match_date = inline_date or current_date
    if match_date is None:
        return None, current_date

    teams = _split_teams(before_venue)
    if teams is None:
        return None, inline_date or current_date

    team1, team2, score_fragment = teams
    score_info = parse_score_line(score_fragment, current_stage)
    if score_info is None:
        return None, inline_date or current_date

    score_90 = score_info["score_90"]
    score_et = score_info["score_et"]
    went_to_et = bool(score_info["went_to_extra_time"])
    went_to_pen = bool(score_info["went_to_penalties"])
    pen_winner_idx = score_info["pen_winner_idx"]

    penalty_winner: str | None = None
    advancing_team: str | None = None
    if went_to_pen and pen_winner_idx is not None:
        penalty_winner = team1 if pen_winner_idx == 0 else team2
        advancing_team = penalty_winner
    elif current_stage != "group":
        if score_et is not None:
            if score_et[0] > score_et[1]:
                advancing_team = team1
            elif score_et[1] > score_et[0]:
                advancing_team = team2
        elif score_90[0] > score_90[1]:
            advancing_team = team1
        elif score_90[1] > score_90[0]:
            advancing_team = team2

    match = OldStatsMatch(
        tournament_id=tournament_id,
        date=match_date,
        team1=team1,
        team2=team2,
        stage=current_stage,
        score_90_team1=score_90[0],
        score_90_team2=score_90[1],
        score_et_team1=score_et[0] if score_et else None,
        score_et_team2=score_et[1] if score_et else None,
        went_to_extra_time=went_to_et,
        went_to_penalties=went_to_pen,
        penalty_winner=penalty_winner,
        advancing_team=advancing_team,
        source_file=source_file,
        source_line=line_no,
    )
    return match, inline_date or current_date


def parse_old_stats_file(path: Path) -> list[OldStatsMatch]:
    tournament_id = tournament_id_from_path(path)
    default_year = season_year_from_tournament_id(tournament_id)
    if tournament_id == "euro-2020":
        default_year = 2021

    current_stage = "group"
    current_date: str | None = None
    matches: list[OldStatsMatch] = []
    rel_source = str(path).replace("\\", "/")

    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stage = _detect_stage(raw_line)
        if stage is not None:
            current_stage = stage

        date_only = DATE_ONLY_RE.match(raw_line.strip())
        if date_only:
            month = _month_number(date_only.group(2))
            day = int(date_only.group(3))
            current_date = f"{default_year:04d}-{month:02d}-{day:02d}"
            continue

        parsed_date = _parse_date_from_line(raw_line, default_year)
        if parsed_date and "@" not in raw_line:
            current_date = parsed_date
            continue

        match, new_date = _parse_match_line(
            raw_line,
            tournament_id=tournament_id,
            default_year=default_year,
            current_date=current_date,
            current_stage=current_stage,
            source_file=rel_source,
            line_no=line_no,
        )
        if new_date is not None:
            current_date = new_date
        if match is not None:
            matches.append(match)

    return matches


def discover_old_stats_files(old_stats_root: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in (
        "worldcup-master/*/cup.txt",
        "worldcup-master/*/cup_finals.txt",
        "euro-master/*/euro.txt",
        "copa-america-master/*/copa.txt",
    ):
        files.extend(sorted(old_stats_root.glob(pattern)))
    return files


def parse_all_old_stats(old_stats_root: Path) -> list[OldStatsMatch]:
    matches: list[OldStatsMatch] = []
    for path in discover_old_stats_files(old_stats_root):
        matches.extend(parse_old_stats_file(path))
    return matches
