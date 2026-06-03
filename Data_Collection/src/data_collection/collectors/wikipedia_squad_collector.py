# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import time
from typing import Sequence
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup, Tag

from src.data_collection.config.tournaments import TournamentConfig
from src.data_collection.schemas.squads import SquadPlayer, SquadSource, TeamSquad, TournamentSquads

WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "Mozilla/5.0 (compatible; final-bracket-squad-collector/1.0)"

DOB_PATTERN = re.compile(r"\(\s*(\d{4}-\d{2}-\d{2})\s*\)")
POSITION_PATTERN = re.compile(r"^\d+\s*(.+)$")
SQUAD_NUMBER_PATTERN = re.compile(r"^\d+$")

DEFAULT_SQUAD_SOURCES: tuple[SquadSource, ...] = (
    SquadSource("world-cup-2026", "2026_FIFA_World_Cup_squads"),
    SquadSource("world-cup-2022", "2022_FIFA_World_Cup_squads"),
    SquadSource("world-cup-2018", "2018_FIFA_World_Cup_squads"),
    SquadSource("world-cup-2014", "2014_FIFA_World_Cup_squads"),
    SquadSource("world-cup-2010", "2010_FIFA_World_Cup_squads"),
    SquadSource("euro-2024", "UEFA_Euro_2024_squads"),
    SquadSource("euro-2020", "UEFA_Euro_2020_squads"),
    SquadSource("euro-2016", "UEFA_Euro_2016_squads"),
    SquadSource("euro-2012", "UEFA_Euro_2012_squads"),
    SquadSource("copa-america-2024", "2024_Copa_Am\u00e9rica_squads"),
    SquadSource("copa-america-2021", "2021_Copa_Am\u00e9rica_squads"),
    SquadSource("copa-america-2019", "2019_Copa_Am\u00e9rica_squads"),
    SquadSource("copa-america-2016", "Copa_Am\u00e9rica_Centenario_squads"),
)


def _parse_int(value: str) -> int | None:
    clean = value.strip().replace(",", "")
    if not clean or clean in {"\u2014", "-", "\u2013"}:
        return None
    if SQUAD_NUMBER_PATTERN.match(clean):
        return int(clean)
    try:
        return int(clean)
    except ValueError:
        return None


def _wikipedia_title(href: str | None) -> str | None:
    if not href or not href.startswith("/wiki/"):
        return None
    return unquote(href.split("/wiki/", 1)[1])


def _is_generic_football_role_wiki_href(href: str) -> bool:
    if not href.startswith("/wiki/"):
        return False
    slug = unquote(href.split("/wiki/", 1)[1]).split("?", 1)[0]
    lowered = slug.lower()
    if "association_football" in lowered:
        return True
    base = lowered.split("_(", 1)[0].split("/", 1)[0]
    return base in {"goalkeeper", "defender", "midfielder", "forward", "winger"}


def _player_link(cell: Tag) -> tuple[str, str | None]:
    for anchor in cell.find_all("a", href=True):
        href = anchor["href"]
        if not href.startswith("/wiki/"):
            continue
        if _is_generic_football_role_wiki_href(href):
            continue
        name = anchor.get_text(" ", strip=True)
        if name:
            return name, _wikipedia_title(href)
    text = cell.get_text(" ", strip=True)
    return text, None


def _club_link(cell: Tag) -> tuple[str | None, str | None]:
    anchors = [
        anchor
        for anchor in cell.find_all("a", href=True)
        if anchor.get_text(strip=True) and anchor["href"].startswith("/wiki/")
    ]
    if anchors:
        anchor = anchors[-1]
        return anchor.get_text(strip=True), _wikipedia_title(anchor["href"])
    text = cell.get_text(" ", strip=True)
    return (text or None), None


def _parse_position(cell: Tag) -> str | None:
    text = cell.get_text(" ", strip=True)
    match = POSITION_PATTERN.match(text)
    if match:
        return match.group(1).strip() or None
    return text or None


def _parse_date_of_birth(cell: Tag) -> str | None:
    match = DOB_PATTERN.search(cell.get_text(" ", strip=True))
    return match.group(1) if match else None


def _parse_date_of_birth_from_cells(cells: Sequence[Tag]) -> str | None:
    for cell in cells:
        date_of_birth = _parse_date_of_birth(cell)
        if date_of_birth:
            return date_of_birth
    return None


def _parse_player_from_cells(cells: Sequence[Tag]) -> tuple[str, str | None] | None:
    for cell in cells:
        player_name, wiki_title = _player_link(cell)
        if wiki_title and player_name:
            return player_name, wiki_title
    return None


