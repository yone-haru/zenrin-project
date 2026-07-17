"""ルート沿いの自動危険地点解析パイプライン。

手順:
1. ルートpolylineを50m間隔でサンプリング
2. 各サンプル点を最寄りのOSM way（30m以内）にマッチさせ道路タグを取得
   （Overpass取得に失敗した場合や30m以内にwayが無い場合はタグなしとして続行し、
   事故データのみでスコアリングする＝降格継続）
3. 各サンプル点周辺の事故件数を取得
4. スコアリング（1〜5）し、閾値（>=2）未満は除外
5. 120m以内の候補地点をクラスタ統合（最大スコアを採用、要因は和集合）
   ※クラスタ半径はサンプリング間隔（50m）より大きくすること。40m等にすると
   隣接サンプルが一切統合されず、同じ通り沿いにピンが乱立する（統合検証で判明）。
"""

from __future__ import annotations

import logging
import uuid

from app.core.geo import (
    LatLng,
    bearing_change_deg,
    bearing_deg,
    haversine_distance_m,
    point_at_distance_m,
    point_to_polyline_distance_m,
    sample_polyline,
)
from app.models.route import HazardPoint, RoutePoint
from app.services import accident_service
from app.services.overpass_service import OverpassData, OverpassError, fetch_osm_features
from app.services.scoring_service import _MANY_ACCIDENTS_THRESHOLD, calculate_hazard_score

logger = logging.getLogger(__name__)

SAMPLE_INTERVAL_M = 50
WAY_MATCH_RADIUS_M = 30
INTERSECTION_WAY_RADIUS_M = 15
JUNCTION_NODE_RADIUS_M = 30
CROSSING_NODE_RADIUS_M = 20
ACCIDENT_SEARCH_RADIUS_M = 50
MIN_HAZARD_SCORE = 2
# サンプリング間隔(50m)より大きくないと隣接サンプルが統合されない点に注意
CLUSTER_RADIUS_M = 120
# 変則交差点（五差路など）: ノード共有が確認できた道路グループがこの数以上なら複雑とみなす
MIN_GROUPS_FOR_COMPLEX_INTERSECTION = 3
# 急カーブ判定: サンプル点の前後この距離（m）での方位変化を見る
SHARP_CURVE_WINDOW_M = 20
# この角度（度）以上の方位変化があれば急カーブとする
SHARP_CURVE_ANGLE_THRESHOLD_DEG = 60


def _match_way_tags(point: LatLng, osm_data: OverpassData) -> dict[str, str]:
    best_tags: dict[str, str] = {}
    best_distance = WAY_MATCH_RADIUS_M
    for way in osm_data.ways:
        distance = point_to_polyline_distance_m(point, way.geometry)
        if distance <= best_distance:
            best_distance = distance
            best_tags = way.tags
    return best_tags


# 交差点判定の対象外とする歩行者・非車道系のhighway種別。
# 日本のOSMでは歩道・階段・敷地内通路が車道と並行する別wayとして大量に登録されており、
# これらを道路本数に数えると「ほぼ全地点が交差点」になる誤検出を招く。
_NON_ROADWAY_HIGHWAYS = {
    "footway",
    "path",
    "steps",
    "cycleway",
    "pedestrian",
    "corridor",
    "bridleway",
    "platform",
    "construction",
    "proposed",
    "service",
    "track",
}


def _way_group_key(way) -> str:
    """交差点判定用のwayグループキー。

    国道の対向車線ペア（onewayの平行way 2本）のように、同じ道路が複数のwayに
    分かれて登録されているケースを「2本の別の道路」と誤認しないよう、
    name（なければref、それもなければway id）でグループ化する。
    """
    name = (way.tags.get("name") or "").strip()
    if name:
        return f"name:{name}"
    ref = (way.tags.get("ref") or "").strip()
    if ref:
        return f"ref:{ref}"
    return f"id:{way.id}"


def _way_coords(way) -> set:
    return {(round(p.lat, 7), round(p.lng, 7)) for p in way.geometry}


