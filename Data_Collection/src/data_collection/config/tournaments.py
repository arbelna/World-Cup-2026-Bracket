from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TournamentConfig:
    tournament_id: str
    tournament_name: str
    competition: str
    season_year: int
    elo_tournament_code: str
    elo_results_url: str
    elo_results_tsv_url: str
    oddsportal_results_url: str
    oddsportal_keywords: tuple[str, ...]
    elo_fixtures_mode: bool = False
    elo_tournament_codes: tuple[str, ...] | None = None
    elo_ratings_tsv_url: str | None = None
    oddsportal_hub: bool = False
    group_stage_only: bool = False


DEFAULT_TOURNAMENTS: tuple[TournamentConfig, ...] = (
    TournamentConfig("euro-2024", "Euro 2024", "Euro", 2024, "EC", "https://www.eloratings.net/2024_European_Championship_results", "https://www.eloratings.net/2024_European_Championship_results.tsv", "https://www.oddsportal.com/football/europe/euro-2024/results/", ("euro 2024",)),
    TournamentConfig("euro-2020", "Euro 2020", "Euro", 2020, "EC", "https://www.eloratings.net/2021_European_Championship_results", "https://www.eloratings.net/2021_European_Championship_results.tsv", "https://www.oddsportal.com/football/europe/euro-2020/results/", ("euro 2020",)),
    TournamentConfig("euro-2016", "Euro 2016", "Euro", 2016, "EC", "https://www.eloratings.net/2016_European_Championship_results", "https://www.eloratings.net/2016_European_Championship_results.tsv", "https://www.oddsportal.com/football/europe/euro-2016/results/", ("euro 2016",)),
    TournamentConfig("euro-2012", "Euro 2012", "Euro", 2012, "EC", "https://www.eloratings.net/2012_European_Championship_results", "https://www.eloratings.net/2012_European_Championship_results.tsv", "https://www.oddsportal.com/football/europe/euro-2012/results/", ("euro 2012",)),
    TournamentConfig("world-cup-2022", "World Cup 2022", "World Cup", 2022, "WC", "https://www.eloratings.net/2022_World_Cup_results", "https://www.eloratings.net/2022_World_Cup_results.tsv", "https://www.oddsportal.com/football/world/world-cup-2022/results/", ("world cup 2022",)),
    TournamentConfig("world-cup-2018", "World Cup 2018", "World Cup", 2018, "WC", "https://www.eloratings.net/2018_World_Cup_results", "https://www.eloratings.net/2018_World_Cup_results.tsv", "https://www.oddsportal.com/football/world/world-cup-2018/results/", ("world cup 2018",)),
    TournamentConfig("world-cup-2014", "World Cup 2014", "World Cup", 2014, "WC", "https://www.eloratings.net/2014_World_Cup_results", "https://www.eloratings.net/2014_World_Cup_results.tsv", "https://www.oddsportal.com/football/world/world-cup-2014/results/", ("world cup 2014",)),
    TournamentConfig("world-cup-2010", "World Cup 2010", "World Cup", 2010, "WC", "https://www.eloratings.net/2010_World_Cup_results", "https://www.eloratings.net/2010_World_Cup_results.tsv", "https://www.oddsportal.com/football/world/world-cup-2010/results/", ("world cup 2010",)),
    TournamentConfig("copa-america-2024", "Copa America 2024", "Copa America", 2024, "CA", "https://www.eloratings.net/2024_Copa_America_results", "https://www.eloratings.net/2024_Copa_America_results.tsv", "https://www.oddsportal.com/football/south-america/copa-america-2024/results/", ("copa america", "2024")),
    TournamentConfig("copa-america-2021", "Copa America 2021", "Copa America", 2021, "CA", "https://www.eloratings.net/2021_Copa_America_results", "https://www.eloratings.net/2021_Copa_America_results.tsv", "https://www.oddsportal.com/football/south-america/copa-america-2021/results/", ("copa america", "2021")),
    TournamentConfig("copa-america-2019", "Copa America 2019", "Copa America", 2019, "CA", "https://www.eloratings.net/2019_Copa_America_results", "https://www.eloratings.net/2019_Copa_America_results.tsv", "https://www.oddsportal.com/football/south-america/copa-america-2019/results/", ("copa america", "2019")),
    TournamentConfig("copa-america-2016", "Copa America 2016", "Copa America", 2016, "CA", "https://www.eloratings.net/2016_Copa_America", "https://www.eloratings.net/2016_Copa_America_results.tsv", "https://www.oddsportal.com/football/south-america/copa-america-2016/results/", ("copa america", "2016")),
    TournamentConfig("world-cup-2026", "World Cup 2026", "World Cup", 2026, "WC", "https://www.eloratings.net/2026_World_Cup", "https://www.eloratings.net/2026_World_Cup_fixtures.tsv", "https://www.oddsportal.com/football/world/world-championship-2026/", ("world cup", "2026"), elo_fixtures_mode=True, elo_tournament_codes=("WC",), elo_ratings_tsv_url="https://www.eloratings.net/2026_World_Cup.tsv", oddsportal_hub=True, group_stage_only=True),
)


def tournaments_for_partition(partition: str) -> tuple[TournamentConfig, ...]:
    if partition == "legacy12":
        return tuple(t for t in DEFAULT_TOURNAMENTS if t.tournament_id != "world-cup-2026")
    if partition == "wc2026":
        return tuple(t for t in DEFAULT_TOURNAMENTS if t.tournament_id == "world-cup-2026")
    raise ValueError(f"Unknown partition: {partition}")
