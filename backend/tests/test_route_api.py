import httpx
from fastapi.testclient import TestClient

from app.api import route as route_api
from app.main import app
from app.models.route import HazardPoint, RoutePoint, RouteResult
from app.services.overpass_service import OverpassData

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def _fake_route(from_lat, from_lng, to_lat, to_lng, distance_m=1250, duration_s=900) -> RouteResult:
    return RouteResult(
        points=[
            RoutePoint(latitude=from_lat, longitude=from_lng),
            RoutePoint(latitude=32.7524, longitude=129.8752),
            RoutePoint(latitude=32.7557, longitude=129.8726),
            RoutePoint(latitude=32.7581, longitude=129.8708),
            RoutePoint(latitude=to_lat, longitude=to_lng),
        ],
        distance_m=distance_m,
        duration_s=duration_s,
    )


def _fake_route_points(from_lat, from_lng, to_lat, to_lng) -> RouteResult:
    # 後方互換のための単一ルート版ヘルパー（既存テスト踏襲）
    return _fake_route(from_lat, from_lng, to_lat, to_lng)


def test_create_route_returns_single_route_with_safety_score(monkeypatch) -> None:
    async def fake_get_routes(from_lat, from_lng, to_lat, to_lng) -> list[RouteResult]:
        return [_fake_route(from_lat, from_lng, to_lat, to_lng)]

    async def fake_fetch_shared_road_data(routes):
        return OverpassData()

    async def fake_analyze_hazards(route_points, road_data=None) -> list[HazardPoint]:
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

    monkeypatch.setattr(route_api, "get_routes", fake_get_routes)
    monkeypatch.setattr(route_api, "_fetch_shared_road_data", fake_fetch_shared_road_data)
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
    assert len(body["routes"]) == 1

    route = body["routes"][0]
    assert route["id"] == "r0"
    assert route["kind"] == "recommended"
    assert route["route_geometry"]["type"] == "LineString"
    assert route["route_geometry"]["coordinates"][0] == [129.8777, 32.7503]
    assert route["distance_m"] == 1250
    assert route["duration_s"] == 900
    assert len(route["hazard_points"]) == 1
    assert route["hazard_points"][0]["risk_score"] == 5
    assert route["danger_reports"] == []
    # penalty = 15 (risk_score 5), penalty_per_km = 15*1000/max(1250,500) = 12 -> score 88 -> grade A
    assert route["safety_score"] == 88
    assert route["safety_grade"] == "A"


def test_create_route_orders_alternatives_by_safety_then_recommends_best(monkeypatch) -> None:
    async def fake_get_routes(from_lat, from_lng, to_lat, to_lng) -> list[RouteResult]:
        return [
            _fake_route(from_lat, from_lng, to_lat, to_lng, distance_m=1000, duration_s=800),
            _fake_route(from_lat, from_lng, to_lat, to_lng, distance_m=1500, duration_s=1200),
        ]

    async def fake_fetch_shared_road_data(routes):
        return OverpassData()

    call_count = {"n": 0}

    async def fake_analyze_hazards(route_points, road_data=None) -> list[HazardPoint]:
        call_count["n"] += 1
        # 1本目（call 1）は危険地点多数＝低スコア、2本目（call 2）は危険地点なし＝高スコア
        if call_count["n"] == 1:
            return [
                HazardPoint(
                    id=f"hazard-{call_count['n']}",
                    title="危険区間",
                    latitude=32.7524,
                    longitude=129.8752,
                    risk_score=5,
                    risk_factors=["歩道なし"],
                    accident_count=3,
                    osm_tags={},
                    distance_from_origin_m=100.0,
                )
            ]
        return []

    monkeypatch.setattr(route_api, "get_routes", fake_get_routes)
    monkeypatch.setattr(route_api, "_fetch_shared_road_data", fake_fetch_shared_road_data)
    monkeypatch.setattr(route_api, "analyze_hazards", fake_analyze_hazards)
    monkeypatch.setattr(route_api, "find_danger_reports_along_route", lambda route, buffer_m: [])

    response = client.post(
        "/api/route",
        json={
            "origin": {"lat": 32.7503, "lng": 129.8777},
            "destination": {"lat": 32.7601, "lng": 129.869},
        },
    )

    assert response.status_code == 200
    body = response.json()
    routes = body["routes"]
    assert len(routes) == 2

    # ちょうど1件だけrecommended、それが配列先頭
    kinds = [r["kind"] for r in routes]
    assert kinds.count("recommended") == 1
    assert kinds[0] == "recommended"
    assert routes[0]["id"] == "r0"
    assert routes[1]["id"] == "r1"

    # 危険地点なしの2本目（distance_m=1500）のほうが安全スコアが高いため推奨になる
    assert routes[0]["distance_m"] == 1500
    assert routes[0]["safety_score"] == 100
    assert routes[1]["distance_m"] == 1000
    assert routes[1]["safety_score"] < 100


def test_create_route_calls_overpass_only_once_for_multiple_routes(monkeypatch) -> None:
    async def fake_get_routes(from_lat, from_lng, to_lat, to_lng) -> list[RouteResult]:
        return [
            _fake_route(from_lat, from_lng, to_lat, to_lng, distance_m=1000),
            _fake_route(from_lat, from_lng, to_lat, to_lng, distance_m=1200),
        ]

    fetch_calls = {"n": 0}

    async def fake_fetch_road_data(bbox):
        fetch_calls["n"] += 1
        return OverpassData()

    monkeypatch.setattr(route_api, "get_routes", fake_get_routes)
    monkeypatch.setattr(route_api, "fetch_road_data", fake_fetch_road_data)
    monkeypatch.setattr(route_api, "find_danger_reports_along_route", lambda route, buffer_m: [])

    response = client.post(
        "/api/route",
        json={
            "origin": {"lat": 32.7503, "lng": 129.8777},
            "destination": {"lat": 32.7601, "lng": 129.869},
        },
    )

    assert response.status_code == 200
    assert fetch_calls["n"] == 1


def test_create_route_returns_503_when_routing_service_unavailable(monkeypatch) -> None:
    async def failing_get_routes(*args, **kwargs):
        raise httpx.HTTPError("connection failed")

    monkeypatch.setattr(route_api, "get_routes", failing_get_routes)

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

    monkeypatch.setattr(route_api, "get_routes", no_route)

    response = client.post(
        "/api/route",
        json={
            "origin": {"lat": 32.7503, "lng": 129.8777},
            "destination": {"lat": 32.7601, "lng": 129.869},
        },
    )

    assert response.status_code == 404


def test_create_route_still_returns_response_when_hazard_analysis_fails(monkeypatch) -> None:
    async def fake_get_routes(from_lat, from_lng, to_lat, to_lng) -> list[RouteResult]:
        return [_fake_route(from_lat, from_lng, to_lat, to_lng)]

    async def fake_fetch_shared_road_data(routes):
        return OverpassData()

    async def failing_analyze_hazards(route_points, road_data=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(route_api, "get_routes", fake_get_routes)
    monkeypatch.setattr(route_api, "_fetch_shared_road_data", fake_fetch_shared_road_data)
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
    body = response.json()
    assert body["routes"][0]["hazard_points"] == []
    assert body["routes"][0]["safety_score"] == 100


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