def _intersection_way_groups_near(point: LatLng, osm_data: OverpassData) -> dict:
    groups: dict = {}
    for way in osm_data.ways:
        if (way.tags.get("highway") or "").lower() in _NON_ROADWAY_HIGHWAYS:
            continue
        if point_to_polyline_distance_m(point, way.geometry) <= INTERSECTION_WAY_RADIUS_M:
            groups.setdefault(_way_group_key(way), []).append(way)
    return groups


def _connected_group_count_near(point: LatLng, groups: dict) -> int:
    """pointの近くでノード（座標）を共有している道路グループの数を返す。

    OSMでは交差・接続する道路は必ず共通ノードを持つ一方、oneway対向車線ペアの
    ような並行道路はノードを共有しない。これにより「近くにway 2本＝交差点」の
    誤検出（並行車線・並走する別道路）を防ぐ。戻り値は「pointの近くで互いに
    ノードを共有していることが確認できたグループ」の数（0/1なら交差点ではない、
    3以上なら五差路等の変則交差点候補）。
    """
    coords_by_group = {
        key: set().union(*(_way_coords(w) for w in ways)) for key, ways in groups.items()
    }
    keys = list(coords_by_group)
    connected_keys: set = set()
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            shared = coords_by_group[keys[i]] & coords_by_group[keys[j]]
            for lat, lng in shared:
                if haversine_distance_m(point.lat, point.lng, lat, lng) <= JUNCTION_NODE_RADIUS_M:
                    connected_keys.add(keys[i])
                    connected_keys.add(keys[j])
    return len(connected_keys)


def _intersection_info(point: LatLng, osm_data: OverpassData) -> tuple[bool, int]:
    """pointにおける交差点情報を (has_uncontrolled_intersection, connected_group_count) で返す。

    has_uncontrolled_intersection: ノード共有が確認できた道路が2本以上あり、かつ
    近くに信号・横断歩道・一時停止等の制御ノードが無い場合True。
    connected_group_count: ノード共有が確認できた道路グループ数（複雑な交差点判定に使う）。
    """
    groups = _intersection_way_groups_near(point, osm_data)
    if len(groups) < 2:
        return False, 0

    group_count = _connected_group_count_near(point, groups)
    if group_count < 2:
        return False, 0

    has_crossing_control = any(
        haversine_distance_m(point.lat, point.lng, node.point.lat, node.point.lng)
        <= CROSSING_NODE_RADIUS_M
        for node in osm_data.nodes
    )
    return not has_crossing_control, group_count


def _has_uncontrolled_intersection(point: LatLng, osm_data: OverpassData) -> bool:
    has_uncontrolled, _ = _intersection_info(point, osm_data)
    return has_uncontrolled


def _detect_sharp_curve(
    polyline: list[LatLng], point: LatLng, distance_from_origin: float
) -> bool:
    """pointの前後SHARP_CURVE_WINDOW_M地点との方位変化がしきい値以上なら急カーブとみなす。

    ルート端付近で前後どちらかの窓がクランプにより point 自身と同一地点になる
    場合は方位を計算できないため急カーブなしとする。
    """
    before = point_at_distance_m(polyline, distance_from_origin - SHARP_CURVE_WINDOW_M)
    after = point_at_distance_m(polyline, distance_from_origin + SHARP_CURVE_WINDOW_M)

    if haversine_distance_m(before.lat, before.lng, point.lat, point.lng) < 1.0:
        return False
    if haversine_distance_m(after.lat, after.lng, point.lat, point.lng) < 1.0:
        return False

    bearing_in = bearing_deg(before, point)
    bearing_out = bearing_deg(point, after)
    return bearing_change_deg(bearing_in, bearing_out) >= SHARP_CURVE_ANGLE_THRESHOLD_DEG


def _title_for(osm_tags: dict[str, str], has_intersection: bool) -> str:
    name = osm_tags.get("name")
    if name:
        return name
    highway = osm_tags.get("highway")
    if has_intersection:
        return "信号・横断歩道のない交差点"
    if highway in ("trunk", "primary"):
        return "幹線道路沿いの危険区間"
    if highway in ("secondary", "tertiary"):
        return "主要道路沿いの危険区間"
    if highway:
        return "道路沿いの危険区間"
    return "事故多発地点"


