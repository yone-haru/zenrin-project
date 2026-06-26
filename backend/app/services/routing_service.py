import httpx

from app.models.route import RoutePoint, RouteResult

# OSRM公開デモサーバー（無料・登録不要、商用利用不可）。
# 将来的にゼンリンのルーティングAPI等、安定運用可能なサービスに差し替える。
OSRM_BASE_URL = "https://router.project-osrm.org/route/v1/foot"


async def get_route(from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> RouteResult:
    url = f"{OSRM_BASE_URL}/{from_lng},{from_lat};{to_lng},{to_lat}"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            params={"overview": "full", "geometries": "geojson"},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()

    routes = data.get("routes")
    if not routes:
        raise ValueError("ルートが見つかりませんでした")

    route = routes[0]
    coordinates = route["geometry"]["coordinates"]  # [lng, lat] の並び
    points = [RoutePoint(latitude=lat, longitude=lng) for lng, lat in coordinates]

    return RouteResult(points=points, distance_m=route["distance"], duration_s=route["duration"])
