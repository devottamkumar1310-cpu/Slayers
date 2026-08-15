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

from app.services.entity_extraction import primary_entity
from app.services.intent_policy import provider_affinity, type_compatibility
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
        haystack = f"{candidate.title} {candidate.source_url} {candidate.asset_url}".lower()

        # ── 1. Semantic relevance (0-35) ─────────────────────────────────────
        # Token overlap, plus a bonus when the named entity behind the query
        # actually appears in the asset. An exact entity hit is the strongest
        # signal we have that this is the right subject and not a coincidence
        # of common words.
        if query_tokens:
            direct_overlap = query_tokens & title_tokens
            partial = sum(
                1 for qt in query_tokens
                if any(qt in tt for tt in title_tokens) and qt not in direct_overlap
            )
            matched = len(direct_overlap) + partial
            semantic = min(28, int((matched / len(query_tokens)) * 28))
        else:
            semantic = 14  # no query -> baseline

        if semantic == 0 and (query_tokens & segment_tokens):
            semantic = 8

        # Read the entity from the narration first: the segment text carries
        # natural capitalisation, whereas a search query may arrive lower-cased
        # (from Gemini, or hand-written) and would yield no entity at all.
        entity = primary_entity(segment_text) or primary_entity(req_query) or ""
        entity_hit = False
        if entity:
            parts = [p for p in entity.lower().split() if len(p) >= _MIN_TOKEN_LEN]
            if parts and all(p in haystack for p in parts):
                entity_hit = True
                semantic = min(35, semantic + 7)

        # ── 2. Visual type match (0-25) ───────────────────────────────────────
        # Delegated to intent_policy so providers, discovery and scoring agree.
        # A scanned document scores 0 here against a product-UI requirement.
        compatibility = type_compatibility(req_type, candidate.asset_type)
        type_score = int(round(25 * compatibility))

        # ── 3. Source quality (0-20), intent-aware ────────────────────────────
        src_lower = candidate.source.lower()
        base_tier = next(
            (v for k, v in _SOURCE_TIERS.items() if k in src_lower),
            13,  # unknown / new source baseline
        )
        source_score = max(0, min(20, int(round(base_tier * provider_affinity(req_type, candidate.source)))))

        # ── 4. Context alignment (0-20) ───────────────────────────────────────
        seg_overlap = segment_tokens & title_tokens
        context_score = min(16, len(seg_overlap) * 4)
        # Domain relevance: the entity appearing in the URL means the asset is
        # hosted on / filed under that subject, not merely titled with it.
        if entity_hit and any(
            p in f"{candidate.source_url} {candidate.asset_url}".lower()
            for p in entity.lower().split()
        ):
            context_score = min(20, context_score + 4)

        # ── Total ─────────────────────────────────────────────────────────────
        raw = semantic + type_score + source_score + context_score
        total = min(100, max(10, raw))

        # ── Status & rationale ────────────────────────────────────────────────
        breakdown = (
            f"Semantic={semantic}/35, Type={type_score}/25, "
            f"Source={source_score}/20, Context={context_score}/20"
        )
        mismatch_note = ""
        if compatibility == 0.0:
            mismatch_note = (
                f" Asset kind '{candidate.asset_type}' does not suit a "
                f"'{req_type}' requirement."
            )
        elif compatibility < 1.0:
            mismatch_note = (
                f" Usable substitute: '{candidate.asset_type}' for a "
                f"'{req_type}' slot."
            )

        entity_note = f" Matches '{entity}'." if entity_hit else ""

        if total >= 80:
            status = "recommended"
            notes = (
                f"High confidence match ({total}/100). "
                f"Strong alignment with '{req_query}'.{entity_note}{mismatch_note} {breakdown}"
            )
        elif total >= 55:
            status = "alternative"
            notes = (
                f"Good alternative ({total}/100). "
                f"Core topic matches with suitable media format.{entity_note}{mismatch_note} {breakdown}"
            )
        else:
            status = "flagged"
            notes = (
                f"Low confidence ({total}/100). "
                f"Topically adjacent - verify visual framing before export.{entity_note}{mismatch_note} {breakdown}"
            )

        return total, notes, status
