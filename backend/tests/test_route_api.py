import httpx
from fastapi.testclient import TestClient

from app.api import route as route_api
from app.main import app
from app.models.route import HazardPoint, RoutePoint, RouteResult

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def _fake_route_points(from_lat, from_lng, to_lat, to_lng) -> RouteResult:
    return RouteResult(
        points=[
            RoutePoint(latitude=from_lat, longitude=from_lng),
            RoutePoint(latitude=32.7524, longitude=129.8752),
            RoutePoint(latitude=32.7557, longitude=129.8726),
            RoutePoint(latitude=32.7581, longitude=129.8708),
            RoutePoint(latitude=to_lat, longitude=to_lng),
        ],
        distance_m=1250,
        duration_s=900,
    )


def test_create_route_returns_route_geometry_hazards_and_danger_reports(monkeypatch) -> None:
    async def fake_get_route(from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> RouteResult:
        return _fake_route_points(from_lat, from_lng, to_lat, to_lng)

    async def fake_analyze_hazards(route_points) -> list[HazardPoint]:
        return [
            HazardPoint(
                id="hazard-1",
                title="本河内交差点",
                latitude=32.7524,
                longitude=129.8752,
                risk_score=5,
                risk_factors=["歩道なし", "事故多発（3件）"],
                accident_count=3,
                osm_tags={"highway": "primary", "sidewalk": "none"},
                distance_from_origin_m=350.0,
            )
        ]

    monkeypatch.setattr(route_api, "get_route", fake_get_route)
    monkeypatch.setattr(route_api, "analyze_hazards", fake_analyze_hazards)
    monkeypatch.setattr(route_api, "find_danger_reports_along_route", lambda route, buffer_m: [])

    response = client.post(
        "/api/route",
        json={
            "origin": {"lat": 32.7503, "lng": 129.8777, "address": "長崎市立〇〇小学校"},
            "destination": {"lat": 32.7601, "lng": 129.869, "address": "〇〇町1-2-3"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route_geometry"]["type"] == "LineString"
    assert body["route_geometry"]["coordinates"][0] == [129.8777, 32.7503]
    assert body["distance_m"] == 1250
    assert body["duration_s"] == 900
    assert len(body["hazard_points"]) == 1
    assert body["hazard_points"][0]["risk_score"] == 5
    assert body["danger_reports"] == []


def test_create_route_returns_503_when_routing_service_unavailable(monkeypatch) -> None:
    async def failing_get_route(*args, **kwargs):
        raise httpx.HTTPError("connection failed")

    monkeypatch.setattr(route_api, "get_route", failing_get_route)

    response = client.post(
        "/api/route",
        json={
            "origin": {"lat": 32.7503, "lng": 129.8777},
            "destination": {"lat": 32.7601, "lng": 129.869},
        },
    )

    assert response.status_code == 503


def test_create_route_returns_404_when_no_route_found(monkeypatch) -> None:
    async def no_route(*args, **kwargs):
        raise ValueError("ルートが見つかりませんでした")

    monkeypatch.setattr(route_api, "get_route", no_route)

    response = client.post(
        "/api/route",
        json={
            "origin": {"lat": 32.7503, "lng": 129.8777},
            "destination": {"lat": 32.7601, "lng": 129.869},
        },
    )

    assert response.status_code == 404


def test_create_route_still_returns_response_when_hazard_analysis_fails(monkeypatch) -> None:
    async def fake_get_route(from_lat, from_lng, to_lat, to_lng) -> RouteResult:
        return _fake_route_points(from_lat, from_lng, to_lat, to_lng)

    async def failing_analyze_hazards(route_points):
        raise RuntimeError("boom")

    monkeypatch.setattr(route_api, "get_route", fake_get_route)
    monkeypatch.setattr(route_api, "analyze_hazards", failing_analyze_hazards)
    monkeypatch.setattr(route_api, "find_danger_reports_along_route", lambda route, buffer_m: [])

    response = client.post(
        "/api/route",
        json={
            "origin": {"lat": 32.7503, "lng": 129.8777},
            "destination": {"lat": 32.7601, "lng": 129.869},
        },
    )

    assert response.status_code == 200
    assert response.json()["hazard_points"] == []


def test_geocode_returns_list_of_items(monkeypatch) -> None:
    from app.models.route import GeocodeResult

    async def fake_search_places(query: str, limit: int = 5):
        return [GeocodeResult(name="長崎市役所", latitude=32.7448, longitude=129.8737)]

    monkeypatch.setattr(route_api, "search_places", fake_search_places)

    response = client.get("/api/geocode", params={"q": "長崎市役所", "limit": 5})

    assert response.status_code == 200
    body = response.json()
    assert body == [{"name": "長崎市役所", "lat": 32.7448, "lng": 129.8737}]


def test_geocode_returns_empty_list_when_no_results(monkeypatch) -> None:
    async def fake_search_places(query: str, limit: int = 5):
        return []

    monkeypatch.setattr(route_api, "search_places", fake_search_places)

    response = client.get("/api/geocode", params={"q": "存在しない場所xyz"})

    assert response.status_code == 200
    assert response.json() == []


def test_geocode_returns_503_when_service_unavailable(monkeypatch) -> None:
    async def failing_search_places(query: str, limit: int = 5):
        raise httpx.HTTPError("connection failed")

    monkeypatch.setattr(route_api, "search_places", failing_search_places)

    response = client.get("/api/geocode", params={"q": "長崎"})

    assert response.status_code == 503
