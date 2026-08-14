"""
Wikimedia Commons provider — zero-API-key fallback.

Returns CC/Public Domain assets from Wikimedia's MediaWiki API.
License is extracted from extmetadata and never fabricated.
"""
import re
import logging
from typing import List
import httpx
from app.services.providers.base import AssetSearchProvider, DiscoveredAssetCandidate
from app.core.config import settings

logger = logging.getLogger("slayers.wikimedia")

_STRIP_HTML = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return _STRIP_HTML.sub("", text).strip()


class WikimediaProvider(AssetSearchProvider):
    @property
    def name(self) -> str:
        return "Wikimedia Commons"

    async def search(self, query: str, asset_type: str, limit: int = 5) -> List[DiscoveredAssetCandidate]:
        results: List[DiscoveredAssetCandidate] = []
        try:
            params = {
                "action": "query",
                "generator": "search",
                "gsrsearch": f"File:{query}",
                "gsrlimit": min(limit, 10),
                "prop": "imageinfo",
                "iiprop": "url|mime|extmetadata|size",
                "format": "json",
            }
            headers = {"User-Agent": "SLAYERS-VisualResearchApp/1.0 (https://github.com/devottamkumar1310-cpu/Slayers)"}

            async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    "https://commons.wikimedia.org/w/api.php",
                    params=params,
                    headers=headers,
                )
                if response.status_code != 200:
                    logger.warning("Wikimedia returned HTTP %s for query '%s'", response.status_code, query)
                    return results

                data = response.json()
                pages = data.get("query", {}).get("pages", {})

                for page_id, page in pages.items():
                    title = page.get("title", "Wikimedia Asset").replace("File:", "").strip()
                    imageinfo_list = page.get("imageinfo", [])
                    if not imageinfo_list:
                        continue

                    info = imageinfo_list[0]
                    asset_url = info.get("url", "")
                    if not asset_url or not asset_url.startswith("http"):
                        continue

                    thumb_url = info.get("thumburl") or asset_url
                    desc_url = info.get("descriptionurl") or f"https://commons.wikimedia.org/wiki/File:{title.replace(' ', '_')}"

                    ext = info.get("extmetadata", {})
                    license_short = ext.get("LicenseShortName", {}).get("value", "")
                    license_url_val = ext.get("LicenseUrl", {}).get("value", "")
                    artist = _clean(ext.get("Artist", {}).get("value", "Wikimedia Contributor"))

                    # Determine usage status
                    ls_lower = license_short.lower()
                    if "public domain" in ls_lower or "cc0" in ls_lower:
                        usage_status = "public_domain"
                    elif "cc" in ls_lower or "creative commons" in ls_lower:
                        usage_status = "cc_licensed"
                    else:
                        usage_status = "verify_manually"

                    mime = info.get("mime", "")
                    detected_type = "video" if "video" in mime else "image"

                    results.append(DiscoveredAssetCandidate(
                        title=title[:200],
                        source="Wikimedia Commons",
                        source_url=desc_url,
                        asset_url=asset_url,
                        thumbnail_url=thumb_url,
                        asset_type=detected_type,
                        license_info=f"{license_short or 'Creative Commons'} (Author: {artist[:60]})",
                        license_url=license_url_val or None,
                        usage_status=usage_status,
                        provider_id=f"wikimedia:{page_id}",
                        raw_metadata={"page_id": page_id, "mime": mime, "artist": artist},
                    ))

        except httpx.TimeoutException:
            logger.warning("Wikimedia timed out for query '%s'", query)
        except httpx.RequestError as e:
            logger.warning("Wikimedia network error for query '%s': %s", query, e)
        except Exception as e:
            logger.error("Wikimedia unexpected error for query '%s': %s", query, e, exc_info=True)

        return results
