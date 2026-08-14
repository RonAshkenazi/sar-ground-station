from app.modules.reid.engine import (
    _REID_02_CONFLICT_RESOLUTION,
    _resolve_conflicts,
    _resolve_conflicts_greedy,
)


def test_resolve_conflicts_uses_optimal_assignment_for_stranded_valid_match() -> None:
    associations = [
        ("A", "X", 0.85),
        ("B", "X", 0.90),
        ("B", "Y", 0.86),
    ]

    accepted = _resolve_conflicts(associations)

    assert _REID_02_CONFLICT_RESOLUTION == "optimal_assignment"
    assert set(accepted) == {("A", "X", 0.85), ("B", "Y", 0.86)}
    assert _resolve_conflicts_greedy(associations) == [("B", "X", 0.90)]


def test_resolve_conflicts_preserves_one_to_one_invariant() -> None:
    accepted = _resolve_conflicts(
        [
            ("A", "X", 0.91),
            ("A", "Y", 0.89),
            ("B", "X", 0.88),
            ("C", "Y", 0.93),
            ("C", "Z", 0.87),
        ]
    )

    srcs = [src for src, _dst, _score in accepted]
    dsts = [dst for _src, dst, _score in accepted]

    assert len(srcs) == len(set(srcs))
    assert len(dsts) == len(set(dsts))


def test_resolve_conflicts_matches_greedy_without_genuine_competition() -> None:
    associations = [
        ("A", "B", 0.91),
        ("B", "C", 0.88),
        ("C", "D", 0.86),
    ]

    assert _resolve_conflicts(associations) == _resolve_conflicts_greedy(associations)
