import pytest
from app.services.relevance_scorer import RelevanceScorer
from app.services.providers.base import DiscoveredAssetCandidate

def test_relevance_scorer_bounds_and_rationale():
    scorer = RelevanceScorer()
    
    cand = DiscoveredAssetCandidate(
        title="OpenAI ChatGPT Interface Dashboard",
        source="Wikimedia Commons",
        source_url="https://commons.wikimedia.org/wiki/File:OpenAI_Logo.svg",
        asset_url="https://upload.wikimedia.org/wikipedia/commons/OpenAI_Logo.svg",
        asset_type="image",
        license_info="Creative Commons BY-SA 4.0"
    )
    
    requirement = {
        "search_query": "OpenAI ChatGPT interface",
        "asset_type": "product_ui"
    }
    
    segment_text = "The new OpenAI ChatGPT interface allows users to select custom models."
    
    score, rationale, status = scorer.score(cand, requirement, segment_text)
    
    assert 0 <= score <= 100
    assert score >= 70
    assert status == "recommended"
    assert "High confidence match" in rationale or "match" in rationale.lower()
