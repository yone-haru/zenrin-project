import asyncio
import time
from collections import OrderedDict

from app.core.config import settings
from app.core.http import request_with_retry
from app.models.route import GeocodeResult
from app.services import google_places_service

# 無料のOpenStreetMap Nominatim API。ゼンリンのジオコーディングAPI取得後はこちらに差し替える。
# 利用ポリシー上、クライアント側で最低1秒間隔のレート制御を行う。
# GOOGLE_MAPS_API_KEY 設定時はGoogle Places API (New) にディスパッチする（下部 search_places 参照）。
_CACHE_MAX_SIZE = 256
_cache: "OrderedDict[tuple[str, int], list[GeocodeResult]]" = OrderedDict()
_rate_lock = asyncio.Lock()
_last_request_at = 0.0


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


async def _rate_limit() -> None:
    global _last_request_at
    async with _rate_lock:
        elapsed = time.monotonic() - _last_request_at
        wait = settings.nominatim_min_interval_s - elapsed
        if wait > 0:
            await asyncio.sleep(wait)
        _last_request_at = time.monotonic()


def _is_google_configured() -> bool:
    return bool(settings.google_maps_api_key)


async def search_places(query: str, limit: int = 5) -> list[GeocodeResult]:
    """地点検索のプロバイダディスパッチャ。

    `GOOGLE_MAPS_API_KEY` 設定時はGoogle Places API (New)、未設定時は既存のNominatim実装を使う。
    """
    if _is_google_configured():
        return await google_places_service.search_places(query, limit)
    return await _search_places_nominatim(query, limit)


async def _search_places_nominatim(query: str, limit: int = 5) -> list[GeocodeResult]:
    cache_key = (query, limit)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    await _rate_limit()

    params = {
        "q": query,
        "format": "json",
        "limit": limit,
        "accept-language": "ja",
    }
    if settings.nominatim_country_codes:
        params["countrycodes"] = settings.nominatim_country_codes

    response = await request_with_retry(
        "GET",
        settings.nominatim_url,
        params=params,
    )
    response.raise_for_status()
    data = response.json()

    results = [
        GeocodeResult(
            name=item["display_name"],
            latitude=float(item["lat"]),
            longitude=float(item["lon"]),
        )
        for item in data
    ]
    _cache_set(cache_key, results)
    return results
