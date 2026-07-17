import asyncio

import httpx
import pytest

from app.services import google_places_service


def _fake_response(json_body: dict, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=json_body,
        request=httpx.Request("POST", google_places_service.PLACES_API_URL),
    )


@pytest.fixture(autouse=True)
def _clear_cache():
    google_places_service._cache.clear()
    yield
    google_places_service._cache.clear()


def test_search_places_returns_geocode_results(monkeypatch) -> None:
    captured: dict = {}

    async def fake_request_with_retry(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = kwargs.get("headers")
        captured["json"] = kwargs.get("json")
        return _fake_response(
            {
                "places": [
                    {
                        "displayName": {"text": "長崎市役所", "languageCode": "ja"},
                        "formattedAddress": "日本、〒850-8685 長崎県長崎市桜町2-22",
                        "location": {"latitude": 32.7448, "longitude": 129.8737},
                    }
                ]
            }
        )

    monkeypatch.setattr(google_places_service, "request_with_retry", fake_request_with_retry)
    monkeypatch.setattr(google_places_service.settings, "google_maps_api_key", "test-key")

    results = asyncio.run(google_places_service.search_places("長崎市役所", 5))

    assert len(results) == 1
    assert results[0].latitude == 32.7448
    assert results[0].longitude == 129.8737
    assert "長崎市役所" in results[0].name
    assert "桜町" in results[0].name

    assert captured["method"] == "POST"
    assert captured["url"] == google_places_service.PLACES_API_URL
    assert captured["headers"]["X-Goog-Api-Key"] == "test-key"
    assert captured["headers"]["X-Goog-FieldMask"] == google_places_service.FIELD_MASK
    assert captured["json"]["textQuery"] == "長崎市役所"
    assert captured["json"]["languageCode"] == "ja"
    assert captured["json"]["regionCode"] == "JP"
    assert captured["json"]["pageSize"] == 5


def test_search_places_returns_empty_list_when_no_places(monkeypatch) -> None:
    async def fake_request_with_retry(method, url, **kwargs):
        return _fake_response({})

    monkeypatch.setattr(google_places_service, "request_with_retry", fake_request_with_retry)
    monkeypatch.setattr(google_places_service.settings, "google_maps_api_key", "test-key")

    results = asyncio.run(google_places_service.search_places("存在しない場所xyz"))

    assert results == []


def test_search_places_uses_cache_for_repeated_query(monkeypatch) -> None:
    call_count = {"n": 0}

    async def fake_request_with_retry(method, url, **kwargs):
        call_count["n"] += 1
        return _fake_response(
            {
                "places": [
                    {
                        "displayName": {"text": "長崎駅"},
                        "location": {"latitude": 32.7503, "longitude": 129.8777},
                    }
                ]
            }
        )

    monkeypatch.setattr(google_places_service, "request_with_retry", fake_request_with_retry)
    monkeypatch.setattr(google_places_service.settings, "google_maps_api_key", "test-key")

    first = asyncio.run(google_places_service.search_places("長崎駅", 5))
    second = asyncio.run(google_places_service.search_places("長崎駅", 5))

    assert first == second
    assert call_count["n"] == 1


def test_search_places_propagates_http_error(monkeypatch) -> None:
    async def fake_request_with_retry(method, url, **kwargs):
        return _fake_response({"error": {"message": "invalid key"}}, status_code=400)

    monkeypatch.setattr(google_places_service, "request_with_retry", fake_request_with_retry)
    monkeypatch.setattr(google_places_service.settings, "google_maps_api_key", "test-key")

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(google_places_service.search_places("長崎"))
