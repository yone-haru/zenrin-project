"""Google Routes API (computeRoutes) 連携サービス。

`settings.google_maps_api_key` が設定されている場合のみ routing_service から呼び出される。
徒歩ルート（推奨1件＋代替）を最大 MAX_ALTERNATIVE_ROUTES 件取得する。

GoogleのWALK durationは実測ベースの徒歩所要時間のため、OSRM公開デモサーバ対策である
80m/分の再計算（routing_service._get_routes_osrm 側の仕様）はここでは行わない。
"""

from __future__ import annotations

from app.core.config import settings
from app.core.http import request_with_retry
from app.models.route import RoutePoint, RouteResult

ROUTES_API_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

FIELD_MASK = "routes.distanceMeters,routes.duration,routes.polyline"

# ルート比較UIで扱う上限件数（プラン v3: 最大3ルート。OSRM側と揃える）。
MAX_ALTERNATIVE_ROUTES = 3


def _parse_duration_seconds(duration: str) -> float:
    """Routes APIのDuration形式（例: "1234s"）を秒（float）に変換する。"""
    return float(duration.rstrip("s"))


def _to_route_result(route: dict) -> RouteResult:
    coordinates = route["polyline"]["geoJsonLinestring"]["coordinates"]  # [lng, lat] の並び
    points = [RoutePoint(latitude=lat, longitude=lng) for lng, lat in coordinates]

    distance_m = float(route["distanceMeters"])
    duration_s = _parse_duration_seconds(route["duration"])

    return RouteResult(points=points, distance_m=distance_m, duration_s=duration_s)


async def get_routes(
    from_lat: float, from_lng: float, to_lat: float, to_lng: float
) -> list[RouteResult]:
    """Google Routes API から徒歩ルート（推奨1件＋代替ルート）を取得する。"""
    body = {
        "origin": {"location": {"latLng": {"latitude": from_lat, "longitude": from_lng}}},
        "destination": {"location": {"latLng": {"latitude": to_lat, "longitude": to_lng}}},
        "travelMode": "WALK",
        "computeAlternativeRoutes": True,
        "polylineEncoding": "GEO_JSON_LINESTRING",
        "languageCode": "ja-JP",
        "units": "METRIC",
    }

    response = await request_with_retry(
        "POST",
        ROUTES_API_URL,
        headers={
            "X-Goog-Api-Key": settings.google_maps_api_key,
            "X-Goog-FieldMask": FIELD_MASK,
            "Content-Type": "application/json",
        },
        json=body,
    )
    response.raise_for_status()
    data = response.json()

    routes = data.get("routes")
    if not routes:
        raise ValueError("ルートが見つかりませんでした")

    return [_to_route_result(route) for route in routes[:MAX_ALTERNATIVE_ROUTES]]
