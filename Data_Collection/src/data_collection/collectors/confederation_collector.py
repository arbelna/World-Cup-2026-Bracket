from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

from src.data_collection.schemas.collection import utc_now_iso
from src.data_collection.utils.matching import normalize_team_name

CONFEDERATION_SLUGS: tuple[tuple[str, str], ...] = (
    ("UEFA", "UEFA"),
    ("CONMEBOL", "CONMEBOL"),
    ("CAF", "CAF"),
    ("AFC", "AFC"),
    ("CONCACAF", "CONCACAF"),
    ("OFC", "OFC"),
)
ELO_TEAM_NAMES_TSV_URL = "https://www.eloratings.net/en.teams.tsv"
ELO_CONFEDERATION_TSV_TEMPLATE = "https://www.eloratings.net/{slug}.tsv"


@dataclass(frozen=True, slots=True)
class ConfederationMap:
    teams: dict[str, str]
    collected_at: str
    sources: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"teams": dict(sorted(self.teams.items())), "collected_at": self.collected_at, "sources": list(self.sources)}

    def lookup(self, team_or_country: str) -> str | None:
        if team_or_country in self.teams:
            return self.teams[team_or_country]
        normalized = normalize_team_name(team_or_country)
        for canonical, confed in self.teams.items():
            if normalize_team_name(canonical) == normalized:
                return confed
        return None


class ConfederationCollector:
    def __init__(self, *, timeout_seconds: int = 30, request_delay_seconds: float = 0.3) -> None:
        self.timeout_seconds = timeout_seconds
        self.request_delay_seconds = request_delay_seconds
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; final-bracket-collector/1.0)"})
        self._code_to_name: dict[str, str] | None = None

    def collect(self) -> ConfederationMap:
        print("[CONFED] Collector start")
        self._ensure_team_maps()
        assert self._code_to_name is not None
        teams: dict[str, str] = {}
        sources: list[str] = []
        for slug, confed in CONFEDERATION_SLUGS:
            url = ELO_CONFEDERATION_TSV_TEMPLATE.format(slug=slug)
            print(f"[CONFED] Fetching confederation={confed} source={url}")
            sources.append(url)
            for line in self._get_tsv_lines(url):
                parts = line.split("\t")
                if len(parts) < 3:
                    continue
                code = parts[2].strip()
                if not code or not code.isalpha() or len(code) > 3:
                    continue
                team_name = self._code_to_name.get(code)
                if team_name:
                    teams[team_name] = confed
            time.sleep(self.request_delay_seconds)
        print(f"[CONFED] Collector done teams={len(teams)}")
        return ConfederationMap(teams=teams, collected_at=utc_now_iso(), sources=tuple(sources + [ELO_TEAM_NAMES_TSV_URL]))

    def _ensure_team_maps(self) -> None:
        if self._code_to_name is not None:
            return
        mapping: dict[str, str] = {}
        for line in self._get_tsv_lines(ELO_TEAM_NAMES_TSV_URL):
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            code = parts[0].strip()
            if "_loc" in code or not code.isalpha() or len(code) > 3:
                continue
            mapping[code] = parts[1].strip()
        self._code_to_name = mapping

    def _get_tsv_lines(self, url: str) -> list[str]:
        response = self.session.get(url, timeout=self.timeout_seconds)
        response.raise_for_status()
        return [line for line in response.content.decode("utf-8").splitlines() if line.strip()]
