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

# Intents for which a scanned document or book is a legitimate result.
# Everything else wants a picture, and gets `filetype:bitmap` added to the
# search so Commons never returns a PDF for it.
_DOCUMENT_FRIENDLY_INTENTS = frozenset({
    "document", "historical", "news_reference", "research", "paper",
})

# Commons ANDs every search term, and the only files matching a long term list
# are documents with a full text layer. Measured: a 5-term query returned 8/8
# PDFs; the same query trimmed to 2-3 terms returned 7-8/8 real images.
_MAX_QUERY_TERMS = 4

# At most this many Commons requests per requirement, so relaxation cannot
# multiply pipeline latency.
_MAX_SEARCH_ATTEMPTS = 2


def _clean(text: str) -> str:
    return _STRIP_HTML.sub("", text).strip()


def build_commons_search(query: str, asset_type: str) -> str:
    """
    Compose the CirrusSearch expression for a requirement.

    Adds `filetype:bitmap` for visual intents so scanned PDFs and DjVu books
    are excluded at the SOURCE rather than filtered out afterwards, and caps
    the term count so the query can still match image metadata.
    """
    terms = [t for t in (query or "").split() if t][:_MAX_QUERY_TERMS]
    expr = " ".join(terms)
    if asset_type not in _DOCUMENT_FRIENDLY_INTENTS:
        expr = f"{expr} filetype:bitmap".strip()
    return expr


def build_search_ladder(query: str, asset_type: str) -> List[str]:
    """
    Progressively broader search expressions, most specific first.

    Because Commons ANDs terms, an intent qualifier can over-constrain a query
    that would otherwise match: measured, "GitHub Copilot interface" returns
    nothing while "GitHub Copilot" returns 8 images. Dropping the trailing term
    recovers those results without weakening the leading entity.
    """
    terms = [t for t in (query or "").split() if t][:_MAX_QUERY_TERMS]
    ladder: List[str] = []
    while terms:
        expr = build_commons_search(" ".join(terms), asset_type)
        if expr and expr not in ladder:
            ladder.append(expr)
        if len(ladder) >= _MAX_SEARCH_ATTEMPTS:
            break
        terms = terms[:-1]
    return ladder or [build_commons_search(query, asset_type)]


class WikimediaProvider(AssetSearchProvider):
    @property
    def name(self) -> str:
        return "Wikimedia Commons"

    async def search(self, query: str, asset_type: str, limit: int = 5) -> List[DiscoveredAssetCandidate]:
        """Walk the search ladder, stopping at the first expression that hits."""
        for expression in build_search_ladder(query, asset_type):
            results = await self._search_once(expression, limit)
            if results:
                return results
        return []

    async def _search_once(self, expression: str, limit: int) -> List[DiscoveredAssetCandidate]:
        results: List[DiscoveredAssetCandidate] = []
        try:
            params = {
                "action": "query",
                "generator": "search",
                "gsrsearch": expression,
                # Namespace 6 is File:. Scoping here rather than prefixing the
                # search string keeps `filetype:` operators working — the old
                # "File:<query>" form silently disabled them.
                "gsrnamespace": 6,
                "gsrlimit": min(limit, 10),
                "prop": "imageinfo",
                "iiprop": "url|mime|extmetadata|size",
                # Ask for a real scaled thumbnail instead of falling back to the
                # full-size original.
                "iiurlwidth": 800,
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
                    logger.warning("Wikimedia returned HTTP %s for '%s'", response.status_code, expression)
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

                    # thumburl is populated by iiurlwidth and, for PDFs/DjVu, is
                    # a rasterised page render rather than the raw document.
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
                    # Classify honestly: a scanned PDF is not an image. Calling
                    # it one let documents earn the full visual-type score.
                    if "video" in mime or "ogg" in mime:
                        detected_type = "video"
                    elif any(d in mime for d in ("pdf", "djvu", "tiff")):
                        detected_type = "document"
                    else:
                        detected_type = "image"

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
            logger.warning("Wikimedia timed out for '%s'", expression)
        except httpx.RequestError as e:
            logger.warning("Wikimedia network error for '%s': %s", expression, e)
        except Exception as e:
            logger.error("Wikimedia unexpected error for '%s': %s", expression, e, exc_info=True)

        return results
