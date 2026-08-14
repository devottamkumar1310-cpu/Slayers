import logging
import asyncio
from typing import List, Dict, Any
from app.services.providers.base import AssetSearchProvider, DiscoveredAssetCandidate
from app.services.providers.wikimedia import WikimediaProvider
from app.services.providers.pexels import PexelsProvider
from app.services.providers.unsplash import UnsplashProvider
from app.services.providers.web_search import WebSearchProvider
from app.services.relevance_scorer import RelevanceScorer

logger = logging.getLogger("slayers.asset_discovery")

class AssetDiscoveryEngine:
    """Discovers and ranks assets across multiple providers concurrently."""

    def __init__(self):
        self.providers: List[AssetSearchProvider] = [
            WikimediaProvider(),
            WebSearchProvider(),
            PexelsProvider(),
            UnsplashProvider(),
        ]
        self.scorer = RelevanceScorer()

    async def _search_provider_safe(
        self,
        provider: AssetSearchProvider,
        query: str,
        asset_type: str,
        limit: int
    ) -> List[DiscoveredAssetCandidate]:
        try:
            return await provider.search(query, asset_type, limit=limit)
        except Exception as e:
            logger.error(f"Provider '{provider.name}' search error for query '{query}': {e}")
            return []

    async def discover_for_requirement(
        self,
        requirement: Dict[str, Any],
        segment_text: str,
        limit_per_provider: int = 4
    ) -> List[Dict[str, Any]]:
        query = requirement.get("search_query", "")
        asset_type = requirement.get("asset_type", "stock_footage")
        
        # Run all provider searches concurrently in parallel
        tasks = [
            self._search_provider_safe(p, query, asset_type, limit_per_provider)
            for p in self.providers
        ]
        results_nested = await asyncio.gather(*tasks, return_exceptions=False)

        candidates: List[DiscoveredAssetCandidate] = []
        for res_list in results_nested:
            if isinstance(res_list, list):
                candidates.extend(res_list)

        # Process and score discovered assets
        processed_assets = []
        seen_urls = set()

        for cand in candidates:
            if not cand.asset_url or cand.asset_url in seen_urls:
                continue
            seen_urls.add(cand.asset_url)

            score, usage_notes, status = self.scorer.score(cand, requirement, segment_text)
            
            processed_assets.append({
                "title": cand.title,
                "source": cand.source,
                "source_url": cand.source_url,
                "asset_url": cand.asset_url,
                "thumbnail_url": cand.thumbnail_url or cand.asset_url,
                "asset_type": cand.asset_type,
                "relevance_score": score,
                "license_info": cand.license_info,
                "usage_notes": usage_notes,
                "status": status,
                "metadata_json": cand.raw_metadata or {}
            })

        # Sort by relevance score descending
        processed_assets.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Ensure top item is marked as 'recommended' and remaining as 'alternative'
        if processed_assets:
            processed_assets[0]["status"] = "recommended"
            for item in processed_assets[1:]:
                if item["status"] == "recommended":
                    item["status"] = "alternative"

        return processed_assets
