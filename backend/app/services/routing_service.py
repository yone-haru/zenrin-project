from app.core.config import settings
from app.core.http import request_with_retry
from app.models.route import RoutePoint, RouteResult

# 徒歩の所要時間換算: 80m/分（不動産の表示に関する公正競争規約で用いられる標準値）。
# OSRM公開デモサーバはfootプロファイル指定でも実質車ルートの所要時間を返すため、
# footプロファイル時はOSRMのdurationを使わず距離から徒歩時間を算出する。
WALKING_SPEED_M_PER_S = 80 / 60


async def get_route(from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> RouteResult:
    url = f"{settings.osrm_base_url}/{settings.osrm_profile}/{from_lng},{from_lat};{to_lng},{to_lat}"

    response = await request_with_retry(
        "GET",
        url,
        params={"overview": "full", "geometries": "geojson"},
    )
    response.raise_for_status()
    data = response.json()

    routes = data.get("routes")
    if not routes:
        raise ValueError("ルートが見つかりませんでした")

    route = routes[0]
    coordinates = route["geometry"]["coordinates"]  # [lng, lat] の並び
    points = [RoutePoint(latitude=lat, longitude=lng) for lng, lat in coordinates]

    distance_m = route["distance"]
    duration_s = route["duration"]
    if settings.osrm_profile == "foot":
        duration_s = distance_m / WALKING_SPEED_M_PER_S

    return RouteResult(points=points, distance_m=distance_m, duration_s=duration_s)
