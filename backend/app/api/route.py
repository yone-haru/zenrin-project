import logging

import httpx
from fastapi import APIRouter, HTTPException

from app.core.geo import LatLng
from app.models.route import (
    GeocodeItem,
    HazardPoint,
    RouteGeometry,
    RouteOption,
    RouteRequest,
    RouteResponse,
    RouteResult,
)
from app.services.geocoding_service import search_places
from app.services.hazard_analysis_service import analyze_hazards
from app.services.overpass_service import OverpassData, OverpassError, compute_bbox, fetch_road_data
from app.services.route_danger_service import find_danger_reports_along_route
from app.services.routing_service import get_routes
from app.services.safety_score import calculate_safety_score

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


async def _fetch_shared_road_data(routes: list[RouteResult]) -> OverpassData:
    """全ルートの合成bboxでOverpassを1回だけ叩き、各ルートの解析に共有するデータを返す。

    per-route/per-pointクエリはOverpassのレート制限に当たるため絶対にしない。
    """
    all_points = [
        LatLng(point.latitude, point.longitude)
        for route in routes
        for point in route.points
    ]
    if not all_points:
        return OverpassData()

    try:
        return await fetch_road_data(compute_bbox(all_points))
    except OverpassError as error:
        logger.warning("Overpass取得に失敗したため事故データのみで解析を継続します: %s", error)
        return OverpassData()


async def _build_route_option(route: RouteResult, road_data: OverpassData) -> RouteOption:
    try:
        hazard_points: list[HazardPoint] = await analyze_hazards(route.points, road_data=road_data)
    except Exception:  # noqa: BLE001 - 危険地点解析の失敗はルート応答自体は返す
        logger.exception("危険地点解析に失敗しました。hazard_pointsなしで応答します")
        hazard_points = []

    danger_reports = find_danger_reports_along_route(route, DANGER_REPORT_BUFFER_M)
    safety_score, safety_grade = calculate_safety_score(hazard_points, danger_reports, route.distance_m)

    return RouteOption(
        id="",  # 最終順序確定後に採番する
        kind="alternative",
        route_geometry=_route_geometry(route.points),
        distance_m=route.distance_m,
        duration_s=route.duration_s,
        safety_score=safety_score,
        safety_grade=safety_grade,
        hazard_points=hazard_points,
        danger_reports=danger_reports,
    )


def _order_and_label(options: list[RouteOption]) -> list[RouteOption]:
    """recommended（safety_score最大・同点はdistance_m最小）を先頭に、残りをdistance_m昇順で並べidを採番する。"""
    best_index = min(
        range(len(options)),
        key=lambda i: (-options[i].safety_score, options[i].distance_m),
    )
    recommended = options[best_index]
    others = sorted(
        (opt for i, opt in enumerate(options) if i != best_index),
        key=lambda opt: opt.distance_m,
    )

    ordered = [recommended, *others]
    return [
        opt.model_copy(update={"id": f"r{idx}", "kind": "recommended" if idx == 0 else "alternative"})
        for idx, opt in enumerate(ordered)
    ]


@router.post("", response_model=RouteResponse)
async def create_route(request: RouteRequest) -> RouteResponse:
    try:
        routes = await get_routes(
            request.origin.lat,
            request.origin.lng,
            request.destination.lat,
            request.destination.lng,
        )
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="ルート検索サービスに接続できませんでした")
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))

    road_data = await _fetch_shared_road_data(routes)

    options = [await _build_route_option(route, road_data) for route in routes]

    return RouteResponse(routes=_order_and_label(options))
