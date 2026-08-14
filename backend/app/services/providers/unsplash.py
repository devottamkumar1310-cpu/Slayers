"""
Unsplash provider — requires UNSPLASH_ACCESS_KEY.
Returns high-resolution photos under the Unsplash License.
"""
import logging
from typing import List
import httpx
from app.core.config import settings
from app.services.providers.base import AssetSearchProvider, DiscoveredAssetCandidate

logger = logging.getLogger("slayers.unsplash")


class UnsplashProvider(AssetSearchProvider):
    @property
    def name(self) -> str:
        return "Unsplash"

    @property
    def is_configured(self) -> bool:
        return bool(settings.UNSPLASH_ACCESS_KEY)

    async def search(self, query: str, asset_type: str, limit: int = 5) -> List[DiscoveredAssetCandidate]:
        results: List[DiscoveredAssetCandidate] = []
        if not self.is_configured:
            return results

        headers = {"Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}"}
        capped = min(limit, 30)

        try:
            async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
                res = await client.get(
                    "https://api.unsplash.com/search/photos",
                    params={"query": query, "per_page": capped},
                    headers=headers,
                )
                if res.status_code == 429:
                    logger.warning("Unsplash rate-limited on query '%s'", query)
                    return results
                if res.status_code == 401:
                    logger.error("Unsplash access key is invalid or expired")
                    return results
                if res.status_code != 200:
                    logger.warning("Unsplash returned HTTP %s for query '%s'", res.status_code, query)
                    return results

                for item in res.json().get("results", []):
                    urls = item.get("urls", {})
                    asset_url = urls.get("regular") or urls.get("full", "")
                    if not asset_url or not asset_url.startswith("http"):
                        continue

                    user = item.get("user", {})
                    username = user.get("username", "photographer")
                    full_name = user.get("name", username)
                    title = item.get("description") or item.get("alt_description") or f"Unsplash photo by {full_name}"

                    results.append(DiscoveredAssetCandidate(
                        title=title[:200],
                        source="Unsplash",
                        source_url=item.get("links", {}).get("html", "https://unsplash.com"),
                        asset_url=asset_url,
                        thumbnail_url=urls.get("small"),
                        asset_type="image",
                        license_info=f"Unsplash License — Free Commercial Use (Credit: {full_name})",
                        license_url="https://unsplash.com/license",
                        usage_status="provider_license",
                        provider_id=f"unsplash:{item.get('id')}",
                        raw_metadata={"id": item.get("id"), "user": username, "width": item.get("width"), "height": item.get("height")},
                    ))
        except httpx.TimeoutException:
            logger.warning("Unsplash timed out for query '%s'", query)
        except httpx.RequestError as e:
            logger.warning("Unsplash network error for query '%s': %s", query, e)
        except Exception as e:
            logger.error("Unsplash unexpected error for query '%s': %s", query, e, exc_info=True)

        return results
