import httpx
import logging
import re
from typing import List
from app.services.providers.base import AssetSearchProvider, DiscoveredAssetCandidate

logger = logging.getLogger("slayers.web_search")

class WebSearchProvider(AssetSearchProvider):
    @property
    def name(self) -> str:
        return "Web & Product Reference Engine"

    async def search(self, query: str, asset_type: str, limit: int = 5) -> List[DiscoveredAssetCandidate]:
        results: List[DiscoveredAssetCandidate] = []
        try:
            # Clean query for domain / entity lookup
            clean_name = re.sub(r'( official| website| interface| logo| product| ui)', '', query, flags=re.IGNORECASE).strip()
            domain_guess = clean_name.lower().replace(" ", "") + ".com"

            # 1. Official Logo / Brand asset via Clearbit & Google Favicons
            logo_url = f"https://logo.clearbit.com/{domain_guess}"
            fav_url = f"https://www.google.com/s2/favicons?domain={domain_guess}&sz=128"
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                try:
                    head_res = await client.head(logo_url, follow_redirects=True)
                    if head_res.status_code == 200 and 'image' in head_res.headers.get('content-type', ''):
                        results.append(DiscoveredAssetCandidate(
                            title=f"{clean_name} Official Brand Asset / Logo",
                            source="Official Web Brand Asset",
                            source_url=f"https://{domain_guess}",
                            asset_url=logo_url,
                            thumbnail_url=fav_url,
                            asset_type="logo" if asset_type == "logo" else "image",
                            license_info="Trademarked Brand / Official Reference (Editorial / Product Context)",
                            raw_metadata={"domain": domain_guess}
                        ))
                except Exception as e:
                    logger.warning(f"Clearbit check failed for {domain_guess}: {e}")

            # 2. Query Wikipedia API for official product/company overview & infobox image
            wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{clean_name.replace(' ', '_')}"
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(wiki_url)
                if res.status_code == 200:
                    data = res.json()
                    title = data.get("title", clean_name)
                    extract = data.get("extract", "")
                    thumbnail = data.get("thumbnail", {}).get("source")
                    page_url = data.get("content_urls", {}).get("desktop", {}).get("page", f"https://en.wikipedia.org/wiki/{clean_name}")
                    
                    if thumbnail:
                        results.append(DiscoveredAssetCandidate(
                            title=f"{title} Official Reference & Context Image",
                            source="Wikipedia Reference DB",
                            source_url=page_url,
                            asset_url=thumbnail,
                            thumbnail_url=thumbnail,
                            asset_type="product_ui" if asset_type == "product_ui" else "image",
                            license_info="Creative Commons / Public Domain Reference",
                            raw_metadata={"extract": extract[:200]}
                        ))
        except Exception as e:
            logger.error(f"Error in WebSearchProvider for '{query}': {e}")

        return results
