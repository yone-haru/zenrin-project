from app.models.report import Report

# 自動危険地点解析（OSMタグ + 事故件数）のスコアリング
_HAZARD_MIN_SCORE = 1
_HAZARD_MAX_SCORE = 5
_HIGH_SPEED_THRESHOLD_KMH = 50
_MANY_ACCIDENTS_THRESHOLD = 3

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


def _parse_maxspeed_kmh(raw: str) -> int | None:
    """OSMのmaxspeedタグ（例: "50", "50 km/h", "30 mph"）をkm/hの整数値に変換する。"""
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return None
    value = int(digits)
    if "mph" in raw.lower():
        value = round(value * 1.60934)
    return value


def calculate_hazard_score(
    osm_tags: dict[str, str],
    accident_count: int,
    has_uncontrolled_intersection: bool = False,
    complex_intersection: bool = False,
    sharp_curve: bool = False,
) -> tuple[int, list[str]]:
    """OSM道路タグと近傍事故件数から危険スコア（1〜5）と要因一覧を算出する。

    仮定: `sidewalk` タグが明示的に `no`/`none` の場合のみ「歩道なし」と判定する
    （タグ自体が存在しない住宅地道路は非常に多く、欠如＝歩道なしと解釈すると
    過大評価になりやすいため）。

    complex_intersection（変則交差点・五差路など）は has_uncontrolled_intersection
    （信号・横断歩道の有無）とは独立に加点する。信号があっても道路の合流本数が
    多ければ見通し・判断の複雑さは残るため。
    """
    score = 0
    factors: list[str] = []

    highway = (osm_tags.get("highway") or "").lower()
    sidewalk = (osm_tags.get("sidewalk") or "").lower()
    maxspeed_kmh = _parse_maxspeed_kmh(osm_tags.get("maxspeed", ""))

    if sidewalk in ("no", "none"):
        score += 2
        factors.append("歩道なし")

    if highway in ("trunk", "primary"):
        score += 2
        factors.append("幹線道路（高速走行が多い区間）")
    elif highway in ("secondary", "tertiary"):
        score += 1
        factors.append("主要道路")

    if maxspeed_kmh is not None and maxspeed_kmh >= _HIGH_SPEED_THRESHOLD_KMH:
        score += 1
        factors.append(f"制限速度{maxspeed_kmh}km/h以上")

    if has_uncontrolled_intersection:
        score += 1
        factors.append("信号・横断歩道のない交差点")

    if complex_intersection:
        score += 1
        factors.append("複雑な交差点（五差路など）")

    if sharp_curve:
        score += 1
        factors.append("急カーブ")

    if accident_count >= _MANY_ACCIDENTS_THRESHOLD:
        score += 2
        factors.append(f"事故多発（{accident_count}件）")
    elif accident_count >= 1:
        score += 1
        factors.append(f"過去事故あり（{accident_count}件）")

    score = max(_HAZARD_MIN_SCORE, min(score, _HAZARD_MAX_SCORE))
    return score, factors