def _is_squad_table(table: Tag) -> bool:
    header_row = table.find("tr")
    if header_row is None:
        return False
    headers = [cell.get_text(" ", strip=True).lower() for cell in header_row.find_all(["th", "td"])]
    return any("player" in header for header in headers)


def _column_index(headers: list[str], *candidates: str) -> int | None:
    lowered = [header.lower() for header in headers]
    for candidate in candidates:
        needle = candidate.lower()
        for index, header in enumerate(lowered):
            if needle in header:
                return index
    return None


def _parse_squad_table(table: Tag) -> list[SquadPlayer]:
    header_row = table.find("tr")
    if header_row is None:
        return []

    headers = [cell.get_text(" ", strip=True) for cell in header_row.find_all(["th", "td"])]
    number_idx = _column_index(headers, "no.")
    position_idx = _column_index(headers, "pos.")
    player_idx = _column_index(headers, "player")
    dob_idx = _column_index(headers, "date of birth")
    caps_idx = _column_index(headers, "caps")
    goals_idx = _column_index(headers, "goals")
    club_idx = _column_index(headers, "club")

    if player_idx is None:
        return []

    players: list[SquadPlayer] = []
    for row in table.find_all("tr")[1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) <= player_idx:
            continue

        player_name, wiki_title = "", None
        if player_idx is not None and player_idx < len(cells):
            player_name, wiki_title = _player_link(cells[player_idx])
        if not player_name:
            found = _parse_player_from_cells(cells)
            if found is not None:
                player_name, wiki_title = found
        if not player_name:
            continue

        squad_number = (
            _parse_int(cells[number_idx].get_text(" ", strip=True))
            if number_idx is not None and number_idx < len(cells)
            else None
        )
        position = (
            _parse_position(cells[position_idx])
            if position_idx is not None and position_idx < len(cells)
            else None
        )
        date_of_birth = (
            _parse_date_of_birth(cells[dob_idx])
            if dob_idx is not None and dob_idx < len(cells)
            else None
        )
        if date_of_birth is None:
            date_of_birth = _parse_date_of_birth_from_cells(cells)
        caps = (
            _parse_int(cells[caps_idx].get_text(" ", strip=True))
            if caps_idx is not None and caps_idx < len(cells)
            else None
        )
        goals = (
            _parse_int(cells[goals_idx].get_text(" ", strip=True))
            if goals_idx is not None and goals_idx < len(cells)
            else None
        )
        club_name, club_wiki = (
            _club_link(cells[club_idx])
            if club_idx is not None and club_idx < len(cells)
            else (None, None)
        )

        players.append(
            SquadPlayer(
                squad_number=squad_number,
                position=position,
                player_name=player_name,
                wikipedia_title=wiki_title,
                date_of_birth=date_of_birth,
                caps=caps,
                goals=goals,
                club_name=club_name,
                club_wikipedia_title=club_wiki,
            )
        )
    return players


def _group_for_heading(heading: Tag) -> str | None:
    heading_id = heading.get("id") or ""
    if heading_id.startswith("Group_"):
        return heading.get_text(" ", strip=True) or None
    return None


def _team_tables(heading: Tag) -> list[Tag]:
    tables: list[Tag] = []
    for element in heading.find_all_next():
        if element.name in {"h2", "h3"}:
            break
        if element.name != "table":
            continue
        classes = element.get("class") or []
        if "wikitable" not in classes:
            continue
        if _is_squad_table(element):
            tables.append(element)
    return tables


def parse_squad_page_html(html: str) -> list[TeamSquad]:
    soup = BeautifulSoup(html, "lxml")
    teams: list[TeamSquad] = []
    current_group: str | None = None

    for heading in soup.find_all(["h2", "h3"]):
        if heading.name == "h2":
            current_group = _group_for_heading(heading)
            continue

        if current_group is None:
            continue

        team_name = heading.get_text(" ", strip=True)
        if not team_name:
            continue

        squad_tables = _team_tables(heading)
        if not squad_tables:
            continue

        players = _parse_squad_table(squad_tables[-1])
        if not players:
            continue

        teams.append(
            TeamSquad(
                team_name=team_name,
                group=current_group,
                players=tuple(players),
            )
        )
    return teams


