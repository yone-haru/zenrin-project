from app.core.config import settings
from app.core.http import request_with_retry
from app.models.route import RoutePoint, RouteResult

# 徒歩の所要時間換算: 80m/分（不動産の表示に関する公正競争規約で用いられる標準値）。
# OSRM公開デモサーバはfootプロファイル指定でも実質車ルートの所要時間を返すため、
# footプロファイル時はOSRMのdurationを使わず距離から徒歩時間を算出する。
WALKING_SPEED_M_PER_S = 80 / 60

# ルート比較UIで扱う上限件数（プラン v3: 最大3ルート）。
MAX_ALTERNATIVE_ROUTES = 3


def _to_route_result(route: dict) -> RouteResult:
    coordinates = route["geometry"]["coordinates"]  # [lng, lat] の並び
    points = [RoutePoint(latitude=lat, longitude=lng) for lng, lat in coordinates]

    distance_m = route["distance"]
    duration_s = route["duration"]
    if settings.osrm_profile == "foot":
        duration_s = distance_m / WALKING_SPEED_M_PER_S

    return RouteResult(points=points, distance_m=distance_m, duration_s=duration_s)


async def get_routes(
    from_lat: float, from_lng: float, to_lat: float, to_lng: float
) -> list[RouteResult]:
    """OSRMからルート（推奨1件＋代替ルート）を最大 MAX_ALTERNATIVE_ROUTES 件取得する。

    footプロファイル時は各ルートのdurationを80m/分で再計算する。
    """
    url = f"{settings.osrm_base_url}/{settings.osrm_profile}/{from_lng},{from_lat};{to_lng},{to_lat}"

    response = await request_with_retry(
        "GET",
        url,
        params={
            "overview": "full",
            "geometries": "geojson",
            "alternatives": "true",
        },
    )
    response.raise_for_status()
    data = response.json()

    routes = data.get("routes")
    if not routes:
        raise ValueError("ルートが見つかりませんでした")

    return [_to_route_result(route) for route in routes[:MAX_ALTERNATIVE_ROUTES]]
