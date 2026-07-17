"""Google Places API (New) Text Search 連携サービス。

`settings.google_maps_api_key` が設定されている場合のみ geocoding_service から呼び出される。
既存のNominatim実装と同じ `GeocodeResult` 契約に変換して返す。
"""

from __future__ import annotations

from collections import OrderedDict

from app.core.config import settings
from app.core.http import request_with_retry
from app.models.route import GeocodeResult

PLACES_API_URL = "https://places.googleapis.com/v1/places:searchText"

FIELD_MASK = "places.displayName,places.formattedAddress,places.location"

_CACHE_MAX_SIZE = 256
_cache: "OrderedDict[tuple[str, int], list[GeocodeResult]]" = OrderedDict()


def _cache_get(key: tuple[str, int]) -> list[GeocodeResult] | None:
    if key not in _cache:
        return None
    _cache.move_to_end(key)
    return _cache[key]


def _cache_set(key: tuple[str, int], value: list[GeocodeResult]) -> None:
    _cache[key] = value
    _cache.move_to_end(key)
    if len(_cache) > _CACHE_MAX_SIZE:
        _cache.popitem(last=False)


def _to_geocode_result(place: dict) -> GeocodeResult:
    display_name = place.get("displayName", {}).get("text", "")
    formatted_address = place.get("formattedAddress")
    name = f"{display_name}（{formatted_address}）" if formatted_address else display_name
    location = place["location"]
    return GeocodeResult(
        name=name,
        latitude=location["latitude"],
        longitude=location["longitude"],
    )


async def search_places(query: str, limit: int = 5) -> list[GeocodeResult]:
    cache_key = (query, limit)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    response = await request_with_retry(
        "POST",
        PLACES_API_URL,
        headers={
            "X-Goog-Api-Key": settings.google_maps_api_key,
            "X-Goog-FieldMask": FIELD_MASK,
            "Content-Type": "application/json",
        },
        json={
            "textQuery": query,
            "languageCode": "ja",
            "regionCode": "JP",
            "pageSize": limit,
        },
    )
    response.raise_for_status()
    data = response.json()

    results = [_to_geocode_result(place) for place in data.get("places", [])]
    _cache_set(cache_key, results)
    return results
