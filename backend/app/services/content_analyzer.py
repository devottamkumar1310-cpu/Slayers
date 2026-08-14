"""
Content Analyzer — Step 1 of the SLAYERS pipeline.

Responsibilities:
- Accepts raw script / transcript / text
- Returns a list of normalized ContentSegment dicts
- Tries Gemini first (with retry + JSON repair); falls back to heuristic engine
- All output is validated against the SegmentSchema before returning

Heuristic engine handles:
  - Timestamped lines  (00:00, [00:15], etc.)
  - Numbered lists     (1. ..., Scene 3: ...)
  - Double-newline paragraphs
  - Single-sentence splitting

Intent detection covers 14 visual categories.
"""
from __future__ import annotations

import re
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, field_validator
from app.core.config import settings

logger = logging.getLogger("slayers.content_analyzer")

# ── Valid intent categories ───────────────────────────────────────────────────
VALID_INTENTS = {
    "stock_footage", "product_ui", "website", "screenshot", "person",
    "location", "news_reference", "historical", "data_visualization",
    "diagram", "illustration", "screen_recording", "logo", "document",
    "abstract_broll", "no_visual_required",
}
VALID_IMPORTANCES = {"high", "medium", "low"}
_TIME_RE = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")


class SegmentSchema(BaseModel):
    """Validates and normalizes a single segment dict."""
    sequence: int
    start_time: str = "00:00"
    end_time: str = "00:05"
    text: str
    scene_description: str = ""
    visual_intent: str = "stock_footage"
    importance: str = "medium"

    @field_validator("visual_intent")
    @classmethod
    def coerce_intent(cls, v: str) -> str:
        return v if v in VALID_INTENTS else "stock_footage"

    @field_validator("importance")
    @classmethod
    def coerce_importance(cls, v: str) -> str:
        return v if v in VALID_IMPORTANCES else "medium"

    @field_validator("text")
    @classmethod
    def require_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Segment text must not be empty")
        return v


# ── Heuristic intent rules (ordered: first match wins) ───────────────────────
_INTENT_RULES: List[tuple] = [
    # highest specificity first
    (r"\b(screencast|walkthrough|live demo|demo video|screen recording)\b",          "screen_recording"),
    (r"\b(ui|interface|dashboard|app|tool|software|click|button|feature|toggle|menu|settings|plugin|extension)\b",  "product_ui"),
    (r"\b(website|site|url|page|online|browser|domain|landing page|homepage|webapp)\b", "website"),
    (r"\b(chart|graph|metric|percentage|percent|revenue|kpi|analytics|statistic|growth rate|data)\b", "data_visualization"),
    (r"\b(architecture|flowchart|system diagram|pipeline|infrastructure|database schema|er diagram)\b", "diagram"),
    (r"\b(logo|brand|icon|trademark|wordmark|symbol)\b",                             "logo"),
    (r"\b(screenshot|screen capture|print screen)\b",                               "screenshot"),
    (r"\b(document|whitepaper|pdf|report|contract|guide|manual)\b",                 "document"),
    (r"\b(illustration|drawing|cartoon|sketch|concept art|vector|render)\b",        "illustration"),
    (r"\b(news|headline|breaking|press release|announcement|media coverage)\b",     "news_reference"),
    (r"\b(history|historical|archive|past|vintage|ancient|century|decade|origin)\b", "historical"),
    (r"\b(developer|engineer|designer|founder|ceo|person|team|user|customer|speaker|researcher)\b", "person"),
    (r"\b(city|office|building|campus|country|location|headquarters|studio|lab|workplace)\b", "location"),
]

# Words per second reading speed for heuristic timestamps
_WPS = 2.5


