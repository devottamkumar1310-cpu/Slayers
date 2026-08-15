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
from app.services.entity_extraction import (
    content_terms,
    build_search_query,
    primary_entity,
)

logger = logging.getLogger("slayers.visual_intent")

VALID_PRIORITIES = {"high", "medium", "low"}


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

        # Entity recovery and query construction live in entity_extraction; see
        # that module for why the previous istitle()-based approach discarded
        # GitHub / OpenAI / AI and produced document-only search results.
        entity = primary_entity(text)
        subject = entity or " ".join(content_terms(text, count=2)) or "technology"

        req = self._build_requirement(intent, subject, text)
        results = [req] if req else []

        # Secondary B-roll for scenes whose primary asset is very specific.
        if intent in ("product_ui", "logo", "website", "data_visualization"):
            broll_subject = " ".join(content_terms(text, count=2)) or subject
            results.append({
                "asset_type": "stock_footage",
                "description": f"Supporting B-roll for: {broll_subject}",
                "search_query": build_search_query(text, "stock_footage"),
                "priority": "low",
                "reason": "Secondary B-roll for scene pacing.",
            })

        return self._validate_requirements(results)

    def _build_requirement(self, intent: str, subject: str, text: str) -> Dict[str, Any]:
        """
        Build the primary requirement for a segment.

        Descriptions and reasons are human-facing copy; the search_query is
        always produced by build_search_query so that every intent gets the
        short, entity-led form that providers actually match on.
        """
        p = subject or "technology"
        copy: Dict[str, tuple] = {
            "product_ui": (
                f"UI or dashboard screenshot of {p}",
                "high",
                "Narration describes specific product functionality.",
            ),
            "screen_recording": (
                f"Screen recording or walkthrough of {p}",
                "high",
                "Narration calls for live product demonstration.",
            ),
            "website": (
                f"Official landing page or website for {p}",
                "high",
                "Script references an online platform or destination.",
            ),
            "logo": (
                f"High-resolution logo or brand mark for {p}",
                "high",
                "Brand identity required for scene.",
            ),
            "screenshot": (
                f"Screenshot showing {p} in use",
                "high",
                "Visual proof of product feature.",
            ),
            "data_visualization": (
                f"Chart or graph showing metrics related to {p}",
                "high",
                "Reinforces statistical or metric claims in narration.",
            ),
            "diagram": (
                f"Architecture or flow diagram for {p}",
                "high",
                "Explains technical structure or pipeline.",
            ),
            "news_reference": (
                f"News or press coverage about {p}",
                "medium",
                "Provides journalistic credibility for the claim.",
            ),
            "historical": (
                f"Archival or historical image related to {p}",
                "medium",
                "Sets chronological context for narration.",
            ),
            "document": (
                f"Document, report or whitepaper on {p}",
                "medium",
                "Provides written reference material for scene.",
            ),
            "illustration": (
                f"Illustration or concept art for {p}",
                "medium",
                "Adds visual appeal or explanatory metaphor.",
            ),
            "person": (
                f"Photo or footage of {p}",
                "medium",
                "Humanises the subject or team referenced.",
            ),
            "location": (
                f"Photo or footage of {p}",
                "medium",
                "Establishes physical setting referenced in narration.",
            ),
        }

        description, priority, reason = copy.get(
            intent,
            (f"B-roll footage for: {p}", "medium", "Background B-roll during narration."),
        )
        resolved_intent = intent if intent in copy else "stock_footage"

        return {
            "asset_type": resolved_intent,
            "description": description,
            "search_query": build_search_query(text, resolved_intent),
            "priority": priority,
            "reason": reason,
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
