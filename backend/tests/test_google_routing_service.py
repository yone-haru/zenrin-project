import asyncio

import httpx
import pytest

from app.services import google_routing_service


def _fake_response(json_body: dict, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=json_body,
        request=httpx.Request("POST", google_routing_service.ROUTES_API_URL),
    )


def test_get_routes_returns_multiple_routes_from_geojson_linestring(monkeypatch) -> None:
    captured: dict = {}

    async def fake_request_with_retry(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = kwargs.get("headers")
        captured["json"] = kwargs.get("json")
        return _fake_response(
            {
                "routes": [
                    {
                        "distanceMeters": 1250,
                        "duration": "900s",
                        "polyline": {
                            "geoJsonLinestring": {
                                "type": "LineString",
                                "coordinates": [
                                    [129.8777, 32.7503],
                                    [129.8752, 32.7524],
                                    [129.869, 32.7601],
                                ],
                            }
                        },
                    },
                    {
                        "distanceMeters": 1500,
                        "duration": "1100.5s",
                        "polyline": {
                            "geoJsonLinestring": {
                                "type": "LineString",
                                "coordinates": [
                                    [129.8777, 32.7503],
                                    [129.869, 32.7601],
                                ],
                            }
                        },
                    },
                ]
            }
        )

    monkeypatch.setattr(google_routing_service, "request_with_retry", fake_request_with_retry)
    monkeypatch.setattr(google_routing_service.settings, "google_maps_api_key", "test-key")

    results = asyncio.run(
        google_routing_service.get_routes(32.7503, 129.8777, 32.7601, 129.869)
    )

    assert len(results) == 2

    assert results[0].distance_m == 1250
    assert results[0].duration_s == 900.0
    assert len(results[0].points) == 3
    # GeoJSON [lng, lat] -> RoutePoint(latitude, longitude)
    assert results[0].points[0].latitude == 32.7503
    assert results[0].points[0].longitude == 129.8777

    # "1100.5s" のような小数付きdurationも正しくfloat秒に変換される
    assert results[1].duration_s == 1100.5

    assert captured["method"] == "POST"
    assert captured["url"] == google_routing_service.ROUTES_API_URL
    assert captured["headers"]["X-Goog-Api-Key"] == "test-key"
    assert captured["headers"]["X-Goog-FieldMask"] == google_routing_service.FIELD_MASK
    assert captured["json"]["travelMode"] == "WALK"
    assert captured["json"]["computeAlternativeRoutes"] is True
    assert captured["json"]["polylineEncoding"] == "GEO_JSON_LINESTRING"


def test_get_routes_caps_at_max_alternative_routes(monkeypatch) -> None:
    def _route(distance: float) -> dict:
        return {
            "distanceMeters": distance,
            "duration": "100s",
            "polyline": {
                "geoJsonLinestring": {
                    "type": "LineString",
                    "coordinates": [[129.8777, 32.7503], [129.869, 32.7601]],
                }
            },
        }

    async def fake_request_with_retry(method, url, **kwargs):
        return _fake_response({"routes": [_route(1000), _route(1100), _route(1200), _route(1300)]})

    monkeypatch.setattr(google_routing_service, "request_with_retry", fake_request_with_retry)
    monkeypatch.setattr(google_routing_service.settings, "google_maps_api_key", "test-key")

    results = asyncio.run(
        google_routing_service.get_routes(32.7503, 129.8777, 32.7601, 129.869)
    )

    assert len(results) == google_routing_service.MAX_ALTERNATIVE_ROUTES


def test_get_routes_raises_value_error_when_no_routes(monkeypatch) -> None:
    async def fake_request_with_retry(method, url, **kwargs):
        return _fake_response({"routes": []})

    monkeypatch.setattr(google_routing_service, "request_with_retry", fake_request_with_retry)
    monkeypatch.setattr(google_routing_service.settings, "google_maps_api_key", "test-key")

    with pytest.raises(ValueError):
        asyncio.run(google_routing_service.get_routes(32.7503, 129.8777, 32.7601, 129.869))


def test_get_routes_propagates_http_error(monkeypatch) -> None:
    async def fake_request_with_retry(method, url, **kwargs):
        return _fake_response({"error": {"message": "invalid key"}}, status_code=400)

    monkeypatch.setattr(google_routing_service, "request_with_retry", fake_request_with_retry)
    monkeypatch.setattr(google_routing_service.settings, "google_maps_api_key", "test-key")

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(google_routing_service.get_routes(32.7503, 129.8777, 32.7601, 129.869))
