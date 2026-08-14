"""
Asset Discovery Engine — Step 4 of the SLAYERS pipeline.

- Runs all providers CONCURRENTLY via asyncio.gather
- Each provider failure is isolated (never crashes the pipeline)
- URL and provider-id deduplication before scoring
- Returns assets sorted by relevance_score descending
- Caps result set to MAX_ASSETS_PER_REQUIREMENT
"""
from __future__ import annotations

import logging
import asyncio
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional

from app.core.config import settings
from app.services.providers.base import AssetSearchProvider, DiscoveredAssetCandidate
from app.services.providers.wikimedia import WikimediaProvider
from app.services.providers.pexels import PexelsProvider
from app.services.providers.unsplash import UnsplashProvider
from app.services.providers.web_search import WebSearchProvider
from app.services.relevance_scorer import RelevanceScorer

logger = logging.getLogger("slayers.asset_discovery")


class AssetDiscoveryEngine:
    """Discovers and ranks assets from multiple providers concurrently."""

    def __init__(self) -> None:
        self.providers: List[AssetSearchProvider] = [
            WikimediaProvider(),
            WebSearchProvider(),
            PexelsProvider(),
            UnsplashProvider(),
        ]
        self.scorer = RelevanceScorer()

    # ── Provider execution ────────────────────────────────────────────────────
    async def _search_safe(
        self,
        provider: AssetSearchProvider,
        query: str,
        asset_type: str,
        limit: int,
    ) -> Tuple[str, List[DiscoveredAssetCandidate], Optional[str]]:
        """Returns (provider_name, results, error_message_or_None)."""
        if not provider.is_configured:
            logger.debug("Provider '%s' skipped (not configured)", provider.name)
            return provider.name, [], None
        try:
            results = await asyncio.wait_for(
                provider.search(query, asset_type, limit=limit),
                timeout=settings.PROVIDER_TIMEOUT_SECONDS + 2,
            )
            logger.debug("Provider '%s' returned %d results for '%s'", provider.name, len(results), query)
            return provider.name, results, None
        except asyncio.TimeoutError:
            msg = f"Provider '{provider.name}' timed out for query '{query}'"
            logger.warning(msg)
            return provider.name, [], msg
        except Exception as e:
            msg = f"Provider '{provider.name}' error for query '{query}': {e}"
            logger.error(msg, exc_info=True)
            return provider.name, [], msg

    # ── Main discovery ────────────────────────────────────────────────────────
    async def discover_for_requirement(
        self,
        requirement: Dict[str, Any],
        segment_text: str,
        limit_per_provider: int | None = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Returns
        -------
        (assets, stats)
            assets : list of asset dicts sorted by relevance_score desc
            stats  : dict with per-provider found counts and any warnings
        """
        query = (requirement.get("search_query") or "").strip()
        asset_type = requirement.get("asset_type", "stock_footage")
        per_provider = limit_per_provider or settings.MAX_PROVIDER_RESULTS

        if not query:
            logger.warning("Empty search query for requirement — skipping discovery")
            return [], {}

        # ── Concurrent provider search ────────────────────────────────────────
        tasks = [
            self._search_safe(p, query, asset_type, per_provider)
            for p in self.providers
        ]
        provider_results = await asyncio.gather(*tasks)

        # ── Aggregate + deduplicate ───────────────────────────────────────────
        stats: Dict[str, Any] = {"found": {}, "warnings": []}
        all_candidates: List[DiscoveredAssetCandidate] = []
        seen_urls: set = set()
        seen_provider_ids: set = set()

        for name, candidates, error in provider_results:
            if error:
                stats["warnings"].append(error)
            accepted = 0
            for c in candidates:
                # Deduplicate by URL
                url_key = c.asset_url.lower()
                if url_key in seen_urls:
                    continue
                seen_urls.add(url_key)
                # Deduplicate by provider_id
                if c.provider_id and c.provider_id in seen_provider_ids:
                    continue
                if c.provider_id:
                    seen_provider_ids.add(c.provider_id)
                all_candidates.append(c)
                accepted += 1
            stats["found"][name] = accepted

        # ── Score + sort ──────────────────────────────────────────────────────
        scored: List[Dict[str, Any]] = []
        for cand in all_candidates:
            try:
                score, notes, status = self.scorer.score(cand, requirement, segment_text)
            except Exception as e:
                logger.warning("Scoring error for asset '%s': %s", cand.title[:60], e)
                score, notes, status = 30, "Scoring error — manual review required.", "flagged"

            scored.append({
                "title": cand.title[:500],
                "source": cand.source,
                "source_url": cand.source_url,
                "asset_url": cand.asset_url,
                "thumbnail_url": cand.thumbnail_url or cand.asset_url,
                "asset_type": cand.asset_type,
                "relevance_score": score,
                "license_info": cand.license_info,
                "license_url": cand.license_url,
                "usage_notes": notes,
                "usage_status": cand.usage_status,
                "status": status,
                "provider_id": cand.provider_id,
                "metadata_json": cand.raw_metadata or {},
            })

        scored.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Cap result set
        scored = scored[: settings.MAX_ASSETS_PER_REQUIREMENT]

        # Ensure top item is "recommended" if it cleared alternative threshold
        if scored:
            scored[0]["status"] = "recommended"
            for item in scored[1:]:
                if item["status"] == "recommended":
                    item["status"] = "alternative"

        return scored, stats
