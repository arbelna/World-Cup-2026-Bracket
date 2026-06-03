from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Sequence
from urllib.parse import quote

import requests

from src.data_collection.config.tournaments import TournamentConfig
from src.data_collection.schemas.collection import FixtureStat, TeamRating, utc_now_iso
from src.data_collection.utils.matching import build_match_key


@dataclass(frozen=True, slots=True)
class ParsedEloMatchRow:
    date_utc: str
    home_code: str
    away_code: str
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None
    tournament_code: str
    elo_rating: dict[str, int | None]
    elo_rating_diff: dict[str, int | None]
    elo_rank: dict[str, int | None]
    elo_rank_diff: dict[str, int | None]
    venue_code: str


class EloCollector:
    ELO_TEAM_NAMES_TSV_URL = "https://www.eloratings.net/en.teams.tsv"
    ELO_TEAM_TSV_URL_TEMPLATE = "https://www.eloratings.net/{slug}.tsv"

    def __init__(
        self,
        tournaments: Sequence[TournamentConfig],
        timeout_seconds: int = 30,
        team_request_delay_seconds: float = 0.5,
    ) -> None:
        self.tournaments = tuple(tournaments)
        self.timeout_seconds = timeout_seconds
        self.team_request_delay_seconds = team_request_delay_seconds
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; final-bracket-collector/1.0)"})
        self._code_to_name: dict[str, str] | None = None
        self._name_to_code: dict[str, str] | None = None

    def collect(self, sanity_check: bool = False) -> tuple[list[TeamRating], list[FixtureStat]]:
        print(f"[ELO] Collector start tournaments={len(self.tournaments)} sanity={sanity_check}")
        self._ensure_team_maps()
        fixtures = self._load_tournament_results(sanity_check=sanity_check)
        team_ratings = self.build_team_ratings(fixtures)
        for tournament in self.tournaments:
            if tournament.elo_ratings_tsv_url:
                snapshot = self._load_ratings_snapshot(tournament, sanity_check=sanity_check)
                if snapshot:
                    team_ratings = self._merge_ratings_snapshot(snapshot, fixtures, tournament.tournament_id)
        print(f"[ELO] Collector done fixtures={len(fixtures)} team_ratings={len(team_ratings)}")
        return team_ratings, fixtures

    def _merge_ratings_snapshot(
        self, snapshot: list[TeamRating], fixtures: Sequence[FixtureStat], tournament_id: str
    ) -> list[TeamRating]:
        first_dates: dict[str, str] = {}
        for fixture in fixtures:
            if fixture.tournament_id != tournament_id:
                continue
            day = _fixture_date(fixture.date_utc).isoformat()
            for team in (fixture.home_team, fixture.away_team):
                if team not in first_dates or day < first_dates[team]:
                    first_dates[team] = day
        merged: list[TeamRating] = []
        for rating in snapshot:
            merged.append(
                TeamRating(
                    tournament_id=rating.tournament_id,
                    team_name=rating.team_name,
                    country_code=rating.country_code,
                    elo_rating=rating.elo_rating,
                    elo_rank=rating.elo_rank,
                    first_match_date=first_dates.get(rating.team_name, rating.first_match_date),
                    source=rating.source,
                    collected_at=rating.collected_at,
                )
            )
        return merged

    def build_team_ratings(self, fixtures: Sequence[FixtureStat]) -> list[TeamRating]:
        self._ensure_team_maps()
        assert self._name_to_code is not None
        by_tournament: dict[str, list[FixtureStat]] = {}
        for fixture in fixtures:
            by_tournament.setdefault(fixture.tournament_id, []).append(fixture)
        ratings: list[TeamRating] = []
        collected_at = utc_now_iso()
        for tournament_id, tournament_fixtures in by_tournament.items():
            tournament = next((t for t in self.tournaments if t.tournament_id == tournament_id), None)
            source = tournament.elo_results_url if tournament else ""
            seen: set[str] = set()
            for fixture in sorted(tournament_fixtures, key=lambda item: _fixture_date(item.date_utc)):
                for team, side in ((fixture.home_team, "home"), (fixture.away_team, "away")):
                    if team in seen:
                        continue
                    seen.add(team)
                    elo_before = _elo_before(fixture.elo_rating.get(side), fixture.elo_rating_diff.get(side))
                    if elo_before is None:
                        continue
                    ratings.append(
                        TeamRating(
                            tournament_id=tournament_id,
                            team_name=team,
                            country_code=self._name_to_code.get(team),
                            elo_rating=elo_before,
                            elo_rank=fixture.elo_rank.get(side),
                            first_match_date=_fixture_date(fixture.date_utc).isoformat(),
                            source=source,
                            collected_at=collected_at,
                        )
                    )
        return ratings

    def _ensure_team_maps(self) -> None:
        if self._code_to_name is not None:
            return
        code_to_name: dict[str, str] = {}
        name_to_code: dict[str, str] = {}
        for line in self._get_tsv_lines(self.ELO_TEAM_NAMES_TSV_URL):
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            code = parts[0].strip()
            if "_loc" in code or not code.isalpha() or len(code) > 3:
                continue
            name = parts[1].strip()
            code_to_name[code] = name
            name_to_code[name] = code
        self._code_to_name = code_to_name
        self._name_to_code = name_to_code

    def _get_tsv_lines(self, url: str) -> list[str]:
        response = self.session.get(url, timeout=self.timeout_seconds)
        response.raise_for_status()
        return [line for line in response.content.decode("utf-8").splitlines() if line.strip()]

    def _load_tournament_results(self, sanity_check: bool) -> list[FixtureStat]:
        self._ensure_team_maps()
        assert self._code_to_name is not None
        collected_at = utc_now_iso()
        fixtures: list[FixtureStat] = []
        for tournament in self.tournaments:
            print(f"[ELO] Fetching tournament={tournament.tournament_id}")
            rows: list[FixtureStat] = []
            for line in self._get_tsv_lines(tournament.elo_results_tsv_url):
                parsed = (
                    self._parse_tournament_fixture_row(line, tournament, self._code_to_name, collected_at)
                    if tournament.elo_fixtures_mode
                    else self._parse_tournament_row(line, tournament, self._code_to_name, collected_at)
                )
                if parsed is not None:
                    rows.append(parsed)
            if tournament.group_stage_only and not sanity_check:
                rows = self._filter_group_stage_fixtures(rows)
            if sanity_check and rows:
                rows = rows[-1:]
            print(f"[ELO] Tournament={tournament.tournament_id} rows={len(rows)}")
            fixtures.extend(rows)
        return fixtures

    def _allowed_tournament_codes(self, tournament: TournamentConfig) -> frozenset[str]:
        return frozenset(tournament.elo_tournament_codes or (tournament.elo_tournament_code,))

    def _filter_group_stage_fixtures(self, fixtures: list[FixtureStat]) -> list[FixtureStat]:
        start_day = date(2026, 6, 11)
        end_day = date(2026, 6, 27)
        return [fx for fx in fixtures if start_day <= _fixture_date(fx.date_utc) <= end_day]

    def _load_ratings_snapshot(self, tournament: TournamentConfig, *, sanity_check: bool) -> list[TeamRating]:
        if not tournament.elo_ratings_tsv_url:
            return []
        self._ensure_team_maps()
        assert self._code_to_name is not None
        ratings: list[TeamRating] = []
        collected_at = utc_now_iso()
        for line in self._get_tsv_lines(tournament.elo_ratings_tsv_url):
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            code = parts[2].strip()
            if not code.isalpha() or len(code) > 3:
                continue
            elo_rating = self._to_int(parts[3])
            if elo_rating is None:
                continue
            ratings.append(
                TeamRating(
                    tournament_id=tournament.tournament_id,
                    team_name=self._code_to_name.get(code, code),
                    country_code=code,
                    elo_rating=elo_rating,
                    elo_rank=self._to_int(parts[0]),
                    first_match_date=None,
                    source=tournament.elo_ratings_tsv_url,
                    collected_at=collected_at,
                )
            )
            if sanity_check:
                break
        print(f"[ELO] Ratings snapshot tournament={tournament.tournament_id} teams={len(ratings)}")
        return ratings

    def _parse_elo_line(self, line: str) -> ParsedEloMatchRow | None:
        parts = line.split("\t")
        if len(parts) < 16:
            return None
        self._ensure_team_maps()
        assert self._code_to_name is not None
        home_code, away_code = parts[3].strip(), parts[4].strip()
        date_utc = self._iso_date(parts[0], parts[1], parts[2])
        if date_utc is None:
            return None
        rating_diff = self._to_int(parts[9])
        return ParsedEloMatchRow(
            date_utc=date_utc,
            home_code=home_code,
            away_code=away_code,
            home_team=self._code_to_name.get(home_code, home_code),
            away_team=self._code_to_name.get(away_code, away_code),
            home_score=self._to_int(parts[5]),
            away_score=self._to_int(parts[6]),
            tournament_code=parts[7].strip(),
            elo_rating={"home": self._to_int(parts[10]), "away": self._to_int(parts[11])},
            elo_rating_diff={"home": rating_diff, "away": -rating_diff if rating_diff is not None else None},
            elo_rank={"home": self._to_int(parts[14]), "away": self._to_int(parts[15])},
            elo_rank_diff={"home": self._to_int(parts[12]), "away": self._to_int(parts[13])},
            venue_code=parts[8].strip(),
        )

    def _parse_elo_fixture_line(self, line: str) -> ParsedEloMatchRow | None:
        parts = line.split("\t")
        if len(parts) < 11:
            return None
        self._ensure_team_maps()
        assert self._code_to_name is not None
        home_code, away_code = parts[3].strip(), parts[4].strip()
        date_utc = self._iso_date(parts[0], parts[1], parts[2])
        if date_utc is None:
            return None
        return ParsedEloMatchRow(
            date_utc=date_utc,
            home_code=home_code,
            away_code=away_code,
            home_team=self._code_to_name.get(home_code, home_code),
            away_team=self._code_to_name.get(away_code, away_code),
            home_score=None,
            away_score=None,
            tournament_code=parts[5].strip(),
            elo_rating={"home": self._to_int(parts[9]), "away": self._to_int(parts[10])},
            elo_rating_diff={"home": 0, "away": 0},
            elo_rank={"home": self._to_int(parts[7]), "away": self._to_int(parts[8])},
            elo_rank_diff={"home": 0, "away": 0},
            venue_code=parts[6].strip(),
        )

    def _parse_tournament_row(
        self, line: str, tournament: TournamentConfig, code_to_name: dict[str, str], collected_at: str
    ) -> FixtureStat | None:
        parsed = self._parse_elo_line(line)
        if parsed is None or parsed.tournament_code not in self._allowed_tournament_codes(tournament):
            return None
        return FixtureStat(
            match_id=f"{tournament.tournament_id}__{build_match_key(parsed.home_team, parsed.away_team, parsed.date_utc)}",
            tournament_id=tournament.tournament_id,
            tournament_name=tournament.tournament_name,
            competition=tournament.competition,
            season_year=tournament.season_year,
            tournament_code=parsed.tournament_code,
            date_utc=parsed.date_utc,
            home_team=parsed.home_team,
            away_team=parsed.away_team,
            home_score=parsed.home_score,
            away_score=parsed.away_score,
            venue=resolve_venue_country(parsed.venue_code, home_team=parsed.home_team, code_to_name=code_to_name),
            elo_rating=parsed.elo_rating,
            elo_rating_diff=parsed.elo_rating_diff,
            elo_rank=parsed.elo_rank,
            elo_rank_diff=parsed.elo_rank_diff,
            source=tournament.elo_results_url,
            collected_at=collected_at,
        )

    def _parse_tournament_fixture_row(
        self, line: str, tournament: TournamentConfig, code_to_name: dict[str, str], collected_at: str
    ) -> FixtureStat | None:
        parsed = self._parse_elo_fixture_line(line)
        if parsed is None or parsed.tournament_code not in self._allowed_tournament_codes(tournament):
            return None
        return FixtureStat(
            match_id=f"{tournament.tournament_id}__{build_match_key(parsed.home_team, parsed.away_team, parsed.date_utc)}",
            tournament_id=tournament.tournament_id,
            tournament_name=tournament.tournament_name,
            competition=tournament.competition,
            season_year=tournament.season_year,
            tournament_code=parsed.tournament_code,
            date_utc=parsed.date_utc,
            home_team=parsed.home_team,
            away_team=parsed.away_team,
            home_score=parsed.home_score,
            away_score=parsed.away_score,
            venue=resolve_venue_country(parsed.venue_code, home_team=parsed.home_team, code_to_name=code_to_name),
            elo_rating=parsed.elo_rating,
            elo_rating_diff=parsed.elo_rating_diff,
            elo_rank=parsed.elo_rank,
            elo_rank_diff=parsed.elo_rank_diff,
            source=tournament.elo_results_url,
            collected_at=collected_at,
        )

    def _iso_date(self, year: str, month: str, day: str) -> str | None:
        try:
            return datetime(int(year), int(month), int(day), tzinfo=timezone.utc).isoformat()
        except ValueError:
            return None

    def _to_int(self, value: str) -> int | None:
        cleaned = re.sub(r"[^\d-]", "", value.strip().replace("\u2212", "-").replace("+", ""))
        if cleaned in {"", "-"}:
            return None
        try:
            return int(cleaned)
        except ValueError:
            return None


def _elo_before(elo_after: int | None, diff: int | None) -> int | None:
    if elo_after is None or diff is None:
        return None
    return elo_after - diff


def resolve_venue_country(
    venue_code: str, *, home_team: str, code_to_name: dict[str, str]
) -> str | None:
    code = venue_code.strip()
    if code:
        return code_to_name.get(code, code)
    return home_team or None


def _fixture_date(date_utc: str | None) -> date:
    if not date_utc:
        return date.min
    return datetime.fromisoformat(date_utc.replace("Z", "+00:00")).date()
