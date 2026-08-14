import pytest
from app.services.content_analyzer import ContentAnalyzer

@pytest.mark.asyncio
async def test_content_segmentation():
    analyzer = ContentAnalyzer()
    script = """
    The software industry is changing rapidly due to AI coding agents.
    Developers use modern IDE interface tools to generate multi-file code features.
    Here is a look at the live analytics dashboard showing team productivity stats.
    """
    
    segments = await analyzer.analyze(script)
    
    assert len(segments) >= 2
    assert segments[0]["sequence"] == 1
    assert "start_time" in segments[0]
    assert "end_time" in segments[0]
    assert "visual_intent" in segments[0]
    assert segments[0]["importance"] in ("high", "medium", "low")

@pytest.mark.asyncio
async def test_empty_script_segmentation():
    analyzer = ContentAnalyzer()
    segments = await analyzer.analyze("")
    assert segments == []
