import pytest

from app.modules.result_analysis.engine import evaluate


def _lon_offset_for_meters(meters: float) -> float:
    return meters / 111_194.92664455874


def test_reliable_farther_cluster_can_win_over_less_reliable_nearer_cluster() -> None:
    preds = [
        {
            "cluster_id": "low-close",
            "lat": 0.0,
            "lon": _lon_offset_for_meters(5.0),
            "radius_m": 26.0,
            "cluster_type": "dynamic",
            "num_samples": 5,
        },
        {
            "cluster_id": "high-far",
            "lat": 0.0,
            "lon": _lon_offset_for_meters(7.0),
            "radius_m": 0.0,
            "cluster_type": "dynamic",
            "num_samples": 10,
        },
    ]
    gts = [{"gt_id": "gt-1", "lat": 0.0, "lon": 0.0, "label": None}]

    result = evaluate(preds, gts)

    assert result["matches"][0]["primary_cluster_id"] == "high-far"
    assert result["matches"][0]["distance_m"] == pytest.approx(7.0, abs=0.01)
    assert result["matches"][0]["association_cost"] == pytest.approx(7.0, abs=0.01)
    assert result["excluded_low_reliability"] == []


def test_low_reliability_cluster_is_excluded_and_reported() -> None:
    preds = [
        {
            "cluster_id": "weak",
            "lat": 0.0,
            "lon": 0.0,
            "radius_m": 30.0,
            "cluster_type": "dynamic",
            "num_samples": 1,
        }
    ]
    gts = [{"gt_id": "gt-1", "lat": 0.0, "lon": 0.0, "label": None}]

    result = evaluate(preds, gts)

    assert result["matches"] == []
    assert result["false_positives"] == []
    assert result["duplicates"] == []
    assert result["possible_merges"] == []
    assert result["excluded_low_reliability"] == [
        {"cluster_id": "weak", "num_samples": 1, "radius_m": 30.0, "reliability": 0.1}
    ]


def test_radius_metrics_include_excluded_predictions() -> None:
    preds = [
        {
            "cluster_id": "trusted",
            "lat": 0.0,
            "lon": 0.0,
            "radius_m": 0.0,
            "cluster_type": "dynamic",
            "num_samples": 10,
        },
        {
            "cluster_id": "wide",
            "lat": 0.0,
            "lon": _lon_offset_for_meters(20.0),
            "radius_m": 100.0,
            "cluster_type": "dynamic",
            "num_samples": 1,
        },
    ]
    gts = [{"gt_id": "gt-1", "lat": 0.0, "lon": 0.0, "label": None}]

    result = evaluate(preds, gts)

    assert result["matches"][0]["primary_cluster_id"] == "trusted"
    assert result["excluded_low_reliability"][0]["cluster_id"] == "wide"
    assert result["metrics"]["median_radius_m"] == 50.0
    assert result["score"]["radius"] == 0.0


def test_default_behavior_is_unchanged_for_fully_reliable_predictions() -> None:
    preds = [
        {
            "cluster_id": "c1",
            "lat": 0.0,
            "lon": 0.0,
            "radius_m": 0.0,
            "cluster_type": "dynamic",
            "num_samples": 10,
        }
    ]
    gts = [{"gt_id": "gt-1", "lat": 0.0, "lon": 0.0, "label": None}]

    result = evaluate(preds, gts)

    assert result["matches"][0]["primary_cluster_id"] == "c1"
    assert result["matches"][0]["association_cost"] == result["matches"][0]["distance_m"]
    assert result["false_positives"] == []
    assert result["excluded_low_reliability"] == []
    assert result["eval_params"]["min_reliable_samples"] == 10
    assert result["eval_params"]["min_reliability_threshold"] == 0.3
