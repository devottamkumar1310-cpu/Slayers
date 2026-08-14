import re
import json
import logging
from typing import Dict, Any, List
from app.core.config import settings

logger = logging.getLogger("slayers.visual_intent")

class VisualIntentEngine:
    """Generates precise Asset Requirements for content segments."""

    async def generate_requirements(self, segment: Dict[str, Any]) -> List[Dict[str, Any]]:
        text = segment.get("text", "")
        intent = segment.get("visual_intent", "stock_footage")
        
        # 1. Try Gemini API if key is present
        if settings.GEMINI_API_KEY:
            try:
                gemini_reqs = await self._generate_with_gemini(segment)
                if gemini_reqs and len(gemini_reqs) > 0:
                    return gemini_reqs
            except Exception as e:
                logger.warning(f"Gemini requirement generation failed, using rule engine: {e}")

        # 2. Rule-Based Visual Requirement Generation
        return self._heuristic_requirements(segment)

    async def _generate_with_gemini(self, segment: Dict[str, Any]) -> List[Dict[str, Any]]:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
You are SLAYERS Visual Intent Engine.
Analyze the following script segment and generate 1-2 precise visual asset requirements for a video editor.

IMPORTANT DISTINCTION:
Distinguish clearly between generic stock footage (e.g. "developer coding at desk") and specific product/website footage (e.g. "OpenAI ChatGPT interface" or "GitHub Copilot dashboard").

Segment text: "{segment.get('text')}"
Detected intent category: "{segment.get('visual_intent')}"

Return a JSON array of objects with fields:
- asset_type: string (one of: stock_footage, product_ui, website, screenshot, person, location, news_reference, historical, data_visualization, diagram, illustration, screen_recording, logo, document, abstract_broll, no_visual_required)
- description: clear, specific description of the visual needed
- search_query: optimal search query keywords for stock or web engines
- priority: "high", "medium", or "low"
- reason: rationale connecting narration to this specific visual requirement

Return ONLY valid JSON array without commentary.
"""
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(json)?\n?", "", raw_text)
            raw_text = re.sub(r"\n?```$", "", raw_text)

        parsed = json.loads(raw_text)
        if isinstance(parsed, list) and len(parsed) > 0:
            return parsed
        return []

    def _heuristic_requirements(self, segment: Dict[str, Any]) -> List[Dict[str, Any]]:
        text = segment.get("text", "")
        intent = segment.get("visual_intent", "stock_footage")
        
        # Extract potential proper nouns / product names / brands
        words = text.split()
        stopwords = {
            "the", "this", "that", "there", "these", "those", "when", "what", "where",
            "how", "with", "from", "they", "their", "your", "today", "here", "also",
            "every", "each", "some", "many", "such", "instead", "another", "our"
        }
        proper_nouns = [
            w.strip(".,!?\"'();:") for w in words
            if w.istitle() and len(w) > 2 and w.lower() not in stopwords
        ]
        
        product_name = " ".join(proper_nouns[:2]) if proper_nouns else ""

        reqs = []

        if intent in ("product_ui", "screenshot", "screen_recording"):
            query_subject = f"{product_name} user interface dashboard" if product_name else "software application interface dashboard"
            reqs.append({
                "asset_type": intent,
                "description": f"Show the actual interface or screen workflow of {product_name or 'the product'} discussed",
                "search_query": query_subject,
                "priority": "high",
                "reason": "Narration directly describes specific product functionality, requiring authentic UI footage."
            })
        elif intent == "website":
            query_subject = f"{product_name} official website page" if product_name else "modern web application homepage"
            reqs.append({
                "asset_type": "website",
                "description": f"Official landing page or website reference for {product_name or 'web platform'}",
                "search_query": query_subject,
                "priority": "high",
                "reason": "Script refers to an online website or digital destination."
            })
        elif intent == "logo":
            query_subject = f"{product_name} official logo" if product_name else "technology brand logo"
            reqs.append({
                "asset_type": "logo",
                "description": f"Official high-resolution vector or transparent logo for {product_name or 'brand'}",
                "search_query": query_subject,
                "priority": "high",
                "reason": "Establishes brand identity and company recognition in scene."
            })
        elif intent == "data_visualization":
            reqs.append({
                "asset_type": "data_visualization",
                "description": f"Data chart, graph, or metrics dashboard showing growth statistics",
                "search_query": f"{product_name} growth data chart statistics" if product_name else "analytics data chart graph",
                "priority": "high",
                "reason": "Visually reinforces statistical claims, metrics, or financial data."
            })
        elif intent == "diagram":
            reqs.append({
                "asset_type": "diagram",
                "description": f"System architecture diagram or flow chart illustrating technical structure",
                "search_query": f"{product_name} system architecture diagram" if product_name else "software system architecture diagram",
                "priority": "high",
                "reason": "Explains underlying technical pipeline or structural relationships."
            })
        elif intent == "news_reference":
            reqs.append({
                "asset_type": "news_reference",
                "description": f"News headline, press release, or media coverage reference",
                "search_query": f"{product_name} press announcement headline" if product_name else "breaking tech news headline",
                "priority": "medium",
                "reason": "Provides journalistic context supporting the narration claim."
            })
        elif intent == "historical":
            reqs.append({
                "asset_type": "historical",
                "description": "Historical footage or archival image establishing timeline context",
                "search_query": f"historical {product_name or 'vintage archive'}",
                "priority": "medium",
                "reason": "Visually roots the narration in past chronological context."
            })
        elif intent == "person":
            query_subject = f"{product_name} portrait" if product_name else "professional engineer at computer"
            reqs.append({
                "asset_type": "person",
                "description": f"Visual reference of {product_name or 'person'} or team working",
                "search_query": query_subject,
                "priority": "medium",
                "reason": "Shows the human subject or team referenced in narration."
            })
        else: # generic abstract B-roll / stock footage
            meaningful_words = [w.strip(".,!?\"'") for w in text.split() if len(w) > 4 and w.lower() not in stopwords]
            query_subject = " ".join(meaningful_words[:3]) if meaningful_words else "modern technology software"
            reqs.append({
                "asset_type": "stock_footage",
                "description": f"High quality cinematic footage supporting theme: {query_subject}",
                "search_query": f"tech {query_subject}",
                "priority": "medium",
                "reason": "Provides engaging background pacing during narration."
            })

        return reqs
