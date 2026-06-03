from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.data_collection.schemas.collection import utc_now_iso


@dataclass(frozen=True, slots=True)
class SquadSource:
    tournament_id: str
    wikipedia_page: str

    @property
    def wikipedia_url(self) -> str:
        return f"https://en.wikipedia.org/wiki/{self.wikipedia_page}"


@dataclass(frozen=True, slots=True)
class SquadPlayer:
    squad_number: int | None
    position: str | None
    player_name: str
    wikipedia_title: str | None
    date_of_birth: str | None
    caps: int | None
    goals: int | None
    club_name: str | None
    club_wikipedia_title: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TeamSquad:
    team_name: str
    group: str | None
    players: tuple[SquadPlayer, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "team_name": self.team_name,
            "group": self.group,
            "players": [player.to_dict() for player in self.players],
        }


@dataclass(frozen=True, slots=True)
class TournamentSquads:
    tournament_id: str
    tournament_name: str
    competition: str
    season_year: int
    wikipedia_page: str
    wikipedia_url: str
    teams: tuple[TeamSquad, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "tournament_id": self.tournament_id,
            "tournament_name": self.tournament_name,
            "competition": self.competition,
            "season_year": self.season_year,
            "wikipedia_page": self.wikipedia_page,
            "wikipedia_url": self.wikipedia_url,
            "team_count": len(self.teams),
            "player_count": sum(len(team.players) for team in self.teams),
            "teams": [team.to_dict() for team in self.teams],
        }


@dataclass(frozen=True, slots=True)
class SquadCollectionResult:
    collected_at: str
    source: str
    tournaments: tuple[TournamentSquads, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "collected_at": self.collected_at,
            "source": self.source,
            "tournament_count": len(self.tournaments),
            "team_count": sum(len(tournament.teams) for tournament in self.tournaments),
            "player_count": sum(
                len(team.players) for tournament in self.tournaments for team in tournament.teams
            ),
            "tournaments": [tournament.to_dict() for tournament in self.tournaments],
        }


def new_squad_collection_result(
    tournaments: tuple[TournamentSquads, ...],
    *,
    source: str = "wikipedia",
) -> SquadCollectionResult:
    return SquadCollectionResult(collected_at=utc_now_iso(), source=source, tournaments=tournaments)
