"""Project similarity between two snapshots.

Only dimensions where both snapshots have coverage >= 0.60 are used. Adverse
dimensions (technical_debt_risk) are inverted so orientation is consistent,
then weighted normalized distance is computed.
"""

from __future__ import annotations

from typing import Any

from ..analysis.scoring.dimensions import all_dimensions, dimension

MIN_COMPARABLE_COVERAGE = 0.60


def weighted_distance(scores_a: dict[str, dict], scores_b: dict[str, dict]) -> dict[str, Any]:
    usable = []
    excluded = []
    for dim in all_dimensions():
        a = scores_a.get(dim.key)
        b = scores_b.get(dim.key)
        if not a or not b:
            excluded.append(dim.key)
            continue
        if a.get("coverage", 0) < MIN_COMPARABLE_COVERAGE or b.get("coverage", 0) < MIN_COMPARABLE_COVERAGE:
            excluded.append(dim.key)
            continue
        sa = a.get("score")
        sb = b.get("score")
        if sa is None or sb is None:
            excluded.append(dim.key)
            continue
        if dim.direction == "lower_is_better":
            sa = 100 - sa
            sb = 100 - sb
        weight = 1.0
        usable.append({"dimension": dim.key, "a": sa, "b": sb, "weight": weight})

    total_w = sum(u["weight"] for u in usable)
    if not usable or total_w <= 0:
        return {
            "similarity": None,
            "distance": None,
            "used_dimensions": [],
            "excluded_dimensions": excluded,
            "similarity_coverage": 0.0,
            "model_compatible": True,
        }
    distance = sum(u["weight"] * abs(u["a"] - u["b"]) / 100.0 for u in usable) / total_w
    similarity = round(100 * (1 - distance))
    return {
        "similarity": similarity,
        "distance": round(distance, 3),
        "used_dimensions": [u["dimension"] for u in usable],
        "excluded_dimensions": excluded,
        "similarity_coverage": round(total_w / len(all_dimensions()), 3),
        "model_compatible": True,
        "per_dimension": [
            {"dimension": u["dimension"], "a": u["a"], "b": u["b"], "abs_delta": abs(u["a"] - u["b"])}
            for u in usable
        ],
    }


def model_compatible(model_a: str, model_b: str) -> bool:
    return model_a == model_b