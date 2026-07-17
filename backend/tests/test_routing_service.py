import asyncio

from app.models.route import RoutePoint, RouteResult
from app.services import google_routing_service, routing_service


def _dummy_route() -> RouteResult:
    return RouteResult(
        points=[RoutePoint(latitude=32.7503, longitude=129.8777)],
        distance_m=1000.0,
        duration_s=750.0,
    )


def test_get_routes_dispatches_to_osrm_when_no_google_key(monkeypatch) -> None:
    monkeypatch.setattr(routing_service.settings, "google_maps_api_key", "")

    calls = {"osrm": 0, "google": 0}

    async def fake_osrm(*args, **kwargs):
        calls["osrm"] += 1
        return [_dummy_route()]

    async def fake_google(*args, **kwargs):
        calls["google"] += 1
        return [_dummy_route()]

    monkeypatch.setattr(routing_service, "_get_routes_osrm", fake_osrm)
    monkeypatch.setattr(google_routing_service, "get_routes", fake_google)

    results = asyncio.run(routing_service.get_routes(32.7503, 129.8777, 32.7601, 129.869))

    assert len(results) == 1
    assert calls["osrm"] == 1
    assert calls["google"] == 0


def test_get_routes_dispatches_to_google_when_key_set(monkeypatch) -> None:
    monkeypatch.setattr(routing_service.settings, "google_maps_api_key", "test-key")

    calls = {"osrm": 0, "google": 0}

    async def fake_osrm(*args, **kwargs):
        calls["osrm"] += 1
        return [_dummy_route()]

    async def fake_google(*args, **kwargs):
        calls["google"] += 1
        return [_dummy_route()]

    monkeypatch.setattr(routing_service, "_get_routes_osrm", fake_osrm)
    monkeypatch.setattr(routing_service.google_routing_service, "get_routes", fake_google)

    results = asyncio.run(routing_service.get_routes(32.7503, 129.8777, 32.7601, 129.869))

    assert len(results) == 1
    assert calls["osrm"] == 0
    assert calls["google"] == 1
