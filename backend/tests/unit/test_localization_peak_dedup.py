from app.modules.localization.engine import (
    _deduplicate_peaks,
    _find_peaks,
    _merge_regions,
    _uncertainty_region,
)


def _grid_cells(shape: tuple[int, int], spacing_m: float = 10.0) -> list[tuple[float, float]]:
    n_lat, n_lon = shape
    step_deg = spacing_m / 111_111
    return [(i * step_deg, j * step_deg) for i in range(n_lat) for j in range(n_lon)]


def _candidates(indices: list[int], cells: list[tuple[float, float]], posterior: list[float]) -> list[dict[str, float]]:
    return [{"lat": cells[index][0], "lon": cells[index][1], "value": posterior[index]} for index in indices]


def test_same_component_candidate_peaks_collapse_to_strongest_without_merge_inflation() -> None:
    shape = (3, 5)
    cells = _grid_cells(shape)
    posterior = [
        0.10,
        0.10,
        0.10,
        0.10,
        0.10,
        0.70,
        1.00,
        0.86,
        0.96,
        0.70,
        0.10,
        0.10,
        0.10,
        0.10,
        0.10,
    ]
    peak_indices = _find_peaks(posterior, shape, confidence_cutoff=0.75)

    deduped = _deduplicate_peaks(_candidates(peak_indices, cells, posterior), cells, posterior, 0.80, shape)
    raw_regions = _merge_regions(
        [
            _uncertainty_region(peak, cells, posterior, 1.0, 0.80, 1.5, shape)
            for peak in _candidates(peak_indices, cells, posterior)
        ]
    )
    deduped_regions = _merge_regions(
        [
            _uncertainty_region(peak, cells, posterior, 1.0, 0.80, 1.5, shape)
            for peak in deduped
        ]
    )

    assert [posterior[index] for index in peak_indices] == [1.0, 0.96]
    assert len(deduped) == 1
    assert deduped[0]["value"] == 1.0
    assert len(deduped_regions) == 1
    assert raw_regions[0]["radius_m"] > deduped_regions[0]["radius_m"]


def test_disjoint_candidate_peaks_are_kept_and_still_merge_when_regions_overlap() -> None:
    shape = (3, 5)
    cells = _grid_cells(shape, spacing_m=8.0)
    posterior = [
        0.10,
        0.10,
        0.10,
        0.10,
        0.10,
        0.20,
        1.00,
        0.20,
        0.95,
        0.20,
        0.10,
        0.10,
        0.10,
        0.10,
        0.10,
    ]
    peak_indices = _find_peaks(posterior, shape, confidence_cutoff=0.75)

    deduped = _deduplicate_peaks(_candidates(peak_indices, cells, posterior), cells, posterior, 0.80, shape)
    regions = _merge_regions(
        [
            _uncertainty_region(peak, cells, posterior, 10.0, 0.80, 1.5, shape)
            for peak in deduped
        ]
    )

    assert [peak["value"] for peak in deduped] == [1.0, 0.95]
    assert len(regions) == 1
    assert regions[0]["radius_m"] > 10.0


def test_peak_cap_applies_after_deduplication_keeps_three_strongest_distinct_peaks() -> None:
    shape = (3, 9)
    cells = _grid_cells(shape)
    posterior = [
        0.10,
        0.10,
        0.10,
        0.10,
        0.10,
        0.10,
        0.10,
        0.10,
        0.10,
        0.20,
        1.00,
        0.20,
        0.95,
        0.20,
        0.90,
        0.20,
        0.85,
        0.20,
        0.10,
        0.10,
        0.10,
        0.10,
        0.10,
        0.10,
        0.10,
        0.10,
        0.10,
    ]
    peak_indices = _find_peaks(posterior, shape, confidence_cutoff=0.75)

    deduped = _deduplicate_peaks(_candidates(peak_indices, cells, posterior), cells, posterior, 0.80, shape)
    retained = deduped[:3]

    assert [peak["value"] for peak in deduped] == [1.0, 0.95, 0.90, 0.85]
    assert [peak["value"] for peak in retained] == [1.0, 0.95, 0.90]
