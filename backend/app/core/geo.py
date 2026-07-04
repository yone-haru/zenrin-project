import math
from typing import NamedTuple

EARTH_RADIUS_M = 6371000


def haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


class LatLng(NamedTuple):
    lat: float
    lng: float


def _to_local_xy(point: LatLng, origin: LatLng) -> tuple[float, float]:
    """originを基準にした平面近似座標（メートル）に変換する。

    短距離（数km以内）であれば等長方位図法的な近似で十分な精度が出るため、
    経路サンプリングや点-線分距離計算のような軽量な幾何処理に用いる。
    """
    lat_rad = math.radians(origin.lat)
    x = math.radians(point.lng - origin.lng) * math.cos(lat_rad) * EARTH_RADIUS_M
    y = math.radians(point.lat - origin.lat) * EARTH_RADIUS_M
    return x, y


def point_to_segment_distance_m(point: LatLng, seg_start: LatLng, seg_end: LatLng) -> float:
    """点と線分の最短距離（メートル）を平面近似で求める。"""
    origin = seg_start
    px, py = _to_local_xy(point, origin)
    ax, ay = 0.0, 0.0
    bx, by = _to_local_xy(seg_end, origin)

    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return math.hypot(px - ax, py - ay)

    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    closest_x = ax + t * dx
    closest_y = ay + t * dy
    return math.hypot(px - closest_x, py - closest_y)


def point_to_polyline_distance_m(point: LatLng, polyline: list[LatLng]) -> float:
    """点と折れ線（複数線分）の最短距離（メートル）を求める。"""
    if len(polyline) == 1:
        return haversine_distance_m(point.lat, point.lng, polyline[0].lat, polyline[0].lng)

    return min(
        point_to_segment_distance_m(point, polyline[i], polyline[i + 1])
        for i in range(len(polyline) - 1)
    )


def sample_polyline(polyline: list[LatLng], interval_m: float) -> list[tuple[LatLng, float]]:
    """折れ線をinterval_m間隔でサンプリングし、(地点, 起点からの沿道距離m)を返す。

    始点・終点は必ず含む。折れ線が空の場合は空リストを返す。
    """
    if not polyline:
        return []
    if len(polyline) == 1:
        return [(polyline[0], 0.0)]

    segment_lengths = [
        haversine_distance_m(
            polyline[i].lat, polyline[i].lng, polyline[i + 1].lat, polyline[i + 1].lng
        )
        for i in range(len(polyline) - 1)
    ]
    total_length = sum(segment_lengths)

    samples: list[tuple[LatLng, float]] = [(polyline[0], 0.0)]
    next_target = interval_m
    cumulative = 0.0

    for i, seg_len in enumerate(segment_lengths):
        seg_start, seg_end = polyline[i], polyline[i + 1]
        while seg_len > 0 and next_target <= cumulative + seg_len:
            ratio = (next_target - cumulative) / seg_len
            lat = seg_start.lat + (seg_end.lat - seg_start.lat) * ratio
            lng = seg_start.lng + (seg_end.lng - seg_start.lng) * ratio
            samples.append((LatLng(lat, lng), next_target))
            next_target += interval_m
        cumulative += seg_len

    if total_length > 0 and (not samples or samples[-1][1] < total_length - 1e-6):
        samples.append((polyline[-1], total_length))

    return samples