class ContentAnalyzer:
    """Analyzes scripts/transcripts into structured content segments."""

    async def analyze(self, source_text: str) -> List[Dict[str, Any]]:
        source_text = source_text.strip()
        if not source_text:
            return []

        # Truncate if too long
        if len(source_text) > settings.MAX_SOURCE_TEXT_LENGTH:
            source_text = source_text[: settings.MAX_SOURCE_TEXT_LENGTH]
            logger.warning("Source text truncated to %d chars", settings.MAX_SOURCE_TEXT_LENGTH)

        # ── Try Gemini (with retry) ───────────────────────────────────────────
        if settings.GEMINI_API_KEY and settings.AI_PROVIDER != "heuristic":
            for attempt in range(2):
                try:
                    segments = await self._analyze_with_gemini(source_text)
                    if segments:
                        logger.info("Gemini segmentation produced %d segments", len(segments))
                        return segments
                except Exception as e:
                    logger.warning("Gemini attempt %d failed: %s", attempt + 1, e)
                    if attempt == 0:
                        await asyncio.sleep(1.5)

        # ── Heuristic fallback ────────────────────────────────────────────────
        logger.info("Using heuristic segmentation engine")
        return self._heuristic_segmentation(source_text)

    # ── Gemini path ───────────────────────────────────────────────────────────
    async def _analyze_with_gemini(self, text: str) -> List[Dict[str, Any]]:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = (
            "You are the SLAYERS Visual Analysis Engine for video editing.\n"
            "Segment the following script into 3–8 distinct narrative scenes "
            "(typically 2–4 sentences per scene).\n\n"
            "For each scene output a JSON object with exactly these fields:\n"
            "  sequence (int, starting at 1)\n"
            "  start_time (\"MM:SS\")\n"
            "  end_time   (\"MM:SS\")\n"
            "  text       (exact narration text)\n"
            "  scene_description (visual summary, ≤120 chars)\n"
            f"  visual_intent (one of: {', '.join(sorted(VALID_INTENTS))})\n"
            "  importance (\"high\" | \"medium\" | \"low\")\n\n"
            "Return ONLY a valid JSON array — no markdown, no commentary.\n\n"
            f'Script:\n"""\n{text}\n"""'
        )

        response = model.generate_content(prompt)
        raw = response.text.strip()
        raw = re.sub(r"^```(?:json)?\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            raise ValueError("Gemini did not return a JSON array")

        return self._validate_segments(parsed)

    # ── Heuristic engine ──────────────────────────────────────────────────────
    def _heuristic_segmentation(self, text: str) -> List[Dict[str, Any]]:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        paragraphs = self._split_into_paragraphs(text)
        return self._validate_segments(self._paragraphs_to_dicts(paragraphs))

    def _split_into_paragraphs(self, text: str) -> List[str]:
        # 1. Timestamped lines: "00:00 Intro..." or "[01:15] ..."
        ts_pattern = re.compile(
            r"(?:^|\n)\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*[-:]?\s*(.+?)(?=\n\[?\d{1,2}:\d{2}|$)",
            re.DOTALL,
        )
        ts_matches = ts_pattern.findall(text)
        if len(ts_matches) >= 2:
            return [c.strip() for _, c in ts_matches if c.strip()]

        # 2. Numbered entries: "1. ...", "Scene 2: ..."
        num_pattern = re.compile(
            r"(?:^|\n)(?:(?:Scene\s*)?\d+[.:\)]\s*)(.+?)(?=\n(?:Scene\s*)?\d+[.:\)]|$)",
            re.DOTALL | re.IGNORECASE,
        )
        num_matches = num_pattern.findall(text)
        if len(num_matches) >= 2:
            return [m.strip() for m in num_matches if m.strip()]

        # 3. Double-newline paragraphs
        paras = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
        if len(paras) >= 2:
            return paras

        # 4. Single-newline lines
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if len(lines) >= 2:
            return lines

        # 5. Sentence chunking (every 2 sentences)
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks, buf = [], []
        for s in sentences:
            if s.strip():
                buf.append(s.strip())
            if len(buf) >= 2:
                chunks.append(" ".join(buf))
                buf = []
        if buf:
            chunks.append(" ".join(buf))
        if chunks:
            return chunks

        return [text.strip()]

    def _paragraphs_to_dicts(self, paragraphs: List[str]) -> List[Dict[str, Any]]:
        result = []
        current_secs = 0
        capped = paragraphs[: settings.MAX_SEGMENTS]

        for idx, para in enumerate(capped, start=1):
            words = len(para.split())
            duration = max(4, int(words / _WPS))
            s_min, s_sec = divmod(current_secs, 60)
            e_min, e_sec = divmod(current_secs + duration, 60)
            current_secs += duration

            intent = self._detect_intent(para)
            importance = "high" if (intent in ("product_ui", "data_visualization", "logo") or idx == 1) else "medium"
            desc = para[:120] + ("…" if len(para) > 120 else "")

            result.append({
                "sequence": idx,
                "start_time": f"{s_min:02d}:{s_sec:02d}",
                "end_time":   f"{e_min:02d}:{e_sec:02d}",
                "text": para,
                "scene_description": f"Visual for: {desc}",
                "visual_intent": intent,
                "importance": importance,
            })
        return result

    def _detect_intent(self, text: str) -> str:
        for pattern, intent in _INTENT_RULES:
            if re.search(pattern, text, re.IGNORECASE):
                return intent
        return "stock_footage"

    # ── Validation ────────────────────────────────────────────────────────────
    def _validate_segments(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        validated = []
        for i, seg in enumerate(raw, start=1):
            try:
                obj = SegmentSchema(
                    sequence=seg.get("sequence", i),
                    start_time=seg.get("start_time", "00:00"),
                    end_time=seg.get("end_time", "00:05"),
                    text=seg.get("text", ""),
                    scene_description=seg.get("scene_description", ""),
                    visual_intent=seg.get("visual_intent", "stock_footage"),
                    importance=seg.get("importance", "medium"),
                )
                validated.append(obj.model_dump())
            except Exception as e:
                logger.warning("Skipping invalid segment at index %d: %s", i, e)
        return validated
