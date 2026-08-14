from app.modules.result_analysis.engine import evaluate


M_PER_DEG = 111_194.92664455874


def _lon(offset_m: float) -> float:
    return offset_m / M_PER_DEG


def _pred(cluster_id: str, offset_m: float) -> dict:
    return {
        "cluster_id": cluster_id,
        "lat": 0.0,
        "lon": _lon(offset_m),
        "radius_m": 12.0,
        "cluster_type": "dynamic",
        "num_samples": 10,
    }


def _gt(gt_id: str, offset_m: float) -> dict:
    return {"gt_id": gt_id, "lat": 0.0, "lon": _lon(offset_m), "label": gt_id}


def _match_by_gt(result: dict, gt_id: str) -> dict:
    return next(match for match in result["matches"] if match["gt_id"] == gt_id)


def _ambiguous_by_gt(result: dict, gt_id: str) -> dict:
    return next(item for item in result["ambiguous_gts"] if item["gt_id"] == gt_id)


def test_no_ambiguity_fixture_keeps_clear_match_behavior() -> None:
    result = evaluate(
        [_pred("c1", 0.0), _pred("c2", 50.0)],
        [_gt("g1", 1.0), _gt("g2", 51.0)],
    )

    assert [(match["gt_id"], match["primary_cluster_id"], match["association_status"]) for match in result["matches"]] == [
        ("g1", "c1", "clear_match"),
        ("g2", "c2", "clear_match"),
    ]
    assert result["ambiguous_gts"] == []
    assert result["false_positives"] == []
    assert result["metrics"]["recall"] == 1.0
    assert result["metrics"]["precision"] == 1.0


def test_ambiguous_gt_matches_free_candidate_after_stage_one_claims_other_candidate() -> None:
    result = evaluate(
        [_pred("claimed", 0.0), _pred("free", 10.0)],
        [_gt("ambiguous", 5.0), _gt("clear", -2.0)],
    )

    rescued = _match_by_gt(result, "ambiguous")
    clear = _match_by_gt(result, "clear")
    assert rescued["primary_cluster_id"] == "free"
    assert rescued["association_status"] == "resolved_after_narrowing"
    assert clear["primary_cluster_id"] == "claimed"
    assert clear["association_status"] == "clear_match"
    assert result["ambiguous_gts"] == []
    assert result["false_positives"] == []


def test_multi_gt_chain_resolves_shared_leftover_cluster_by_second_assignment() -> None:
    result = evaluate(
        [_pred("x", 0.0), _pred("y", 10.0), _pred("z", -10.0)],
        [
            _gt("ambiguous_a", 5.0),
            _gt("ambiguous_b", -4.8),
            _gt("clear_y", 12.0),
            _gt("clear_z", -12.0),
        ],
    )

    assert _match_by_gt(result, "clear_y")["primary_cluster_id"] == "y"
    assert _match_by_gt(result, "clear_z")["primary_cluster_id"] == "z"
    rescued_matches = [
        match
        for match in result["matches"]
        if match["gt_id"] in {"ambiguous_a", "ambiguous_b"}
    ]
    assert len(rescued_matches) == 1
    assert rescued_matches[0]["gt_id"] == "ambiguous_b"
    assert rescued_matches[0]["primary_cluster_id"] == "x"
    assert rescued_matches[0]["association_status"] == "resolved_after_narrowing"
    assert _ambiguous_by_gt(result, "ambiguous_a")["competing_cluster_ids"] == []


def test_irreducible_ambiguity_with_two_leftover_candidates_stays_ambiguous() -> None:
    result = evaluate(
        [_pred("left", 0.0), _pred("right", 10.0)],
        [_gt("ambiguous", 5.0)],
    )

    assert result["matches"] == []
    ambiguous = _ambiguous_by_gt(result, "ambiguous")
    assert ambiguous["competing_cluster_ids"] == ["left", "right"]
    assert {item["cluster_id"] for item in result["false_positives"]} == {"left", "right"}


def test_still_ambiguous_reporting_uses_narrowed_viable_leftover_candidates() -> None:
    result = evaluate(
        [_pred("claimed_a", 25.0), _pred("claimed_b", 26.0), _pred("too_far", 31.0)],
        [_gt("ambiguous", 0.0), _gt("clear_a", 24.5), _gt("clear_b", 26.5)],
        ratio_gate=1.3,
        max_match_dist_m=30.0,
    )

    assert _match_by_gt(result, "clear_a")["primary_cluster_id"] == "claimed_a"
    assert _match_by_gt(result, "clear_b")["primary_cluster_id"] == "claimed_b"
    ambiguous = _ambiguous_by_gt(result, "ambiguous")
    assert ambiguous["competing_cluster_ids"] == []
    assert [item["cluster_id"] for item in result["false_positives"]] == ["too_far"]
