import httpx

from app.models.route import GeocodeResult

# 無料のOpenStreetMap Nominatim API。ゼンリンのジオコーディングAPI取得後はこちらに差し替える。
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "school-route-safety-mvp/1.0"


async def search_places(query: str, limit: int = 5) -> list[GeocodeResult]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": limit},
            headers={"User-Agent": USER_AGENT},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()

    return [
        GeocodeResult(
            name=item["display_name"],
            latitude=float(item["lat"]),
            longitude=float(item["lon"]),
        )
        for item in data
    ]
