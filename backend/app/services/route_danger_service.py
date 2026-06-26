from app.core.geo import haversine_distance_m
from app.core.storage import load_reports
from app.models.route import RouteDangerReport, RouteResult


def find_danger_reports_along_route(route: RouteResult, buffer_m: float = 30) -> list[RouteDangerReport]:
    """ルート上の各通過点との最短距離がbuffer_m以内の投稿を抽出する。"""
    reports = load_reports()

    results = []
    for report in reports:
        min_distance = min(
            haversine_distance_m(report.latitude, report.longitude, point.latitude, point.longitude)
            for point in route.points
        )
        if min_distance <= buffer_m:
            results.append(RouteDangerReport(report=report, distance_from_route_m=min_distance))

    results.sort(key=lambda item: item.distance_from_route_m)
    return results
