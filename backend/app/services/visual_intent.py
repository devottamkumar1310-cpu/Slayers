"""
Visual Intent Engine — Step 3 of the SLAYERS pipeline.

For each ContentSegment, generates 1–2 precise AssetRequirement dicts.
Uses Gemini when available, falls back to a rule-based engine.
All output is validated via RequirementSchema before returning.
"""
from __future__ import annotations

import re
import json
import logging
import asyncio
from typing import List, Dict, Any

from pydantic import BaseModel, field_validator
from app.core.config import settings
from app.services.content_analyzer import VALID_INTENTS

logger = logging.getLogger("slayers.visual_intent")

VALID_PRIORITIES = {"high", "medium", "low"}

_STOPWORDS = frozenset({
    "the", "this", "that", "there", "these", "those", "when", "what",
    "where", "how", "with", "from", "they", "their", "your", "today",
    "here", "also", "every", "each", "some", "many", "such", "instead",
    "another", "our", "have", "been", "were", "will", "would", "which",
    "into", "over", "about", "after", "before", "during", "through",
})


class RequirementSchema(BaseModel):
    asset_type: str
    description: str
    search_query: str
    priority: str = "medium"
    reason: str = ""

    @field_validator("asset_type")
    @classmethod
    def coerce_type(cls, v: str) -> str:
        return v.strip() if v.strip() in VALID_INTENTS else "stock_footage"

    @field_validator("priority")
    @classmethod
    def coerce_priority(cls, v: str) -> str:
        return v.strip().lower() if v.strip().lower() in VALID_PRIORITIES else "medium"

    @field_validator("description", "search_query")
    @classmethod
    def require_non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field must not be empty")
        return v[:500]


