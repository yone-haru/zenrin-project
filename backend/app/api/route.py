import httpx
from fastapi import APIRouter, HTTPException

from app.models.route import (
    GeocodeResponse,
    GeocodeResult,
    HazardPoint,
    RouteGeometry,
    RouteRequest,
    RouteResponse,
    RouteSearchResult,
)
from app.services.geocoding_service import search_places
from app.services.route_danger_service import find_danger_reports_along_route
from app.services.routing_service import get_route

router = APIRouter(prefix="/api/route", tags=["route"])
geocode_router = APIRouter(prefix="/api", tags=["geocode"])


def _route_geometry(route_points) -> RouteGeometry:
    return RouteGeometry(
        coordinates=[[point.longitude, point.latitude] for point in route_points],
    )


def _sample_hazards(route_points) -> list[HazardPoint]:
    if not route_points:
        return []

    samples = [
        (
            "honkochi-crossing",
            "本河内交差点",
            0.3,
            5,
            ["歩道なし", "過去事故3件", "幹線道路との交差"],
            3,
            {"highway": "primary", "sidewalk": "none"},
        ),
        (
            "sakuramachi-bridge",
            "桜町歩道橋前",
            0.58,
            3,
            ["見通し不良", "横断歩道の間隔が広い"],
            1,
            {"highway": "secondary", "sidewalk": "left"},
        ),
        (
            "sakaemachi-corner",
            "栄町2丁目角",
            0.82,
            2,
            ["車両の通行が多い"],
            0,
            {"highway": "residential", "sidewalk": "both"},
        ),
    ]

    last_index = max(0, len(route_points) - 1)
    hazards = []
    for hazard_id, title, ratio, score, factors, accidents, tags in samples:
        point = route_points[min(last_index, round(last_index * ratio))]
        hazards.append(
            HazardPoint(
                id=hazard_id,
                title=title,
                latitude=point.latitude,
                longitude=point.longitude,
                risk_score=score,
                risk_factors=factors,
                accident_count=accidents,
                osm_tags=tags,
                distance_from_origin_m=round(1250 * ratio),
            )
        )
    return hazards


@router.get("/geocode", response_model=list[GeocodeResult])
async def geocode(query: str) -> list[GeocodeResult]:
    try:
        return await search_places(query)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="地点検索サービスに接続できませんでした")


@router.get("/search", response_model=RouteSearchResult)
async def search_route(
    from_lat: float,
    from_lng: float,
    to_lat: float,
    to_lng: float,
    buffer_m: float = 30,
) -> RouteSearchResult:
    try:
        route = await get_route(from_lat, from_lng, to_lat, to_lng)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="ルート検索サービスに接続できませんでした")
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))

    danger_reports = find_danger_reports_along_route(route, buffer_m)
    return RouteSearchResult(route=route, danger_reports=danger_reports)


@router.post("", response_model=RouteResponse)
async def create_route(request: RouteRequest) -> RouteResponse:
    try:
        route = await get_route(
            request.origin.lat,
            request.origin.lng,
            request.destination.lat,
            request.destination.lng,
        )
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="ルート検索サービスに接続できませんでした")
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))

    return RouteResponse(
        route_geometry=_route_geometry(route.points),
        distance_m=route.distance_m,
        duration_s=route.duration_s,
        hazard_points=_sample_hazards(route.points),
    )


@geocode_router.get("/geocode", response_model=GeocodeResponse)
async def geocode_by_query(q: str) -> GeocodeResponse:
    try:
        results = await search_places(q)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="地点検索サービスに接続できませんでした")

    if not results:
        raise HTTPException(status_code=404, detail="地点が見つかりませんでした")

    first = results[0]
    return GeocodeResponse(lat=first.latitude, lng=first.longitude, display_name=first.name)