class WikipediaSquadCollector:
    def __init__(
        self,
        *,
        sources: Sequence[SquadSource] = DEFAULT_SQUAD_SOURCES,
        tournaments: Sequence[TournamentConfig],
        timeout_seconds: int = 30,
        request_delay_seconds: float = 0.35,
        session: requests.Session | None = None,
    ) -> None:
        self.sources = tuple(sources)
        self.tournaments = {tournament.tournament_id: tournament for tournament in tournaments}
        self.timeout_seconds = timeout_seconds
        self.request_delay_seconds = request_delay_seconds
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def fetch_page_html(self, page_title: str) -> str:
        try:
            return self._fetch_page_html_action_api(page_title)
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code in {403, 429}:
                print(
                    f"[TM] Wikipedia action API rate-limited ({exc.response.status_code}) for {page_title}, "
                    "falling back to REST HTML endpoint"
                )
                time.sleep(max(self.request_delay_seconds, 2.0))
                return self._fetch_page_html_rest(page_title)
            raise

    def _get_with_retries(self, url: str, *, params: dict[str, str] | None = None, accept: str) -> requests.Response:
        delays = (0.0, 2.0, 5.0, 10.0, 20.0)
        last_response: requests.Response | None = None
        for delay in delays:
            if delay:
                time.sleep(delay)
            response = self.session.get(
                url,
                params=params,
                headers={"Accept": accept},
                timeout=self.timeout_seconds,
            )
            last_response = response
            if response.status_code not in {429, 503}:
                return response
            print(f"[TM] Wikipedia throttled ({response.status_code}), retrying in {delay or 2.0}s")
        assert last_response is not None
        return last_response

    def _fetch_page_html_action_api(self, page_title: str) -> str:
        response = self._get_with_retries(
            WIKIPEDIA_API_URL,
            params={
                "action": "parse",
                "page": page_title,
                "format": "json",
                "prop": "text",
                "formatversion": "2",
            },
            accept="application/json",
        )
        response.raise_for_status()
        payload = response.json()
        if "error" in payload:
            code = payload["error"].get("code", "unknown")
            info = payload["error"].get("info", "")
            raise RuntimeError(f"Wikipedia API error for {page_title}: {code} - {info}")
        parsed = payload["parse"]
        if "text" in parsed and isinstance(parsed["text"], str):
            return parsed["text"]
        return parsed["text"]["*"]

    def _fetch_page_html_rest(self, page_title: str) -> str:
        response = self._get_with_retries(
            f"https://en.wikipedia.org/api/rest_v1/page/html/{page_title}",
            accept="text/html",
        )
        response.raise_for_status()
        return response.text

    def collect_tournament(self, source: SquadSource) -> TournamentSquads:
        print(f"[TM] Wikipedia fetch tournament={source.tournament_id} page={source.wikipedia_page}")
        tournament = self.tournaments.get(source.tournament_id)
        if tournament is None:
            raise KeyError(f"No tournament config for id={source.tournament_id!r}")

        html = self.fetch_page_html(source.wikipedia_page)
        teams = tuple(parse_squad_page_html(html))
        if not teams:
            raise RuntimeError(f"No squads parsed from Wikipedia page {source.wikipedia_page!r}")
        print(
            f"[TM] Wikipedia parsed tournament={source.tournament_id} teams={len(teams)} "
            f"players={sum(len(team.players) for team in teams)}"
        )

        return TournamentSquads(
            tournament_id=tournament.tournament_id,
            tournament_name=tournament.tournament_name,
            competition=tournament.competition,
            season_year=tournament.season_year,
            wikipedia_page=source.wikipedia_page,
            wikipedia_url=source.wikipedia_url,
            teams=teams,
        )

    def collect(
        self,
        tournament_ids: Sequence[str] | None = None,
    ) -> tuple[TournamentSquads, ...]:
        selected = self._select_sources(tournament_ids)
        print(f"[TM] Wikipedia collector start tournaments={len(selected)}")
        results: list[TournamentSquads] = []
        for index, source in enumerate(selected):
            print(f"[TM] Wikipedia progress {index + 1}/{len(selected)} tournament={source.tournament_id}")
            results.append(self.collect_tournament(source))
            if index + 1 < len(selected) and self.request_delay_seconds > 0:
                time.sleep(self.request_delay_seconds)
        print("[TM] Wikipedia collector done")
        return tuple(results)

    def _select_sources(self, tournament_ids: Sequence[str] | None) -> tuple[SquadSource, ...]:
        if not tournament_ids:
            return self.sources
        wanted = {tid.strip() for tid in tournament_ids if tid.strip()}
        selected = tuple(source for source in self.sources if source.tournament_id in wanted)
        if len(selected) != len(wanted):
            found = {source.tournament_id for source in selected}
            missing = sorted(wanted - found)
            raise ValueError(f"Unknown tournament id(s): {', '.join(missing)}")
        return selected
