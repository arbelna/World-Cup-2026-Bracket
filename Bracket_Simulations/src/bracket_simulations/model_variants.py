from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bracket_simulations.pairwise.rows import CORE7_FEATURE_NAMES


@dataclass(frozen=True, slots=True)
class ModelVariantSpec:
    variant_id: str
    mode_name: str
    label: str
    feature_names: tuple[str, ...]


ELO_ONLY_FEATURES: tuple[str, ...] = ("elo_diff",)
ELO_PLUS_VALUES_FEATURES: tuple[str, ...] = (
    "elo_diff",
    "z_log_top_15_average_value_team_a",
    "z_log_top_15_average_value_team_b",
)
MINUS_CONFED_FEATURES: tuple[str, ...] = tuple(
    name for name in CORE7_FEATURE_NAMES if "confederation" not in name
)
MINUS_STAGE_FEATURES: tuple[str, ...] = tuple(
    name for name in CORE7_FEATURE_NAMES if name != "stage_binary"
)
MINUS_HOST_FEATURES: tuple[str, ...] = tuple(
    name for name in CORE7_FEATURE_NAMES if name != "host_diff"
)

BASE_VARIANT = ModelVariantSpec(
    variant_id="base",
    mode_name="model_all",
    label="Base core7",
    feature_names=CORE7_FEATURE_NAMES,
)
MODEL_VARIANTS: tuple[ModelVariantSpec, ...] = (
    BASE_VARIANT,
    ModelVariantSpec(
        variant_id="elo_only",
        mode_name="model_elo_only",
        label="Elo only",
        feature_names=ELO_ONLY_FEATURES,
    ),
    ModelVariantSpec(
        variant_id="elo_plus_values",
        mode_name="model_elo_plus_values",
        label="Elo plus values",
        feature_names=ELO_PLUS_VALUES_FEATURES,
    ),
    ModelVariantSpec(
        variant_id="minus_confed",
        mode_name="model_minus_confed",
        label="Remove confederation",
        feature_names=MINUS_CONFED_FEATURES,
    ),
    ModelVariantSpec(
        variant_id="host_off",
        mode_name="model_host_off",
        label="Host off",
        feature_names=MINUS_HOST_FEATURES,
    ),
    ModelVariantSpec(
        variant_id="stage_neutral",
        mode_name="model_stage_neutral",
        label="Stage neutral",
        feature_names=MINUS_STAGE_FEATURES,
    ),
)

MODEL_VARIANT_BY_ID = {spec.variant_id: spec for spec in MODEL_VARIANTS}
MODEL_VARIANT_BY_MODE = {spec.mode_name: spec for spec in MODEL_VARIANTS}


def list_simulation_modes() -> list[str]:
    return ["market_all", *(spec.mode_name for spec in MODEL_VARIANTS)]


def resolve_model_variant(*, variant_id: str | None = None, mode: str | None = None) -> ModelVariantSpec:
    if variant_id is not None:
        if variant_id not in MODEL_VARIANT_BY_ID:
            raise ValueError(f"Unknown model variant: {variant_id}")
        return MODEL_VARIANT_BY_ID[variant_id]
    if mode is not None:
        if mode not in MODEL_VARIANT_BY_MODE:
            raise ValueError(f"Unknown model mode: {mode}")
        return MODEL_VARIANT_BY_MODE[mode]
    raise ValueError("variant_id or mode is required")


def list_model_variant_ids() -> list[str]:
    return [spec.variant_id for spec in MODEL_VARIANTS]


def variant_pairwise_path(base_path: Path, variant_id: str) -> Path:
    if variant_id == "base":
        return base_path
    suffix = base_path.suffix
    stem = base_path.stem
    return base_path.with_name(f"{stem}__{variant_id}{suffix}")
