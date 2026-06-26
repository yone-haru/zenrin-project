from fastapi.testclient import TestClient

from app.api import route as route_api
from app.main import app
from app.models.route import RoutePoint, RouteResult


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_route_returns_route_geometry_and_hazards(monkeypatch) -> None:
    async def fake_get_route(from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> RouteResult:
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

    monkeypatch.setattr(route_api, "get_route", fake_get_route)

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
    assert len(body["hazard_points"]) == 3
    assert body["hazard_points"][0]["risk_score"] == 5
