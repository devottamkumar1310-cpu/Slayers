import httpx
import logging
from typing import List
from app.core.config import settings
from app.services.providers.base import AssetSearchProvider, DiscoveredAssetCandidate

logger = logging.getLogger("slayers.unsplash")

class UnsplashProvider(AssetSearchProvider):
    @property
    def name(self) -> str:
        return "Unsplash"

    async def search(self, query: str, asset_type: str, limit: int = 5) -> List[DiscoveredAssetCandidate]:
        results: List[DiscoveredAssetCandidate] = []
        if not settings.UNSPLASH_ACCESS_KEY:
            return results

        headers = {"Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"https://api.unsplash.com/search/photos?query={query}&per_page={limit}"
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    for item in data.get("results", []):
                        user = item.get("user", {})
                        results.append(DiscoveredAssetCandidate(
                            title=item.get("description") or item.get("alt_description") or f"Unsplash: {query}",
                            source="Unsplash",
                            source_url=item.get("links", {}).get("html", "https://unsplash.com"),
                            asset_url=item.get("urls", {}).get("regular"),
                            thumbnail_url=item.get("urls", {}).get("small"),
                            asset_type="image",
                            license_info=f"Unsplash License (Free Commercial Use, credit {user.get('name', 'photographer')})",
                            raw_metadata=item
                        ))
        except Exception as e:
            logger.error(f"Error querying Unsplash provider for '{query}': {e}")

        return results
