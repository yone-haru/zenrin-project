from app.models.report import Report, ReportStatus
from app.models.route import HazardPoint, RouteDangerReport
from app.services.safety_score import calculate_safety_score


def _hazard(risk_score: int) -> HazardPoint:
    return HazardPoint(
        id=f"hazard-{risk_score}",
        latitude=32.75,
        longitude=129.87,
        risk_score=risk_score,
        risk_factors=[],
        accident_count=0,
        osm_tags={},
    )


def _danger_report(risk_score: int | None) -> RouteDangerReport:
    report = Report(
        latitude=32.75,
        longitude=129.87,
        image_urls=["/uploads/x.jpg"],
        risk_score=risk_score,
        status=ReportStatus.UNCONFIRMED,
    )
    return RouteDangerReport(report=report, distance_from_route_m=5.0)


def test_no_hazards_or_reports_gives_full_score_and_grade_a() -> None:
    score, grade = calculate_safety_score([], [], 1000)

    assert score == 100
    assert grade == "A"


def test_hazard_penalty_applied_and_normalized_per_km() -> None:
    # risk_score 5 -> penalty 15。distance 1000m -> penalty_per_km = 15 -> score 85
    score, grade = calculate_safety_score([_hazard(5)], [], 1000)

    assert score == 85
    assert grade == "A"


def test_short_route_uses_minimum_500m_for_normalization() -> None:
    # distance_m=200 < 500 のため 500 で正規化される。
    # penalty=3 (risk_score2) -> penalty_per_km = 3*1000/500 = 6 -> score 94
    score, grade = calculate_safety_score([_hazard(2)], [], 200)

    assert score == 94
    assert grade == "A"


def test_danger_report_penalty_uses_report_risk_score() -> None:
    # report.risk_score=4 -> penalty 6。distance 1000m -> penalty_per_km=6 -> score 94
    score, grade = calculate_safety_score([], [_danger_report(4)], 1000)

    assert score == 94
    assert grade == "A"


def test_danger_report_without_risk_score_defaults_to_2() -> None:
    # risk_score未設定(None) -> デフォルト2扱い -> penalty 2。distance 1000m -> score 98
    score, grade = calculate_safety_score([], [_danger_report(None)], 1000)

    assert score == 98
    assert grade == "A"


def test_combined_hazards_and_reports_can_reach_lower_grades() -> None:
    hazards = [_hazard(5), _hazard(5), _hazard(4)]  # penalty = 15+15+10 = 40
    reports = [_danger_report(5), _danger_report(3)]  # penalty = 8+4 = 12
    # 合計penalty=52, distance=1000m -> penalty_per_km=52 -> score=48 -> grade D
    score, grade = calculate_safety_score(hazards, reports, 1000)

    assert score == 48
    assert grade == "D"


def test_grade_thresholds() -> None:
    assert calculate_safety_score([], [], 1000) == (100, "A")
    # penalty_per_kmを調整してB/C/D/Eの境界付近を確認する
    # score=70 -> penalty_per_km=30 -> B (70 >= 70)
    score, grade = calculate_safety_score([_hazard(5), _hazard(5)], [], 1000)
    assert score == 70
    assert grade == "B"

    # score=55 -> penalty_per_km=45 -> C (55 >= 55)
    score, grade = calculate_safety_score([_hazard(5), _hazard(5), _hazard(5)], [], 1000)
    assert score == 55
    assert grade == "C"

    # score=40 -> penalty_per_km=60 -> D (40 >= 40)
    score, grade = calculate_safety_score([_hazard(5), _hazard(5), _hazard(5), _hazard(5)], [], 1000)
    assert score == 40
    assert grade == "D"

    # penalty_per_km=61 -> score=39 -> E
    score, grade = calculate_safety_score(
        [_hazard(5), _hazard(5), _hazard(5), _hazard(5)], [_danger_report(1)], 1000
    )
    assert score == 39
    assert grade == "E"


def test_score_never_goes_below_zero() -> None:
    hazards = [_hazard(5) for _ in range(20)]  # penalty = 300
    score, grade = calculate_safety_score(hazards, [], 500)

    assert score == 0
    assert grade == "E"
