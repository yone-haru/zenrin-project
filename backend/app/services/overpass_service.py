"""OSM Overpass API連携。

ルート全体を包含するbboxで **1回だけ** クエリを投げ（1点ずつのクエリは禁止）、
結果をメモリTTLキャッシュする。bboxは0.005度単位に外側丸めしてからキャッシュキー
兼実際の問い合わせ範囲とすることで、近接するルート同士のキャッシュヒット率を高める。
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from app.core.config import settings
from app.core.geo import LatLng
from app.core.http import request_with_retry

CACHE_PRECISION_DEGREES = 0.005
CACHE_TTL_S = 3600
BBOX_MARGIN_M = 50


@dataclass(frozen=True)
class OsmWay:
    id: int
    tags: dict[str, str]
    geometry: list[LatLng]


@dataclass(frozen=True)
class OsmNode:
    id: int
    tags: dict[str, str]
    point: LatLng


@dataclass(frozen=True)
class OverpassData:
    ways: list[OsmWay] = field(default_factory=list)
    nodes: list[OsmNode] = field(default_factory=list)


_cache: dict[tuple[float, float, float, float], tuple[float, OverpassData]] = {}


class OverpassError(Exception):
    """Overpass APIへの問い合わせに失敗した場合の例外。"""


def _round_bbox(
    min_lat: float, min_lng: float, max_lat: float, max_lng: float
) -> tuple[float, float, float, float]:
    precision = CACHE_PRECISION_DEGREES
    return (
        math.floor(min_lat / precision) * precision,
        math.floor(min_lng / precision) * precision,
        math.ceil(max_lat / precision) * precision,
        math.ceil(max_lng / precision) * precision,
    )


def compute_bbox(points: list[LatLng], margin_m: float = BBOX_MARGIN_M) -> tuple[float, float, float, float]:
    """ルート全体を包含するbbox（min_lat, min_lng, max_lat, max_lng）を返す。"""
    lats = [p.lat for p in points]
    lngs = [p.lng for p in points]
    lat_margin = margin_m / 111_000
    avg_lat = sum(lats) / len(lats)
    lng_margin = margin_m / (111_000 * max(math.cos(math.radians(avg_lat)), 0.1))
    return (
        min(lats) - lat_margin,
        min(lngs) - lng_margin,
        max(lats) + lat_margin,
        max(lngs) + lng_margin,
    )


def _build_query(bbox: tuple[float, float, float, float]) -> str:
    min_lat, min_lng, max_lat, max_lng = bbox
    bbox_str = f"{min_lat},{min_lng},{max_lat},{max_lng}"
    return f"""
[out:json][timeout:25];
(
  way[highway]({bbox_str});
  node[highway~"crossing|traffic_signals"]({bbox_str});
);
out geom;
"""


def _parse_response(data: dict) -> OverpassData:
    ways: list[OsmWay] = []
    nodes: list[OsmNode] = []

    for element in data.get("elements", []):
        tags = element.get("tags", {})
        if element.get("type") == "way":
            geometry = [LatLng(g["lat"], g["lon"]) for g in element.get("geometry", []) if g]
            if geometry:
                ways.append(OsmWay(id=element["id"], tags=tags, geometry=geometry))
        elif element.get("type") == "node":
            nodes.append(
                OsmNode(id=element["id"], tags=tags, point=LatLng(element["lat"], element["lon"]))
            )

    return OverpassData(ways=ways, nodes=nodes)


async def fetch_road_data(bbox: tuple[float, float, float, float]) -> OverpassData:
    """既知のbbox（min_lat, min_lng, max_lat, max_lng）のOSM道路・交差点情報を取得する（TTLキャッシュ付き）。

    複数ルートを解析する場合は、呼び出し側で全ルートの合成bboxを1つ計算し、
    このメソッドを1回だけ呼ぶこと（per-route/per-pointクエリはレート制限に当たるため禁止）。
    """
    bbox = _round_bbox(*bbox)

    cached = _cache.get(bbox)
    if cached is not None:
        cached_at, data = cached
        if time.monotonic() - cached_at < CACHE_TTL_S:
            return data

    query = _build_query(bbox)

    try:
        response = await request_with_retry(
            "POST", settings.overpass_api_url, data={"data": query}
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as error:  # noqa: BLE001 - 外部APIの失敗は全て呼び出し元へ伝播させる
        raise OverpassError(f"Overpass APIへの問い合わせに失敗しました: {error}") from error

    parsed = _parse_response(payload)
    _cache[bbox] = (time.monotonic(), parsed)
    return parsed


async def fetch_osm_features(points: list[LatLng]) -> OverpassData:
    """ルートpointsを包含するbboxのOSM道路・交差点情報を取得する（TTLキャッシュ付き）。"""
    if not points:
        return OverpassData()

    return await fetch_road_data(compute_bbox(points))


def clear_cache() -> None:
    """テスト用にキャッシュをクリアする。"""
    _cache.clear()
