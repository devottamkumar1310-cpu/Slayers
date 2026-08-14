"""
Relevance Scorer — deterministic, explainable scoring for discovered assets.

Score breakdown (max 100):
  Semantic relevance  (0–35)  — token overlap between query and asset title
  Visual type match   (0–25)  — asset_type alignment with requirement type
  Source quality      (0–20)  — provider tier
  Context alignment   (0–20)  — segment text keyword overlap with title

Status thresholds:
  ≥ 80  → recommended
  ≥ 55  → alternative
  <  55  → flagged
"""
from __future__ import annotations

import re
import logging
from typing import Dict, Any, Tuple

from app.services.providers.base import DiscoveredAssetCandidate

logger = logging.getLogger("slayers.relevance_scorer")

# Minimum chars for a token to count (avoids matching noise like "an", "of")
_MIN_TOKEN_LEN = 3

# Asset types that require images vs videos
_IMAGE_INTENTS = frozenset({
    "product_ui", "screenshot", "website", "logo", "diagram",
    "data_visualization", "document", "illustration", "news_reference",
    "historical", "person", "location",
})
_VIDEO_INTENTS = frozenset({"stock_footage", "screen_recording", "video", "abstract_broll"})

# Source tier weights
_SOURCE_TIERS: Dict[str, int] = {
    "wikimedia commons": 20,
    "wikipedia": 18,
    "pexels": 18,
    "unsplash": 17,
    "clearbit (brand asset api)": 16,
    "web & brand reference": 15,
    "official web brand asset": 14,
}


def _tokenize(text: str) -> frozenset:
    return frozenset(
        t for t in re.findall(r"\b[a-z0-9]{%d,}\b" % _MIN_TOKEN_LEN, text.lower())
    )


class RelevanceScorer:
    """Computes a deterministic, fully-explainable relevance score (0–100)."""

    def score(
        self,
        candidate: DiscoveredAssetCandidate,
        requirement: Dict[str, Any],
        segment_text: str,
    ) -> Tuple[int, str, str]:
        """
        Returns
        -------
        (score, usage_notes, status)
            score       : int [0, 100]
            usage_notes : human-readable explanation
            status      : 'recommended' | 'alternative' | 'flagged'
        """
        req_query = requirement.get("search_query", "")
        req_type = requirement.get("asset_type", "stock_footage")

        query_tokens = _tokenize(req_query)
        title_tokens = _tokenize(candidate.title)
        segment_tokens = _tokenize(segment_text)

        # ── 1. Semantic relevance (0–35) ─────────────────────────────────────
        if query_tokens:
            direct_overlap = query_tokens & title_tokens
            # Partial substring matches: e.g. "github" matches "github-copilot"
            partial = sum(
                1 for qt in query_tokens
                if any(qt in tt for tt in title_tokens) and qt not in direct_overlap
            )
            matched = len(direct_overlap) + partial
            semantic = min(35, int((matched / len(query_tokens)) * 35))
        else:
            semantic = 18  # no query → baseline

        # Bonus: if candidate has no query-word overlap but title has related
        # topic words from the segment (partial topical relevance)
        if semantic == 0 and (query_tokens & segment_tokens):
            semantic = 10

        # ── 2. Visual type match (0–25) ───────────────────────────────────────
        cand_type = candidate.asset_type.lower()
        if req_type in _IMAGE_INTENTS and cand_type == "image":
            type_score = 25
        elif req_type in _VIDEO_INTENTS and cand_type == "video":
            type_score = 25
        elif req_type == "logo" and cand_type == "logo":
            type_score = 25
        elif cand_type in ("image", "video"):
            type_score = 15
        else:
            type_score = 10

        # ── 3. Source quality (0–20) ──────────────────────────────────────────
        src_lower = candidate.source.lower()
        source_score = next(
            (v for k, v in _SOURCE_TIERS.items() if k in src_lower),
            13,  # unknown / new source baseline
        )

        # ── 4. Context alignment (0–20) ───────────────────────────────────────
        seg_overlap = segment_tokens & title_tokens
        context_score = min(20, len(seg_overlap) * 4)

        # ── Total ─────────────────────────────────────────────────────────────
        raw = semantic + type_score + source_score + context_score
        total = min(100, max(10, raw))

        # ── Status & rationale ────────────────────────────────────────────────
        breakdown = (
            f"Semantic={semantic}/35, Type={type_score}/25, "
            f"Source={source_score}/20, Context={context_score}/20"
        )
        if total >= 80:
            status = "recommended"
            notes = (
                f"High confidence match ({total}/100). "
                f"Strong keyword alignment with '{req_query}'. {breakdown}"
            )
        elif total >= 55:
            status = "alternative"
            notes = (
                f"Good alternative ({total}/100). "
                f"Core topic matches with suitable media format. {breakdown}"
            )
        else:
            status = "flagged"
            notes = (
                f"Low confidence ({total}/100). "
                f"Topically adjacent — verify visual framing before export. {breakdown}"
            )

        return total, notes, status
