from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from bracket_simulations.paths import CONFIG_DIR, DATA_INPUT, DATA_OUTPUT, MATCH_DATASET, STAGE_ROOT


@dataclass(slots=True)
class TournamentConfig:
    tournament_id: str
    competition: str
    n_groups: int
    group_labels: list[str]
    advance_per_group: int
    has_r32: bool
    best_third_qualifiers: int
    first_knockout_stage: str
    train_dataset: Path
    exclude_tournament_from_train: str | None
    match_dataset_filter_competition: str
    fixtures_file: Path
    team_ratings_file: Path
    groups_file: Path
    knockout_bracket_file: Path
    r32_scenarios_file: Path | None
    group_pairwise_predictions_file: Path
    knockout_pairwise_predictions_file: Path
    knockout_context_file: Path
    default_batch_size: int
    default_n_sims: int
    alphas: dict[str, float]
    stages_tracked: list[str]
    output_slug: str

    @property
    def output_dir(self) -> Path:
        return DATA_OUTPUT / self.output_slug

    @property
    def pairwise_predictions_file(self) -> Path:
        return self.group_pairwise_predictions_file


def _resolve(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return STAGE_ROOT / path


def load_tournament_config(name: str) -> TournamentConfig:
    path = CONFIG_DIR / f"{name}.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    legacy_pairwise = raw.get("pairwise_predictions_file", "data/input/pairwise_predictions.csv")
    return TournamentConfig(
        tournament_id=str(raw["tournament_id"]),
        competition=str(raw["competition"]),
        n_groups=int(raw["n_groups"]),
        group_labels=[str(x) for x in raw["group_labels"]],
        advance_per_group=int(raw["advance_per_group"]),
        has_r32=bool(raw.get("has_r32", False)),
        best_third_qualifiers=int(raw.get("best_third_qualifiers", 0)),
        first_knockout_stage=str(raw["first_knockout_stage"]),
        train_dataset=_resolve(raw.get("train_dataset", str(MATCH_DATASET.relative_to(STAGE_ROOT)))),
        exclude_tournament_from_train=raw.get("exclude_tournament_from_train"),
        match_dataset_filter_competition=str(raw["match_dataset_filter_competition"]),
        fixtures_file=_resolve(raw.get("fixtures_file", "data/input/fixtures_stats.json")),
        team_ratings_file=_resolve(raw.get("team_ratings_file", "data/input/team_ratings.json")),
        groups_file=_resolve(raw["groups_file"]),
        knockout_bracket_file=_resolve(raw["knockout_bracket_file"]),
        r32_scenarios_file=_resolve(raw["r32_scenarios_file"]) if raw.get("r32_scenarios_file") else None,
        group_pairwise_predictions_file=_resolve(
            raw.get("group_pairwise_predictions_file", legacy_pairwise)
        ),
        knockout_pairwise_predictions_file=_resolve(
            raw.get("knockout_pairwise_predictions_file", legacy_pairwise)
        ),
        knockout_context_file=_resolve(
            raw.get("knockout_context_file", "data/input/knockout_context.json")
        ),
        default_batch_size=int(raw.get("default_batch_size", 1000)),
        default_n_sims=int(raw.get("default_n_sims", 10000)),
        alphas={str(k): float(v) for k, v in (raw.get("alphas") or {}).items()},
        stages_tracked=[str(s) for s in raw.get("stages_tracked", [])],
        output_slug=str(raw.get("output_slug", name)),
    )


def list_tournament_config_names() -> list[str]:
    return sorted(p.stem for p in CONFIG_DIR.glob("wc*.yaml"))


def config_template(slug: str, year: int) -> str:
    return f"""output_slug: {slug}
tournament_id: world-cup-{year}
competition: World Cup {year}
n_groups: 8
group_labels: [A, B, C, D, E, F, G, H]
advance_per_group: 2
has_r32: false
best_third_qualifiers: 0
first_knockout_stage: R16

train_dataset: data/input/match_dataset.json
exclude_tournament_from_train: world-cup-{year}
match_dataset_filter_competition: World Cup {year}

fixtures_file: data/input/fixtures_stats.json
team_ratings_file: data/input/team_ratings.json
groups_file: data/input/{slug}_groups.json
knockout_bracket_file: data/input/{slug}_knockout_bracket.json
group_pairwise_predictions_file: data/input/{slug}_group_pairwise_predictions.csv
knockout_pairwise_predictions_file: data/input/{slug}_knockout_pairwise_predictions.csv
knockout_context_file: data/input/{slug}_knockout_context.json

default_batch_size: 1000
default_n_sims: 100000

alphas:
  group_tie: 1.0
  R16: 0.5
  QF: 0.5
  SF: 0.5
  third_place: 0.5
  final: 0.5

stages_tracked: [R16, QF, SF, final, winner]
"""
