import httpx
import logging
from typing import List, Optional
from app.services.providers.base import AssetSearchProvider, DiscoveredAssetCandidate

logger = logging.getLogger("slayers.wikimedia")

class WikimediaProvider(AssetSearchProvider):
    @property
    def name(self) -> str:
        return "Wikimedia Commons"

    async def search(self, query: str, asset_type: str, limit: int = 5) -> List[DiscoveredAssetCandidate]:
        results: List[DiscoveredAssetCandidate] = []
        try:
            url = "https://commons.wikimedia.org/w/api.php"
            params = {
                "action": "query",
                "generator": "search",
                "gsrsearch": f"File:{query}",
                "gsrlimit": limit,
                "prop": "imageinfo",
                "iiprop": "url|mime|extmetadata|size",
                "format": "json"
            }
            headers = {
                "User-Agent": "SLAYERS-VisualResearchApp/1.0 (https://github.com/slayers-app)"
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params, headers=headers)
                if response.status_code != 200:
                    logger.warning(f"Wikimedia API returned status {response.status_code}")
                    return results

                data = response.json()
                pages = data.get("query", {}).get("pages", {})
                
                for page_id, page in pages.items():
                    title = page.get("title", "Wikimedia Asset").replace("File:", "")
                    imageinfo_list = page.get("imageinfo", [])
                    if not imageinfo_list:
                        continue
                    
                    info = imageinfo_list[0]
                    asset_url = info.get("url")
                    thumb_url = info.get("thumburl", asset_url)
                    source_url = info.get("descriptionurl", f"https://commons.wikimedia.org/wiki/File:{title.replace(' ', '_')}")
                    
                    extmetadata = info.get("extmetadata", {})
                    license_name = extmetadata.get("LicenseShortName", {}).get("value", "Creative Commons / Public Domain")
                    artist = extmetadata.get("Artist", {}).get("value", "Wikimedia Contributor")
                    
                    # Clean artist string HTML tags if present
                    if "<" in artist and ">" in artist:
                        import re
                        artist = re.sub(r'<[^>]+>', '', artist)
                    
                    mime = info.get("mime", "")
                    detected_type = "video" if "video" in mime or title.endswith((".ogv", ".webm", ".mp4")) else "image"
                    
                    results.append(DiscoveredAssetCandidate(
                        title=title[:100],
                        source="Wikimedia Commons",
                        source_url=source_url,
                        asset_url=asset_url,
                        thumbnail_url=thumb_url,
                        asset_type=detected_type,
                        license_info=f"{license_name} (Author: {artist[:40]})",
                        raw_metadata={"page_id": page_id, "extmetadata": extmetadata}
                    ))
        except Exception as e:
            logger.error(f"Error querying Wikimedia provider for '{query}': {e}")

        return results
