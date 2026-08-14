import pytest
from app.services.visual_intent import VisualIntentEngine

@pytest.mark.asyncio
async def test_product_ui_visual_intent():
    engine = VisualIntentEngine()
    segment = {
        "text": "The new OpenAI ChatGPT interface allows users to select custom canvas models.",
        "visual_intent": "product_ui"
    }
    
    reqs = await engine.generate_requirements(segment)
    
    assert len(reqs) >= 1
    req = reqs[0]
    assert req["asset_type"] in ("product_ui", "website", "screenshot", "screen_recording")
    assert "OpenAI" in req["search_query"] or "interface" in req["search_query"] or "ChatGPT" in req["search_query"]
    assert req["priority"] == "high"
    assert "reason" in req

@pytest.mark.asyncio
async def test_generic_stock_visual_intent():
    engine = VisualIntentEngine()
    segment = {
        "text": "Software engineers spend long hours thinking about system architecture.",
        "visual_intent": "stock_footage"
    }
    
    reqs = await engine.generate_requirements(segment)
    
    assert len(reqs) >= 1
    req = reqs[0]
    assert req["asset_type"] == "stock_footage"
    assert "reason" in req
