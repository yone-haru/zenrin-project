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


def point_at_distance_m(polyline: list[LatLng], target_m: float) -> LatLng:
    """折れ線の起点からtarget_m（沿道距離）進んだ地点を線形補間で返す。

    target_m が範囲外の場合は始点・終点にクランプする（急カーブ判定で
    ルート両端付近の窓が route 外にはみ出さないようにするため）。
    """
    if not polyline:
        raise ValueError("polyline is empty")
    if len(polyline) == 1:
        return polyline[0]

    target_m = max(0.0, target_m)
    cumulative = 0.0
    for i in range(len(polyline) - 1):
        seg_start, seg_end = polyline[i], polyline[i + 1]
        seg_len = haversine_distance_m(seg_start.lat, seg_start.lng, seg_end.lat, seg_end.lng)
        if seg_len == 0:
            continue
        if target_m <= cumulative + seg_len:
            ratio = max(0.0, min(1.0, (target_m - cumulative) / seg_len))
            lat = seg_start.lat + (seg_end.lat - seg_start.lat) * ratio
            lng = seg_start.lng + (seg_end.lng - seg_start.lng) * ratio
            return LatLng(lat, lng)
        cumulative += seg_len

    return polyline[-1]


def bearing_deg(start: LatLng, end: LatLng) -> float:
    """startからendへの方位角（度・0-360、北=0・東=90）を返す。"""
    lat1 = math.radians(start.lat)
    lat2 = math.radians(end.lat)
    d_lng = math.radians(end.lng - start.lng)
    x = math.sin(d_lng) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lng)
    theta = math.atan2(x, y)
    return (math.degrees(theta) + 360) % 360


def bearing_change_deg(bearing1: float, bearing2: float) -> float:
    """2つの方位角の差（0-180度、向きは区別しない）を返す。"""
    diff = abs(bearing1 - bearing2) % 360
    return min(diff, 360 - diff)
