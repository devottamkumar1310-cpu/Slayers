import httpx
import logging
from typing import List
from app.core.config import settings
from app.services.providers.base import AssetSearchProvider, DiscoveredAssetCandidate

logger = logging.getLogger("slayers.pexels")

class PexelsProvider(AssetSearchProvider):
    @property
    def name(self) -> str:
        return "Pexels"

    async def search(self, query: str, asset_type: str, limit: int = 5) -> List[DiscoveredAssetCandidate]:
        results: List[DiscoveredAssetCandidate] = []
        if not settings.PEXELS_API_KEY:
            return results

        headers = {"Authorization": settings.PEXELS_API_KEY}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Search videos if stock_footage requested, otherwise photos
                if asset_type in ("stock_footage", "screen_recording", "video"):
                    url = f"https://api.pexels.com/videos/search?query={query}&per_page={limit}"
                    res = await client.get(url, headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        for vid in data.get("videos", []):
                            video_files = vid.get("video_files", [])
                            asset_url = video_files[0].get("link") if video_files else vid.get("url")
                            results.append(DiscoveredAssetCandidate(
                                title=f"Pexels Video: {query} (ID {vid.get('id')})",
                                source="Pexels",
                                source_url=vid.get("url"),
                                asset_url=asset_url,
                                thumbnail_url=vid.get("image"),
                                asset_type="video",
                                license_info="Pexels License (Free Commercial Use, No Attribution Required)",
                                raw_metadata=vid
                            ))
                else:
                    url = f"https://api.pexels.com/v1/search?query={query}&per_page={limit}"
                    res = await client.get(url, headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        for photo in data.get("photos", []):
                            results.append(DiscoveredAssetCandidate(
                                title=f"Pexels Photo: {query} by {photo.get('photographer')}",
                                source="Pexels",
                                source_url=photo.get("url"),
                                asset_url=photo.get("src", {}).get("large"),
                                thumbnail_url=photo.get("src", {}).get("medium"),
                                asset_type="image",
                                license_info="Pexels License (Free Commercial Use, No Attribution Required)",
                                raw_metadata=photo
                            ))
        except Exception as e:
            logger.error(f"Error querying Pexels provider for '{query}': {e}")

        return results
