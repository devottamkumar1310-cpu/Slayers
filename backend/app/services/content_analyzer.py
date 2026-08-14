import re
import json
import logging
from typing import List, Dict, Any
from app.core.config import settings

logger = logging.getLogger("slayers.content_analyzer")

class ContentAnalyzer:
    """Analyzes scripts/transcripts into scenes and initial visual intents."""

    async def analyze(self, source_text: str) -> List[Dict[str, Any]]:
        source_text = source_text.strip()
        if not source_text:
            return []

        # 1. Try Gemini API if key is configured
        if settings.GEMINI_API_KEY:
            try:
                gemini_res = await self._analyze_with_gemini(source_text)
                if gemini_res and len(gemini_res) > 0:
                    return gemini_res
            except Exception as e:
                logger.warning(f"Gemini analysis failed, falling back to rule-based engine: {e}")

        # 2. Heuristic NLP Segmentation Engine (Fast, local, robust fallback)
        return self._heuristic_segmentation(source_text)

    async def _analyze_with_gemini(self, text: str) -> List[Dict[str, Any]]:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
You are the SLAYERS visual analysis engine for video editing.
Segment the following video script/transcript into distinct narrative scenes (typically 2-4 sentences per scene).

For each scene, output a JSON object with:
- sequence: integer starting at 1
- start_time: string timestamp e.g. "00:00"
- end_time: string timestamp e.g. "00:08"
- text: exact narration text for this segment
- scene_description: visual context summary of what is discussed
- visual_intent: one of [stock_footage, product_ui, website, screenshot, person, location, news_reference, historical, data_visualization, diagram, illustration, screen_recording, logo, document, abstract_broll, no_visual_required]
- importance: "high", "medium", or "low"

Script to analyze:
\"\"\"
{text}
\"\"\"

Return ONLY a valid JSON array of objects without markdown formatting or commentary.
"""
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        
        # Clean markdown codeblocks if wrapped
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(json)?\n?", "", raw_text)
            raw_text = re.sub(r"\n?```$", "", raw_text)

        parsed = json.loads(raw_text)
        if isinstance(parsed, list) and len(parsed) > 0:
            return parsed
        return []

    def _heuristic_segmentation(self, text: str) -> List[Dict[str, Any]]:
        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 1. Check for timestamped lines e.g. "00:00 Intro text" or "[00:15] ..."
        timestamp_pattern = r'(?:^|\n)(?:\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?)\s*[-:]?\s*(.+?)(?=(?:\n\[?\d{1,2}:\d{2})|$)'
        ts_matches = re.findall(timestamp_pattern, text, re.DOTALL)
        
        raw_paragraphs = []
        if len(ts_matches) >= 2:
            for ts, content in ts_matches:
                if content.strip():
                    raw_paragraphs.append(content.strip())
        else:
            # 2. Check for numbered lines e.g. "1. ..." or "Scene 1: ..."
            numbered_pattern = r'(?:^|\n)(?:(?:Scene\s*)?\d+[\.:\)]\s*)(.+?)(?=(?:\n(?:Scene\s*)?\d+[\.:\)])|$)'
            num_matches = re.findall(numbered_pattern, text, re.DOTALL | re.IGNORECASE)
            if len(num_matches) >= 2:
                for content in num_matches:
                    if content.strip():
                        raw_paragraphs.append(content.strip())

        if not raw_paragraphs:
            # Split by double/single newlines
            raw_paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        if len(raw_paragraphs) < 2:
            # Split sentences using punctuation
            sentences = re.split(r'(?<=[.!?])\s+', text)
            raw_paragraphs = []
            chunk = []
            for s in sentences:
                if s.strip():
                    chunk.append(s.strip())
                if len(chunk) >= 2:
                    raw_paragraphs.append(" ".join(chunk))
                    chunk = []
            if chunk:
                raw_paragraphs.append(" ".join(chunk))

        if not raw_paragraphs and text.strip():
            raw_paragraphs = [text.strip()]

        segments = []
        current_seconds = 0
        
        # Comprehensive intent detection rules
        intent_rules = [
            (r'\b(ui|interface|dashboard|app|tool|software|screen|click|button|feature|toggle|menu|settings)\b', 'product_ui'),
            (r'\b(website|site|url|page|online|browser|domain|landing page)\b', 'website'),
            (r'\b(chart|graph|statistic|data|metric|percentage|percent|increase|growth|number|revenue|kpi|analytics)\b', 'data_visualization'),
            (r'\b(logo|brand|icon|symbol|company|trademark)\b', 'logo'),
            (r'\b(developer|coder|person|engineer|team|founder|ceo|speaker|user|customer|audience)\b', 'person'),
            (r'\b(history|historical|past|century|decade|vintage|ancient|archive|origin)\b', 'historical'),
            (r'\b(news|headline|report|article|press|breaking|announcement|media)\b', 'news_reference'),
            (r'\b(diagram|architecture|flowchart|structure|system|pipeline|database|infrastructure)\b', 'diagram'),
            (r'\b(document|paper|pdf|contract|file|whitepaper|report|guide)\b', 'document'),
            (r'\b(illustration|drawing|cartoon|sketch|render|concept art|vector)\b', 'illustration'),
            (r'\b(recording|walkthrough|screencast|live demo|demo video)\b', 'screen_recording'),
            (r'\b(city|office|building|world|location|country|headquarters|lab|studio)\b', 'location'),
        ]

        for idx, paragraph in enumerate(raw_paragraphs, start=1):
            word_count = len(paragraph.split())
            duration_secs = max(5, int(word_count / 2.5))
            
            start_min, start_sec = divmod(current_seconds, 60)
            end_min, end_sec = divmod(current_seconds + duration_secs, 60)
            
            start_str = f"{start_min:02d}:{start_sec:02d}"
            end_str = f"{end_min:02d}:{end_sec:02d}"
            
            current_seconds += duration_secs
            
            # Detect visual intent
            detected_intent = 'stock_footage'
            for pattern, intent in intent_rules:
                if re.search(pattern, paragraph, re.IGNORECASE):
                    detected_intent = intent
                    break

            scene_desc = f"Visual representation of: {paragraph[:80]}..."
            if len(paragraph) <= 80:
                scene_desc = f"Visual representation of: {paragraph}"

            importance = "high" if detected_intent in ("product_ui", "data_visualization", "logo") or idx == 1 else "medium"

            segments.append({
                "sequence": idx,
                "start_time": start_str,
                "end_time": end_str,
                "text": paragraph,
                "scene_description": scene_desc,
                "visual_intent": detected_intent,
                "importance": importance
            })

        return segments
