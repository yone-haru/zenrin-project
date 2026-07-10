from typing import Literal

from pydantic import BaseModel

from app.models.report import Report


class GeocodeResult(BaseModel):
    name: str
    latitude: float
    longitude: float


class RoutePoint(BaseModel):
    latitude: float
    longitude: float


class RouteResult(BaseModel):
    points: list[RoutePoint]
    distance_m: float
    duration_s: float


class RouteDangerReport(BaseModel):
    report: Report
    distance_from_route_m: float


class RouteLocation(BaseModel):
    lat: float
    lng: float
    address: str | None = None


class RouteRequest(BaseModel):
    origin: RouteLocation
    destination: RouteLocation


class HazardPoint(BaseModel):
    id: str
    latitude: float
    longitude: float
    risk_score: int
    risk_factors: list[str]
    accident_count: int
    osm_tags: dict[str, str]
    title: str | None = None
    distance_from_origin_m: float | None = None


class RouteGeometry(BaseModel):
    type: str = "LineString"
    coordinates: list[list[float]]


class RouteOption(BaseModel):
    id: str
    kind: Literal["recommended", "alternative"]
    route_geometry: RouteGeometry
    distance_m: float
    duration_s: float
    safety_score: int
    safety_grade: Literal["A", "B", "C", "D", "E"]
    hazard_points: list[HazardPoint]
    danger_reports: list[RouteDangerReport]


class RouteResponse(BaseModel):
    routes: list[RouteOption]


class GeocodeItem(BaseModel):
    name: str
    lat: float
    lng: float