class VisualIntentEngine:
    """Generates AssetRequirement dicts for each content segment."""

    async def generate_requirements(self, segment: Dict[str, Any]) -> List[Dict[str, Any]]:
        text = segment.get("text", "")
        intent = segment.get("visual_intent", "stock_footage")

        # ── Gemini path ───────────────────────────────────────────────────────
        if settings.GEMINI_API_KEY and settings.AI_PROVIDER != "heuristic":
            for attempt in range(2):
                try:
                    reqs = await self._generate_with_gemini(segment)
                    if reqs:
                        logger.debug("Gemini generated %d requirements for intent=%s", len(reqs), intent)
                        return reqs
                except Exception as e:
                    logger.warning("Gemini requirement gen attempt %d failed: %s", attempt + 1, e)
                    if attempt == 0:
                        await asyncio.sleep(1.5)

        # ── Heuristic fallback ────────────────────────────────────────────────
        return self._heuristic_requirements(segment)

    # ── Gemini ────────────────────────────────────────────────────────────────
    async def _generate_with_gemini(self, segment: Dict[str, Any]) -> List[Dict[str, Any]]:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        valid_types = ", ".join(sorted(VALID_INTENTS))
        prompt = (
            "You are SLAYERS Visual Intent Engine.\n"
            "Analyze the script segment and generate 1–2 precise visual asset requirements.\n\n"
            "DISTINGUISH CLEARLY between:\n"
            "  - Generic stock footage (e.g. 'developer typing at laptop')\n"
            "  - Specific product UI (e.g. 'GitHub Copilot code completion interface')\n\n"
            f'Segment text: "{segment.get("text")}"\n'
            f'Detected intent: "{segment.get("visual_intent")}"\n\n'
            "Return a JSON array of objects with these exact fields:\n"
            f"  asset_type (one of: {valid_types})\n"
            "  description (specific visual description, ≤200 chars)\n"
            "  search_query (optimal search keywords, ≤80 chars)\n"
            "  priority (\"high\" | \"medium\" | \"low\")\n"
            "  reason (brief rationale connecting narration to visual, ≤200 chars)\n\n"
            "Return ONLY valid JSON array — no markdown, no commentary."
        )

        response = model.generate_content(prompt)
        raw = response.text.strip()
        raw = re.sub(r"^```(?:json)?\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            raise ValueError("Gemini returned non-list for requirements")

        return self._validate_requirements(parsed)

    # ── Heuristic engine ──────────────────────────────────────────────────────
    def _heuristic_requirements(self, segment: Dict[str, Any]) -> List[Dict[str, Any]]:
        text = segment.get("text", "")
        intent = segment.get("visual_intent", "stock_footage")

        # Extract likely proper nouns (capitalized words not in stopwords)
        tokens = text.split()
        proper_nouns = [
            t.strip(".,!?\"'();:")
            for t in tokens
            if t.istitle() and len(t) > 2 and t.lower() not in _STOPWORDS
        ]
        product_name = " ".join(proper_nouns[:2]) if proper_nouns else ""

        # Meaningful content words for fallback queries
        content_words = [
            w.strip(".,!?\"'();:")
            for w in tokens
            if len(w) > 4 and w.lower() not in _STOPWORDS
        ]
        content_phrase = " ".join(content_words[:4]) if content_words else "technology"

        req = self._build_requirement(intent, product_name, content_phrase)
        results = [req] if req else []

        # Add a generic B-roll as secondary if primary is very specific
        if intent in ("product_ui", "logo", "website", "data_visualization") and content_words:
            results.append({
                "asset_type": "stock_footage",
                "description": f"Supporting B-roll footage for: {content_phrase}",
                "search_query": f"{content_phrase} technology",
                "priority": "low",
                "reason": "Secondary B-roll for scene pacing.",
            })

        return self._validate_requirements(results)

    def _build_requirement(self, intent: str, product: str, content: str) -> Dict[str, Any]:
        p = product or content or "technology"
        templates: Dict[str, Dict[str, Any]] = {
            "product_ui": {
                "asset_type": "product_ui",
                "description": f"UI/dashboard screenshot of {p}",
                "search_query": f"{p} interface dashboard",
                "priority": "high",
                "reason": "Narration describes specific product functionality.",
            },
            "screen_recording": {
                "asset_type": "screen_recording",
                "description": f"Screen recording or walkthrough of {p}",
                "search_query": f"{p} screencast walkthrough",
                "priority": "high",
                "reason": "Narration calls for live product demonstration.",
            },
            "website": {
                "asset_type": "website",
                "description": f"Official landing page / website for {p}",
                "search_query": f"{p} official website homepage",
                "priority": "high",
                "reason": "Script references an online platform or destination.",
            },
            "logo": {
                "asset_type": "logo",
                "description": f"High-resolution transparent logo for {p}",
                "search_query": f"{p} official logo transparent",
                "priority": "high",
                "reason": "Brand identity required for scene.",
            },
            "screenshot": {
                "asset_type": "screenshot",
                "description": f"Screenshot showing {p} in action",
                "search_query": f"{p} screenshot",
                "priority": "high",
                "reason": "Visual proof of product feature.",
            },
            "data_visualization": {
                "asset_type": "data_visualization",
                "description": f"Chart or graph showing metrics related to {p}",
                "search_query": f"{p} data chart growth statistics",
                "priority": "high",
                "reason": "Reinforces statistical or metric claims in narration.",
            },
            "diagram": {
                "asset_type": "diagram",
                "description": f"System architecture or flow diagram for {p}",
                "search_query": f"{p} architecture diagram flowchart",
                "priority": "high",
                "reason": "Explains technical structure or pipeline.",
            },
            "news_reference": {
                "asset_type": "news_reference",
                "description": f"News headline or press coverage about {p}",
                "search_query": f"{p} news announcement press",
                "priority": "medium",
                "reason": "Provides journalistic credibility for the claim.",
            },
            "historical": {
                "asset_type": "historical",
                "description": f"Archival or historical image related to {p}",
                "search_query": f"historical {p} archive vintage",
                "priority": "medium",
                "reason": "Sets chronological context for narration.",
            },
            "document": {
                "asset_type": "document",
                "description": f"Document, report or whitepaper on {p}",
                "search_query": f"{p} whitepaper report document",
                "priority": "medium",
                "reason": "Provides written reference material for scene.",
            },
            "illustration": {
                "asset_type": "illustration",
                "description": f"Custom illustration or concept art for {p}",
                "search_query": f"{p} illustration concept art vector",
                "priority": "medium",
                "reason": "Adds visual appeal or explanatory metaphor.",
            },
            "person": {
                "asset_type": "person",
                "description": f"Photo or footage of {p or 'professional'} at work",
                "search_query": f"{p or 'software engineer'} professional portrait",
                "priority": "medium",
                "reason": "Humanises the subject or team referenced.",
            },
            "location": {
                "asset_type": "location",
                "description": f"Photo or footage of {p or 'office'} environment",
                "search_query": f"{p or 'tech office'} location workspace",
                "priority": "medium",
                "reason": "Establishes physical setting referenced in narration.",
            },
        }
        if intent in templates:
            return templates[intent]

        # Default: generic stock footage
        return {
            "asset_type": "stock_footage",
            "description": f"Cinematic B-roll footage for: {content}",
            "search_query": f"{content} technology cinematic",
            "priority": "medium",
            "reason": "Background B-roll during narration.",
        }

    # ── Validation ────────────────────────────────────────────────────────────
    def _validate_requirements(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        validated = []
        for i, req in enumerate(raw):
            try:
                obj = RequirementSchema(**req)
                validated.append(obj.model_dump())
            except Exception as e:
                logger.warning("Dropping invalid requirement at index %d: %s", i, e)
        return validated
