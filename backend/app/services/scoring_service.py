from app.models.report import Report

_KEYWORD_WEIGHTS: dict[str, int] = {
    "ガードレール": 2,
    "見通し": 2,
    "街灯": 1,
    "歩道が狭": 1,
    "出会い頭": 2,
    "カーブ": 1,
}

_BASE_SCORE = 1
_MAX_SCORE = 5

# 緯度経度の差がこの範囲内（およそ50m相当）であれば同一地点とみなす
NEARBY_RADIUS_DEGREES = 0.0005


def calculate_risk_score(description: str) -> int:
    score = _BASE_SCORE
    for keyword, weight in _KEYWORD_WEIGHTS.items():
        if keyword in description:
            score += weight
    return min(score, _MAX_SCORE)


def is_nearby(a: Report, b: Report) -> bool:
    return (
        abs(a.latitude - b.latitude) <= NEARBY_RADIUS_DEGREES
        and abs(a.longitude - b.longitude) <= NEARBY_RADIUS_DEGREES
    )


def aggregate_nearby_scores(new_report: Report, existing_reports: list[Report]) -> list[Report]:
    """new_reportと近隣の既存投稿をまとめ、平均スコアで更新したReport一覧を返す。"""
    cluster = [r for r in existing_reports if is_nearby(new_report, r)]
    cluster.append(new_report)

    average = round(sum(r.risk_score or 0 for r in cluster) / len(cluster))
    average = max(_BASE_SCORE, min(average, _MAX_SCORE))

    for r in cluster:
        r.risk_score = average

    return cluster
