"""
WebSearch provider — no API key required.

Uses:
1. Clearbit Logo API  — to get brand logos
2. Wikipedia REST API — to get article thumbnail + context

Both checks are resilient: connection failures are logged as warnings, not errors.
No fake / guessed URLs are ever injected into results.
"""
import re
import logging
from typing import List
import httpx
from app.services.providers.base import AssetSearchProvider, DiscoveredAssetCandidate
from app.core.config import settings

logger = logging.getLogger("slayers.web_search")

_STRIP_SUFFIX = re.compile(
    r"\b(official|website|interface|logo|product|ui|page|app|software|platform)\b",
    re.IGNORECASE,
)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _domain_from_query(query: str) -> str:
    """Best-effort domain guess from a human-readable query."""
    clean = _STRIP_SUFFIX.sub("", query).strip()
    clean = _NON_ALNUM.sub("", clean.lower())
    return f"{clean}.com" if clean else ""


class WebSearchProvider(AssetSearchProvider):
    @property
    def name(self) -> str:
        return "Web & Brand Reference"

    async def search(self, query: str, asset_type: str, limit: int = 5) -> List[DiscoveredAssetCandidate]:
        results: List[DiscoveredAssetCandidate] = []

        # Derive a clean entity name from the query
        clean_name = _STRIP_SUFFIX.sub("", query).strip() or query
        domain = _domain_from_query(query)

        # ── 1. Clearbit logo (only for logo / product_ui / website intents) ──────
        if asset_type in ("logo", "product_ui", "website", "screenshot") and domain:
            logo_url = f"https://logo.clearbit.com/{domain}"
            fav_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    head = await client.head(logo_url, follow_redirects=True)
                    if head.status_code == 200 and "image" in head.headers.get("content-type", ""):
                        results.append(DiscoveredAssetCandidate(
                            title=f"{clean_name} — Official Brand Logo",
                            source="Clearbit (Brand Asset API)",
                            source_url=f"https://{domain}",
                            asset_url=logo_url,
                            thumbnail_url=fav_url,
                            asset_type="logo",
                            license_info="Trademarked brand asset — editorial / product context only",
                            usage_status="verify_manually",
                            provider_id=f"clearbit:{domain}",
                            raw_metadata={"domain": domain},
                        ))
            except httpx.TimeoutException:
                logger.debug("Clearbit timed out for domain '%s'", domain)
            except httpx.RequestError as e:
                logger.debug("Clearbit request error for domain '%s': %s", domain, e)
            except Exception as e:
                logger.warning("Clearbit unexpected error for domain '%s': %s", domain, e)

        # ── 2. Wikipedia REST API thumbnail ──────────────────────────────────────
        wiki_entity = clean_name.replace(" ", "_")
        try:
            async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
                res = await client.get(
                    f"https://en.wikipedia.org/api/rest_v1/page/summary/{wiki_entity}",
                    headers={"User-Agent": "SLAYERS-VisualResearchApp/1.0"},
                )
                if res.status_code == 200:
                    data = res.json()
                    thumbnail = data.get("thumbnail", {}).get("source")
                    if thumbnail and thumbnail.startswith("http"):
                        title = data.get("title", clean_name)
                        page_url = (
                            data.get("content_urls", {})
                            .get("desktop", {})
                            .get("page", f"https://en.wikipedia.org/wiki/{wiki_entity}")
                        )
                        extract = data.get("extract", "")[:300]
                        results.append(DiscoveredAssetCandidate(
                            title=f"{title} — Wikipedia Reference Image",
                            source="Wikipedia",
                            source_url=page_url,
                            asset_url=thumbnail,
                            thumbnail_url=thumbnail,
                            asset_type="image",
                            license_info="Wikimedia / Creative Commons — see source page for license",
                            usage_status="cc_licensed",
                            provider_id=f"wikipedia:{data.get('pageid', wiki_entity)}",
                            raw_metadata={"pageid": data.get("pageid"), "extract": extract},
                        ))
        except httpx.TimeoutException:
            logger.debug("Wikipedia timed out for entity '%s'", wiki_entity)
        except httpx.RequestError as e:
            logger.debug("Wikipedia request error for entity '%s': %s", wiki_entity, e)
        except Exception as e:
            logger.warning("Wikipedia unexpected error for entity '%s': %s", wiki_entity, e)

        return results
