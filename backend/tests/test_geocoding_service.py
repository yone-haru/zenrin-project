import asyncio

from app.models.route import GeocodeResult
from app.services import geocoding_service


def _dummy_result() -> list[GeocodeResult]:
    return [GeocodeResult(name="長崎駅", latitude=32.7503, longitude=129.8777)]


def test_search_places_dispatches_to_nominatim_when_no_google_key(monkeypatch) -> None:
    monkeypatch.setattr(geocoding_service.settings, "google_maps_api_key", "")

    calls = {"nominatim": 0, "google": 0}

    async def fake_nominatim(*args, **kwargs):
        calls["nominatim"] += 1
        return _dummy_result()

    async def fake_google(*args, **kwargs):
        calls["google"] += 1
        return _dummy_result()

    monkeypatch.setattr(geocoding_service, "_search_places_nominatim", fake_nominatim)
    monkeypatch.setattr(geocoding_service.google_places_service, "search_places", fake_google)

    results = asyncio.run(geocoding_service.search_places("長崎駅"))

    assert len(results) == 1
    assert calls["nominatim"] == 1
    assert calls["google"] == 0


def test_search_places_dispatches_to_google_when_key_set(monkeypatch) -> None:
    monkeypatch.setattr(geocoding_service.settings, "google_maps_api_key", "test-key")

    calls = {"nominatim": 0, "google": 0}

    async def fake_nominatim(*args, **kwargs):
        calls["nominatim"] += 1
        return _dummy_result()

    async def fake_google(*args, **kwargs):
        calls["google"] += 1
        return _dummy_result()

    monkeypatch.setattr(geocoding_service, "_search_places_nominatim", fake_nominatim)
    monkeypatch.setattr(geocoding_service.google_places_service, "search_places", fake_google)

    results = asyncio.run(geocoding_service.search_places("長崎駅"))

    assert len(results) == 1
    assert calls["nominatim"] == 0
    assert calls["google"] == 1
