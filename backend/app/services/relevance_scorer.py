import logging
import re
from typing import Dict, Any, Tuple
from app.services.providers.base import DiscoveredAssetCandidate

logger = logging.getLogger("slayers.relevance_scorer")

class RelevanceScorer:
    """Computes a deterministic, explainable relevance score (0-100) for candidate assets."""

    def score(
        self,
        candidate: DiscoveredAssetCandidate,
        requirement: Dict[str, Any],
        segment_text: str
    ) -> Tuple[int, str, str]:
        """
        Returns:
            Tuple of (score [0-100], usage_notes [str], status ['recommended'|'alternative'|'flagged'])
        """
        search_query = requirement.get("search_query", "").lower()
        req_asset_type = requirement.get("asset_type", "stock_footage").lower()
        
        cand_title = candidate.title.lower()
        cand_source = candidate.source.lower()
        cand_type = candidate.asset_type.lower()
        
        # 1. Semantic Relevance (0-30 points)
        # Tokenize words (>2 chars, alphanumeric)
        query_words = set(re.findall(r'\b[a-z0-9]{3,}\b', search_query))
        title_words = set(re.findall(r'\b[a-z0-9]{3,}\b', cand_title))
        
        if query_words:
            overlap = query_words.intersection(title_words)
            # Check partial substring matches as well (e.g. 'chatgpt' in 'chatgpt_logo.png')
            partial_matches = sum(1 for qw in query_words if any(qw in tw for tw in title_words))
            match_count = max(len(overlap), partial_matches)
            semantic_score = min(30, int((match_count / len(query_words)) * 30))
        else:
            semantic_score = 15

        # 2. Visual-Type Match (0-25 points)
        type_score = 15 # baseline
        if req_asset_type in ("product_ui", "screenshot", "website", "logo", "diagram", "data_visualization") and cand_type in ("image", "logo"):
            type_score = 25
        elif req_asset_type in ("stock_footage", "screen_recording", "video") and cand_type == "video":
            type_score = 25
        elif cand_type in ("image", "video"):
            type_score = 20

        # 3. Source Quality (0-20 points)
        source_score = 15
        if "wikimedia" in cand_source or "official" in cand_source:
            source_score = 20
        elif "pexels" in cand_source or "unsplash" in cand_source:
            source_score = 18

        # 4. Query Match (0-15 points)
        query_score = 15 if any(qw in cand_title for qw in query_words) else 8

        # 5. Contextual Match (0-10 points)
        segment_words = set(re.findall(r'\b[a-z0-9]{4,}\b', segment_text.lower()))
        seg_overlap = segment_words.intersection(title_words)
        context_score = min(10, len(seg_overlap) * 4)

        raw_score = semantic_score + type_score + source_score + query_score + context_score
        total_score = min(100, max(15, raw_score))

        # Status & Explainable Rationale
        if total_score >= 80:
            status = "recommended"
            rationale = f"High confidence match ({total_score}/100): Direct keyword alignment with query '{search_query}' and verified visual type."
        elif total_score >= 60:
            status = "alternative"
            rationale = f"Good alternative match ({total_score}/100): Matches core subject context with appropriate media formatting."
        else:
            status = "flagged"
            rationale = f"Contextual candidate ({total_score}/100): Relevant topic reference; check visual framing before export."

        return total_score, rationale, status
