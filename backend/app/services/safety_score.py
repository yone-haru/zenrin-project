"""ルート単位の安全スコア算出（決定的・API契約 v3固定式）。

penalty = Σ hazard_points: {2:3, 3:6, 4:10, 5:15}[risk_score]
        + Σ danger_reports: {1:1, 2:2, 3:4, 4:6, 5:8}[report.risk_score or 2]
penalty_per_km = penalty * 1000 / max(distance_m, 500)
safety_score = max(0, 100 - round(penalty_per_km))
grade: A>=85, B>=70, C>=55, D>=40, E<40
"""

from __future__ import annotations

from app.models.route import HazardPoint, RouteDangerReport

_HAZARD_PENALTY: dict[int, int] = {2: 3, 3: 6, 4: 10, 5: 15}
_REPORT_PENALTY: dict[int, int] = {1: 1, 2: 2, 3: 4, 4: 6, 5: 8}
_DEFAULT_REPORT_RISK_SCORE = 2
_MIN_DISTANCE_M = 500

# (score以上, grade) の降順リスト。どれにも満たなければ "E"。
_GRADE_THRESHOLDS: list[tuple[int, str]] = [
    (85, "A"),
    (70, "B"),
    (55, "C"),
    (40, "D"),
]


def _grade_for(score: int) -> str:
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "E"


def calculate_safety_score(
    hazard_points: list[HazardPoint],
    danger_reports: list[RouteDangerReport],
    distance_m: float,
) -> tuple[int, str]:
    """ルートの hazard_points・danger_reports・距離から (safety_score, safety_grade) を算出する。"""
    penalty = sum(_HAZARD_PENALTY.get(hazard.risk_score, 0) for hazard in hazard_points)
    penalty += sum(
        _REPORT_PENALTY.get(item.report.risk_score or _DEFAULT_REPORT_RISK_SCORE, 0)
        for item in danger_reports
    )

    penalty_per_km = penalty * 1000 / max(distance_m, _MIN_DISTANCE_M)
    safety_score = max(0, 100 - round(penalty_per_km))
    safety_grade = _grade_for(safety_score)

    return safety_score, safety_grade
