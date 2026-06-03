from __future__ import annotations

from dataclasses import dataclass

from match_model.rows import MatchRow


@dataclass(slots=True)
class LotoFold:
    held_out_competition: str
    train_rows: list[MatchRow]
    test_rows: list[MatchRow]


def leave_one_tournament_out(rows: list[MatchRow]) -> list[LotoFold]:
    competitions = sorted({row.competition for row in rows if not row.is_mirror})
    folds: list[LotoFold] = []
    for held_out in competitions:
        train = [row for row in rows if row.competition != held_out]
        test = [row for row in rows if row.competition == held_out and not row.is_mirror]
        folds.append(
            LotoFold(
                held_out_competition=held_out,
                train_rows=train,
                test_rows=test,
            )
        )
    return folds
