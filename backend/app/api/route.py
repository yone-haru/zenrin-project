import logging

import httpx
from fastapi import APIRouter, HTTPException

from app.models.route import (
    GeocodeItem,
    HazardPoint,
    RouteGeometry,
    RouteRequest,
    RouteResponse,
)
from app.services.geocoding_service import search_places
from app.services.hazard_analysis_service import analyze_hazards
from app.services.route_danger_service import find_danger_reports_along_route
from app.services.routing_service import get_route

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/route", tags=["route"])
geocode_router = APIRouter(prefix="/api", tags=["geocode"])

DANGER_REPORT_BUFFER_M = 30


def _route_geometry(route_points) -> RouteGeometry:
    return RouteGeometry(
        coordinates=[[point.longitude, point.latitude] for point in route_points],
    )


@geocode_router.get("/geocode", response_model=list[GeocodeItem])
async def geocode(q: str, limit: int = 5) -> list[GeocodeItem]:
    try:
        results = await search_places(q, limit)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="地点検索サービスに接続できませんでした")

    return [GeocodeItem(name=r.name, lat=r.latitude, lng=r.longitude) for r in results]


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

    try:
        hazard_points: list[HazardPoint] = await analyze_hazards(route.points)
    except Exception:  # noqa: BLE001 - 危険地点解析の失敗はルート応答自体は返す
        logger.exception("危険地点解析に失敗しました。hazard_pointsなしで応答します")
        hazard_points = []

    danger_reports = find_danger_reports_along_route(route, DANGER_REPORT_BUFFER_M)

    return RouteResponse(
        route_geometry=_route_geometry(route.points),
        distance_m=route.distance_m,
        duration_s=route.duration_s,
        hazard_points=hazard_points,
        danger_reports=danger_reports,
    )