def _cluster(candidates: list[HazardPoint]) -> list[HazardPoint]:
    """CLUSTER_RADIUS_M以内の候補を統合する（単純な貪欲法によるクラスタリング）。"""
    clusters: list[list[HazardPoint]] = []
    for candidate in candidates:
        for cluster in clusters:
            representative = cluster[0]
            if (
                haversine_distance_m(
                    representative.latitude,
                    representative.longitude,
                    candidate.latitude,
                    candidate.longitude,
                )
                <= CLUSTER_RADIUS_M
            ):
                cluster.append(candidate)
                break
        else:
            clusters.append([candidate])

    merged: list[HazardPoint] = []
    for cluster in clusters:
        best = max(cluster, key=lambda h: h.risk_score)
        accident_count = max(member.accident_count for member in cluster)

        # 事故件数に言及する要因は数値がメンバー間で異なりうるため、和集合を取ると
        # 「事故多発（5件）」「事故多発（4件）」のように重複した表現が残ってしまう。
        # クラスタ全体の最終accident_countに基づき1つだけ再生成する。
        non_accident_factors = [
            f for member in cluster for f in member.risk_factors
            if "事故多発" not in f and "過去事故あり" not in f
        ]
        factors = list(dict.fromkeys(non_accident_factors))
        if accident_count >= _MANY_ACCIDENTS_THRESHOLD:
            factors.append(f"事故多発（{accident_count}件）")
        elif accident_count >= 1:
            factors.append(f"過去事故あり（{accident_count}件）")

        merged.append(
            HazardPoint(
                id=best.id,
                title=best.title,
                latitude=best.latitude,
                longitude=best.longitude,
                risk_score=best.risk_score,
                risk_factors=factors,
                accident_count=accident_count,
                osm_tags=best.osm_tags,
                distance_from_origin_m=best.distance_from_origin_m,
            )
        )
    return merged


async def analyze_hazards(
    route_points: list[RoutePoint],
    road_data: OverpassData | None = None,
) -> list[HazardPoint]:
    """ルート沿いの危険地点を解析する。

    road_data を渡した場合はOverpassへ問い合わせず、渡されたデータをそのまま使う。
    複数ルートをまとめて解析する場合は、呼び出し側で全ルート合成bboxを1回だけ
    fetch_road_data() で取得し、各ルートの解析にこの引数で共有すること
    （per-route Overpassクエリはレート制限に当たるため禁止）。
    road_data が None の場合は従来どおりこの関数がルート単体のbboxで取得する。
    """
    if not route_points:
        return []

    polyline = [LatLng(p.latitude, p.longitude) for p in route_points]

    if road_data is not None:
        osm_data = road_data
    else:
        try:
            osm_data = await fetch_osm_features(polyline)
        except OverpassError as error:
            logger.warning("Overpass取得に失敗したため事故データのみで解析を継続します: %s", error)
            osm_data = OverpassData()

    samples = sample_polyline(polyline, SAMPLE_INTERVAL_M)

    candidates: list[HazardPoint] = []
    for point, distance_from_origin in samples:
        osm_tags = _match_way_tags(point, osm_data)
        has_intersection, group_count = _intersection_info(point, osm_data)
        complex_intersection = group_count >= MIN_GROUPS_FOR_COMPLEX_INTERSECTION
        sharp_curve = _detect_sharp_curve(polyline, point, distance_from_origin)
        accident_count = accident_service.count_near(point.lat, point.lng, ACCIDENT_SEARCH_RADIUS_M)

        score, factors = calculate_hazard_score(
            osm_tags,
            accident_count,
            has_intersection,
            complex_intersection=complex_intersection,
            sharp_curve=sharp_curve,
        )
        if score < MIN_HAZARD_SCORE:
            continue

        candidates.append(
            HazardPoint(
                id=str(uuid.uuid4()),
                title=_title_for(osm_tags, has_intersection),
                latitude=point.lat,
                longitude=point.lng,
                risk_score=score,
                risk_factors=factors,
                accident_count=accident_count,
                osm_tags=osm_tags,
                distance_from_origin_m=round(distance_from_origin, 1),
            )
        )

    return _cluster(candidates)
