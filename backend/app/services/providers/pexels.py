"""
Pexels provider — requires PEXELS_API_KEY.
Returns photos and videos under the Pexels License (free commercial use).
"""
import logging
from typing import List
import httpx
from app.core.config import settings
from app.services.providers.base import AssetSearchProvider, DiscoveredAssetCandidate

logger = logging.getLogger("slayers.pexels")

_VIDEO_TYPES = {"stock_footage", "screen_recording", "video"}


class PexelsProvider(AssetSearchProvider):
    @property
    def name(self) -> str:
        return "Pexels"

    @property
    def is_configured(self) -> bool:
        return bool(settings.PEXELS_API_KEY)

    async def search(self, query: str, asset_type: str, limit: int = 5) -> List[DiscoveredAssetCandidate]:
        results: List[DiscoveredAssetCandidate] = []
        if not self.is_configured:
            return results

        headers = {"Authorization": settings.PEXELS_API_KEY}
        capped = min(limit, 10)

        try:
            async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
                if asset_type in _VIDEO_TYPES:
                    url = f"https://api.pexels.com/videos/search"
                    res = await client.get(url, params={"query": query, "per_page": capped}, headers=headers)
                    if res.status_code == 429:
                        logger.warning("Pexels rate-limited on query '%s'", query)
                        return results
                    if res.status_code == 401:
                        logger.error("Pexels API key is invalid or expired")
                        return results
                    if res.status_code == 200:
                        for vid in res.json().get("videos", []):
                            vfiles = vid.get("video_files", [])
                            asset_url = vfiles[0].get("link") if vfiles else vid.get("url", "")
                            if not asset_url or not asset_url.startswith("http"):
                                continue
                            results.append(DiscoveredAssetCandidate(
                                title=f"Pexels Video — {query}",
                                source="Pexels",
                                source_url=vid.get("url", "https://pexels.com"),
                                asset_url=asset_url,
                                thumbnail_url=vid.get("image"),
                                asset_type="video",
                                license_info="Pexels License — Free Commercial Use, No Attribution Required",
                                license_url="https://www.pexels.com/license/",
                                usage_status="provider_license",
                                provider_id=f"pexels:video:{vid.get('id')}",
                                raw_metadata={"id": vid.get("id"), "width": vid.get("width"), "height": vid.get("height")},
                            ))
                else:
                    url = "https://api.pexels.com/v1/search"
                    res = await client.get(url, params={"query": query, "per_page": capped}, headers=headers)
                    if res.status_code == 429:
                        logger.warning("Pexels rate-limited on query '%s'", query)
                        return results
                    if res.status_code == 401:
                        logger.error("Pexels API key is invalid or expired")
                        return results
                    if res.status_code == 200:
                        for photo in res.json().get("photos", []):
                            src = photo.get("src", {})
                            asset_url = src.get("large") or src.get("original", "")
                            if not asset_url or not asset_url.startswith("http"):
                                continue
                            results.append(DiscoveredAssetCandidate(
                                title=f"Pexels Photo by {photo.get('photographer', 'Unknown')} — {query}",
                                source="Pexels",
                                source_url=photo.get("url", "https://pexels.com"),
                                asset_url=asset_url,
                                thumbnail_url=src.get("medium"),
                                asset_type="image",
                                license_info="Pexels License — Free Commercial Use, No Attribution Required",
                                license_url="https://www.pexels.com/license/",
                                usage_status="provider_license",
                                provider_id=f"pexels:photo:{photo.get('id')}",
                                raw_metadata={"id": photo.get("id"), "photographer": photo.get("photographer")},
                            ))
        except httpx.TimeoutException:
            logger.warning("Pexels timed out for query '%s'", query)
        except httpx.RequestError as e:
            logger.warning("Pexels network error for query '%s': %s", query, e)
        except Exception as e:
            logger.error("Pexels unexpected error for query '%s': %s", query, e, exc_info=True)

        return results
