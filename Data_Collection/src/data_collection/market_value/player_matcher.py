from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

import duckdb

INVALID_PLAYER_NAMES = frozenset({"gk", "df", "mf", "fw", "goalkeeper", "defender", "midfielder", "forward"})


def normalize_player_name(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    lowered = ascii_value.lower().strip()
    lowered = re.sub(r"\s+", " ", lowered)
    lowered = re.sub(r"\b(jr|sr|ii|iii)\b\.?", "", lowered).strip()
    return re.sub(r"[^a-z0-9]+", "", lowered)


def wikipedia_title_to_name(title: str | None) -> str | None:
    if not title:
        return None
    base = title.split("/")[-1]
    base = re.sub(r"_\(.*\)$", "", base)
    base = base.replace("_", " ").strip()
    return base or None


@dataclass(frozen=True, slots=True)
class PlayerRecord:
    player_id: int
    name: str
    first_name: str | None
    last_name: str | None
    date_of_birth: str | None
    normalized_name: str
    normalized_full: str
    normalized_tokens: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MatchResult:
    player_id: int
    matched_name: str
    method: str
    score: float


class TransfermarktPlayerIndex:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        rows = conn.execute(
            """
            SELECT player_id, name, first_name, last_name, CAST(date_of_birth AS DATE) AS date_of_birth
            FROM players
            """
        ).fetchall()
        self.players: list[PlayerRecord] = []
        self.by_name: dict[str, list[PlayerRecord]] = {}
        self.by_name_dob: dict[tuple[str, str], PlayerRecord] = {}
        self.by_last_first: dict[tuple[str, str], list[PlayerRecord]] = {}
        self.by_last_dob: dict[tuple[str, str], list[PlayerRecord]] = {}
        self.by_prefix: dict[str, list[PlayerRecord]] = {}
        self.by_dob: dict[str, list[PlayerRecord]] = {}
        for player_id, name, first_name, last_name, dob in rows:
            dob_str = str(dob) if dob is not None else None
            normalized_name = normalize_player_name(str(name))
            first = str(first_name or "").strip()
            last = str(last_name or "").strip()
            normalized_full = normalize_player_name(f"{first}{last}") or normalized_name
            record = PlayerRecord(
                player_id=int(player_id),
                name=str(name),
                first_name=first or None,
                last_name=last or None,
                date_of_birth=dob_str,
                normalized_name=normalized_name,
                normalized_full=normalized_full,
                normalized_tokens=self._name_tokens(str(name)),
            )
            self.players.append(record)
            self.by_name.setdefault(normalized_name, []).append(record)
            prefix = normalized_name[:3] if len(normalized_name) >= 3 else normalized_name
            self.by_prefix.setdefault(prefix, []).append(record)
            if dob_str:
                self.by_name_dob[(normalized_name, dob_str)] = record
                if normalized_full != normalized_name:
                    self.by_name_dob[(normalized_full, dob_str)] = record
                self.by_dob.setdefault(dob_str, []).append(record)
            if last and first:
                self.by_last_first.setdefault((normalize_player_name(last), normalize_player_name(first)), []).append(record)
            if last and dob_str:
                self.by_last_dob.setdefault((normalize_player_name(last), dob_str), []).append(record)

    def match(
        self,
        player_name: str,
        *,
        date_of_birth: str | None = None,
        wikipedia_title: str | None = None,
    ) -> MatchResult | None:
        if normalize_player_name(player_name) in INVALID_PLAYER_NAMES:
            return None
        candidates: list[tuple[PlayerRecord, str, float]] = []
        for label, name in (
            ("squad_name", player_name),
            ("wikipedia_title", wikipedia_title_to_name(wikipedia_title) or ""),
        ):
            if not name:
                continue
            found = self._match_single_name(name, date_of_birth=date_of_birth)
            if found is not None:
                rec, method, score = found
                candidates.append((rec, f"{label}:{method}", score))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (-item[2], item[0].player_id))
        best = candidates[0]
        return MatchResult(player_id=best[0].player_id, matched_name=best[0].name, method=best[1], score=best[2])

    def _match_single_name(
        self,
        player_name: str,
        *,
        date_of_birth: str | None,
        allow_reverse: bool = True,
    ) -> tuple[PlayerRecord, str, float] | None:
        normalized = normalize_player_name(player_name)
        if not normalized:
            return None
        if date_of_birth:
            exact = self.by_name_dob.get((normalized, date_of_birth))
            if exact is not None:
                return exact, "name_dob_exact", 1.0
        options = self.by_name.get(normalized, [])
        if len(options) == 1:
            return options[0], "name_unique", 0.98
        if date_of_birth and options:
            dob_matches = [p for p in options if p.date_of_birth == date_of_birth]
            if len(dob_matches) == 1:
                return dob_matches[0], "name_dob_unique", 0.97
        tokens = [token for token in re.split(r"\s+", player_name.strip()) if token]
        if len(tokens) >= 2:
            last = normalize_player_name(tokens[-1])
            first = normalize_player_name(tokens[0])
            lf_options = self.by_last_first.get((last, first), [])
            if date_of_birth:
                lf_matches = [p for p in lf_options if p.date_of_birth == date_of_birth]
                if len(lf_matches) == 1:
                    return lf_matches[0], "last_first_dob", 0.96
            if len(lf_options) == 1:
                return lf_options[0], "last_first_unique", 0.95
            if date_of_birth:
                last_dob_options = self.by_last_dob.get((last, date_of_birth), [])
                if len(last_dob_options) == 1:
                    return last_dob_options[0], "last_dob_unique", 0.94
            if allow_reverse:
                reversed_name = " ".join(reversed(tokens))
                reversed_match = self._match_single_name(
                    reversed_name,
                    date_of_birth=date_of_birth,
                    allow_reverse=False,
                )
                if reversed_match is not None:
                    record, method, score = reversed_match
                    return record, f"reversed_{method}", score
        if date_of_birth:
            dob_match = self._match_by_dob_tokens(player_name, date_of_birth)
            if dob_match is not None:
                return dob_match
        if options:
            scored = [(option, SequenceMatcher(None, normalized, option.normalized_name).ratio()) for option in options]
            scored.sort(key=lambda item: item[1], reverse=True)
            best, score = scored[0]
            if score >= 0.92 and (len(scored) == 1 or score - scored[1][1] >= 0.05):
                if date_of_birth and best.date_of_birth and best.date_of_birth != date_of_birth:
                    return None
                return best, "name_fuzzy", score
        fuzzy_pool = self._fuzzy_candidates(normalized)
        if fuzzy_pool:
            best_option, best_score = fuzzy_pool[0]
            if best_score >= 0.94 and (len(fuzzy_pool) == 1 or best_score - fuzzy_pool[1][1] >= 0.03):
                if date_of_birth and best_option.date_of_birth and best_option.date_of_birth != date_of_birth:
                    return None
                return best_option, "prefix_fuzzy", best_score
        return None

    def _fuzzy_candidates(self, normalized: str) -> list[tuple[PlayerRecord, float]]:
        prefix = normalized[:3] if len(normalized) >= 3 else normalized
        pool = self.by_prefix.get(prefix, [])
        scored: list[tuple[PlayerRecord, float]] = []
        for record in pool:
            score = SequenceMatcher(None, normalized, record.normalized_name).ratio()
            if score >= 0.9:
                scored.append((record, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:5]

    @staticmethod
    def _name_tokens(value: str) -> tuple[str, ...]:
        cleaned = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
        tokens = [re.sub(r"[^a-z0-9]+", "", t) for t in re.split(r"\s+", cleaned) if t.strip()]
        return tuple(token for token in tokens if token)

    def _match_by_dob_tokens(self, player_name: str, date_of_birth: str) -> tuple[PlayerRecord, str, float] | None:
        dob_pool = self.by_dob.get(date_of_birth, [])
        if not dob_pool:
            return None
        tokens = self._name_tokens(player_name)
        if not tokens:
            return None
        first = tokens[0]
        last = tokens[-1]
        scored: list[tuple[PlayerRecord, int]] = []
        for record in dob_pool:
            score = 0
            token_set = set(record.normalized_tokens)
            if first and first in token_set:
                score += 2
            if last and last in token_set:
                score += 3
            if first and first in record.normalized_name:
                score += 1
            if last and last in record.normalized_name:
                score += 2
            if score > 0:
                scored.append((record, score))
        if not scored:
            return None
        scored.sort(key=lambda item: item[1], reverse=True)
        best, best_score = scored[0]
        if best_score < 4:
            return None
        if len(scored) > 1 and best_score == scored[1][1]:
            return None
        return best, "dob_token_unique", 0.93


def fetch_pre_tournament_valuations(
    conn: duckdb.DuckDBPyConnection, player_ids: list[int], cutoff_date: str
) -> dict[int, dict[str, Any]]:
    if not player_ids:
        return {}
    rows = conn.execute(
        """
        SELECT player_id, market_value_in_eur, date
        FROM player_valuations
        WHERE player_id IN (SELECT * FROM UNNEST(?::INTEGER[]))
          AND date <= ?::DATE
        QUALIFY ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY date DESC) = 1
        """,
        [player_ids, cutoff_date],
    ).fetchall()
    return {
        int(player_id): {
            "market_value": int(market_value) if market_value is not None else None,
            "valuation_date": str(valuation_date),
        }
        for player_id, market_value, valuation_date in rows
    }
