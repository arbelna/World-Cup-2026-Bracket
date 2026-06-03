from __future__ import annotations

CONFEDERATION_ORDER: tuple[str, ...] = (
    "UEFA",
    "CONMEBOL",
    "CAF",
    "AFC",
    "CONCACAF",
    "OFC",
)

_CONFEDERATION_TO_INDEX: dict[str, int] = {
    name: idx for idx, name in enumerate(CONFEDERATION_ORDER)
}


def host_flag(value: bool | None) -> float:
    return 1.0 if value is True else 0.0


def host_diff(team_a_host: bool | None, team_b_host: bool | None) -> float:
    return host_flag(team_a_host) - host_flag(team_b_host)


def confederation_index(label: str | None) -> float:
    if label is None:
        return -1.0
    text = str(label).strip()
    if not text:
        return -1.0
    idx = _CONFEDERATION_TO_INDEX.get(text)
    if idx is None:
        return -1.0
    return float(idx)
