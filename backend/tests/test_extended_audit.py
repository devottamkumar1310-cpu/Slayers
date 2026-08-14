import pytest
from app.services.content_analyzer import ContentAnalyzer
from app.services.visual_intent import VisualIntentEngine
from app.services.relevance_scorer import RelevanceScorer
from app.services.asset_discovery import AssetDiscoveryEngine
from app.services.providers.base import DiscoveredAssetCandidate
from app.schemas.schemas import ProjectSummaryResponse

@pytest.mark.asyncio
async def test_multi_format_script_parsing():
    analyzer = ContentAnalyzer()
    
    # 1. Numbered script format
    numbered_script = """
    Scene 1: Introduction to revolutionary cloud microservices architecture.
    Scene 2: Live metrics dashboard processing millions of requests per second.
    Scene 3: Summary of engineering productivity gains and concluding remarks.
    """
    segments_num = await analyzer.analyze(numbered_script)
    assert len(segments_num) >= 3
    assert segments_num[0]["sequence"] == 1
    assert segments_num[1]["visual_intent"] in ("data_visualization", "product_ui")

    # 2. Timestamped script format
    timestamped_script = """
    00:00 Welcome to today's tech breakdown.
    00:15 OpenAI releases a brand new canvas interface for coding.
    00:30 Revenue charts show 45% year over year growth.
    """
    segments_ts = await analyzer.analyze(timestamped_script)
    assert len(segments_ts) >= 3
    assert segments_ts[1]["visual_intent"] in ("product_ui", "logo", "news_reference")
    assert segments_ts[2]["visual_intent"] in ("data_visualization", "product_ui")

@pytest.mark.asyncio
async def test_expanded_visual_intent_categories():
    engine = VisualIntentEngine()
    
    # Data visualization test
    seg_chart = {
        "text": "The quarterly analytics report shows a 68% increase in active developers.",
        "visual_intent": "data_visualization"
    }
    reqs_chart = await engine.generate_requirements(seg_chart)
    assert len(reqs_chart) >= 1
    assert reqs_chart[0]["asset_type"] == "data_visualization"
    assert "chart" in reqs_chart[0]["search_query"] or "data" in reqs_chart[0]["search_query"]

    # Diagram test
    seg_diag = {
        "text": "The underlying system architecture consists of distributed event pipelines.",
        "visual_intent": "diagram"
    }
    reqs_diag = await engine.generate_requirements(seg_diag)
    assert len(reqs_diag) >= 1
    assert reqs_diag[0]["asset_type"] == "diagram"

    # Logo test
    seg_logo = {
        "text": "We are partnering directly with Microsoft to integrate enterprise tooling.",
        "visual_intent": "logo"
    }
    reqs_logo = await engine.generate_requirements(seg_logo)
    assert len(reqs_logo) >= 1
    assert reqs_logo[0]["asset_type"] == "logo"
    assert "Microsoft" in reqs_logo[0]["search_query"]

@pytest.mark.asyncio
async def test_parallel_asset_discovery_and_resilience():
    discovery = AssetDiscoveryEngine()
    
    req = {
        "search_query": "artificial intelligence neural network",
        "asset_type": "stock_footage",
        "priority": "high"
    }
    
    results = await discovery.discover_for_requirement(req, "Narration discussing neural network layers.")
    
    # Check that results are returned and sorted descending by relevance score
    assert isinstance(results, list)
    if len(results) >= 2:
        for i in range(len(results) - 1):
            assert results[i]["relevance_score"] >= results[i+1]["relevance_score"]
        assert results[0]["status"] == "recommended"
        assert results[1]["status"] in ("alternative", "recommended")

def test_relevance_scorer_calibration():
    scorer = RelevanceScorer()
    
    cand_high = DiscoveredAssetCandidate(
        title="OpenAI Logo Vector SVG",
        source="Wikimedia Commons",
        source_url="https://commons.wikimedia.org/wiki/File:OpenAI_Logo.svg",
        asset_url="https://upload.wikimedia.org/wikipedia/commons/OpenAI_Logo.svg",
        asset_type="logo",
        license_info="Public Domain"
    )
    
    req = {"search_query": "OpenAI official logo", "asset_type": "logo"}
    score, rationale, status = scorer.score(cand_high, req, "Showing the official OpenAI brand logo.")
    
    assert score >= 75
    assert status in ("recommended", "alternative")
    assert "100" in rationale
