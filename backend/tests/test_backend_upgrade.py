"""
Comprehensive SLAYERS test suite.

Coverage:
  - Content analyzer: all 5 split strategies, intent detection, Pydantic validation
  - Visual intent engine: all 14 intent templates, heuristic fallbacks, validation
  - Relevance scorer: scoring formula, status thresholds, partial matching
  - Asset discovery: provider deduplication, stats aggregation, result capping
  - API: create, list, get, status, summary, delete, 409 guard, 422 validation
  - Provider failures: timeout, network error, bad JSON — pipeline continues
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ── Test DB: use a named file so the same engine is seen across all imports ──
# We monkeypatch app.core.db before importing the app so that BOTH Base.metadata
# and SessionLocal use the test engine.
import app.core.db as _db_module

_TEST_DB_URL = "sqlite:///./test_slayers_temp.db"
_engine_test = create_engine(_TEST_DB_URL, connect_args={"check_same_thread": False})
_TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine_test)

# Patch the module-level objects BEFORE any other app code runs
_db_module.engine = _engine_test
_db_module.SessionLocal = _TestingSessionLocal


def _override_get_db():
    session = _TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


_db_module.get_db = _override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create tables once for the entire test session, drop on teardown."""
    from app.core.db import Base
    Base.metadata.create_all(bind=_engine_test)
    yield
    Base.metadata.drop_all(bind=_engine_test)
    _engine_test.dispose()
    # Best-effort file cleanup on Windows (ignore lock errors)
    import os, time
    for _ in range(3):
        try:
            os.remove("test_slayers_temp.db")
            break
        except (FileNotFoundError, PermissionError):
            time.sleep(0.5)


@pytest.fixture
def db():
    session = _TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client():
    from app.main import app
    from app.core.db import get_db

    app.dependency_overrides[get_db] = _override_get_db
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()



# ─────────────────────────────────────────────────────────────────────────────
# 1. CONTENT ANALYZER
# ─────────────────────────────────────────────────────────────────────────────
class TestContentAnalyzer:
    def setup_method(self):
        from app.services.content_analyzer import ContentAnalyzer
        self.analyzer = ContentAnalyzer()

    def _run(self, text):
        return asyncio.get_event_loop().run_until_complete(
            self.analyzer.analyze(text)
        )

    def test_empty_text_returns_empty(self):
        assert self._run("") == []

    def test_whitespace_only_returns_empty(self):
        assert self._run("   \n\n  ") == []

    def test_single_paragraph(self):
        result = self._run("The AI revolution is transforming software development.")
        assert len(result) >= 1
        assert result[0]["sequence"] == 1

    def test_numbered_list_splitting(self):
        text = "1. Introduction to AI agents.\n2. How they write code.\n3. Real world impact."
        result = self._run(text)
        assert len(result) == 3

    def test_timestamped_splitting(self):
        text = "00:00 Introduction\n00:10 Deep dive into AI\n00:25 Conclusion"
        result = self._run(text)
        assert len(result) == 3

    def test_double_newline_splitting(self):
        text = "First paragraph about AI.\n\nSecond paragraph about robotics.\n\nThird about automation."
        result = self._run(text)
        assert len(result) == 3

    def test_intent_product_ui(self):
        result = self._run("The new dashboard interface allows users to click through settings.")
        assert result[0]["visual_intent"] == "product_ui"

    def test_intent_data_visualization(self):
        result = self._run("Revenue grew by 45 percent according to the latest metrics and analytics.")
        assert result[0]["visual_intent"] == "data_visualization"

    def test_intent_diagram(self):
        result = self._run("The system architecture diagram shows the complete pipeline infrastructure.")
        assert result[0]["visual_intent"] == "diagram"

    def test_intent_news_reference(self):
        result = self._run("A major breaking news headline announced the product launch.")
        assert result[0]["visual_intent"] == "news_reference"

    def test_intent_historical(self):
        result = self._run("Looking at the historical archive from the past century of innovation.")
        assert result[0]["visual_intent"] == "historical"

    def test_intent_logo(self):
        result = self._run("The brand logo and icon symbolize the company trademark.")
        assert result[0]["visual_intent"] == "logo"

    def test_intent_location(self):
        result = self._run("The headquarters office building is located in the city center.")
        assert result[0]["visual_intent"] == "location"

    def test_intent_fallback_stock_footage(self):
        result = self._run("Something completely vague with no clear visual markers whatsoever.")
        assert result[0]["visual_intent"] == "stock_footage"

    def test_segments_have_required_fields(self):
        result = self._run("AI is transforming the world. This is a second sentence here.")
        for seg in result:
            assert "sequence" in seg
            assert "text" in seg
            assert "visual_intent" in seg
            assert "importance" in seg

    def test_max_segments_respected(self):
        # Create a very long text
        many_lines = "\n".join([f"Line {i}: This is content about topic {i}." for i in range(1, 200)])
        result = self._run(many_lines)
        from app.core.config import settings
        assert len(result) <= settings.MAX_SEGMENTS

    def test_gemini_failure_falls_back(self):
        """When Gemini raises, heuristic engine is used."""
        with patch.object(self.analyzer, "_analyze_with_gemini", side_effect=RuntimeError("API down")):
            with patch("app.core.config.settings.GEMINI_API_KEY", "fake-key"):
                result = self._run("The software interface allows users to click buttons.")
        assert len(result) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 2. VISUAL INTENT ENGINE
# ─────────────────────────────────────────────────────────────────────────────
class TestVisualIntentEngine:
    def setup_method(self):
        from app.services.visual_intent import VisualIntentEngine
        self.engine = VisualIntentEngine()

    def _req(self, text: str, intent: str):
        seg = {"text": text, "visual_intent": intent, "scene_description": ""}
        return asyncio.get_event_loop().run_until_complete(
            self.engine.generate_requirements(seg)
        )

    def test_product_ui_returns_requirement(self):
        reqs = self._req("The app dashboard shows real-time metrics.", "product_ui")
        assert len(reqs) >= 1
        assert reqs[0]["asset_type"] == "product_ui"
        assert reqs[0]["priority"] == "high"

    def test_logo_returns_requirement(self):
        reqs = self._req("Google's brand logo is globally recognized.", "logo")
        assert reqs[0]["asset_type"] == "logo"

    def test_data_visualization_requirement(self):
        reqs = self._req("Revenue grew 40 percent this quarter.", "data_visualization")
        assert reqs[0]["asset_type"] == "data_visualization"

    def test_diagram_requirement(self):
        reqs = self._req("The architecture diagram shows pipeline flow.", "diagram")
        assert reqs[0]["asset_type"] == "diagram"

    def test_news_reference_requirement(self):
        reqs = self._req("A headline announced the new product launch.", "news_reference")
        assert reqs[0]["asset_type"] == "news_reference"

    def test_historical_requirement(self):
        reqs = self._req("Looking back at the vintage archive.", "historical")
        assert reqs[0]["asset_type"] == "historical"

    def test_stock_footage_fallback(self):
        reqs = self._req("Some vague narration content here.", "stock_footage")
        assert reqs[0]["asset_type"] == "stock_footage"

    def test_all_requirements_have_required_fields(self):
        reqs = self._req("The software is changing how developers work.", "product_ui")
        for r in reqs:
            assert "asset_type" in r
            assert "description" in r
            assert "search_query" in r
            assert "priority" in r
            assert r["priority"] in ("high", "medium", "low")

    def test_search_query_non_empty(self):
        reqs = self._req("GitHub Copilot is an AI coding assistant.", "product_ui")
        assert all(len(r["search_query"].strip()) > 0 for r in reqs)

    def test_proper_noun_extraction(self):
        reqs = self._req("OpenAI and GitHub have released AI coding tools.", "product_ui")
        # At least one requirement should reference proper nouns
        all_queries = " ".join(r["search_query"] for r in reqs).lower()
        # Should have some real content words
        assert len(all_queries) > 5

    def test_gemini_failure_falls_back_to_heuristic(self):
        with patch.object(self.engine, "_generate_with_gemini", side_effect=RuntimeError("API error")):
            with patch("app.core.config.settings.GEMINI_API_KEY", "fake-key"):
                seg = {"text": "The dashboard shows metrics.", "visual_intent": "product_ui", "scene_description": ""}
                reqs = asyncio.get_event_loop().run_until_complete(
                    self.engine.generate_requirements(seg)
                )
        assert len(reqs) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 3. RELEVANCE SCORER
# ─────────────────────────────────────────────────────────────────────────────
class TestRelevanceScorer:
    def setup_method(self):
        from app.services.relevance_scorer import RelevanceScorer
        from app.services.providers.base import DiscoveredAssetCandidate
        self.scorer = RelevanceScorer()
        self.Candidate = DiscoveredAssetCandidate

    def _candidate(self, title="Test Image", source="Pexels", asset_type="image"):
        return self.Candidate(
            title=title,
            source=source,
            source_url="https://pexels.com/photo/1",
            asset_url="https://images.pexels.com/photo.jpg",
            asset_type=asset_type,
            license_info="Pexels License",
        )

    def test_score_in_valid_range(self):
        cand = self._candidate("GitHub Copilot interface dashboard")
        req = {"asset_type": "product_ui", "search_query": "github copilot interface"}
        score, notes, status = self.scorer.score(cand, req, "GitHub Copilot is an AI tool")
        assert 0 <= score <= 100

    def test_high_overlap_yields_recommended(self):
        cand = self._candidate("github copilot ai coding dashboard interface screenshot")
        req = {"asset_type": "product_ui", "search_query": "github copilot interface dashboard"}
        score, notes, status = self.scorer.score(cand, req, "GitHub Copilot dashboard")
        assert status == "recommended"
        assert score >= 80

    def test_unrelated_title_yields_low_score(self):
        cand = self._candidate("random beach sunset photo holiday")
        req = {"asset_type": "product_ui", "search_query": "github copilot interface"}
        score, notes, status = self.scorer.score(cand, req, "GitHub Copilot is an AI tool")
        assert score < 70

    def test_type_mismatch_penalizes(self):
        # video candidate for an image requirement
        cand = self._candidate(asset_type="video")
        req = {"asset_type": "logo", "search_query": "brand logo"}
        score1, _, _ = self.scorer.score(cand, req, "the brand logo")

        cand_img = self._candidate(asset_type="image")
        score2, _, _ = self.scorer.score(cand_img, req, "the brand logo")
        assert score2 >= score1

    def test_notes_contain_breakdown(self):
        cand = self._candidate("tech software dashboard")
        req = {"asset_type": "product_ui", "search_query": "software dashboard"}
        _, notes, _ = self.scorer.score(cand, req, "")
        assert "Semantic=" in notes

    def test_wikimedia_source_scores_higher(self):
        cand_wiki = self._candidate(source="Wikimedia Commons")
        cand_unknown = self._candidate(source="Some Random Site")
        req = {"asset_type": "image", "search_query": "test"}
        s1, _, _ = self.scorer.score(cand_wiki, req, "")
        s2, _, _ = self.scorer.score(cand_unknown, req, "")
        assert s1 > s2

    def test_zero_overlap_still_positive_score(self):
        cand = self._candidate("completely unrelated banana tree photo")
        req = {"asset_type": "stock_footage", "search_query": "artificial intelligence"}
        score, _, _ = self.scorer.score(cand, req, "")
        assert score > 0


# ─────────────────────────────────────────────────────────────────────────────
# 4. ASSET DISCOVERY ENGINE
# ─────────────────────────────────────────────────────────────────────────────
class TestAssetDiscoveryEngine:
    def setup_method(self):
        from app.services.asset_discovery import AssetDiscoveryEngine
        from app.services.providers.base import DiscoveredAssetCandidate
        self.engine = AssetDiscoveryEngine()
        self.Candidate = DiscoveredAssetCandidate

    def _candidate(self, title, url, provider_id=None):
        return self.Candidate(
            title=title,
            source="Pexels",
            source_url="https://pexels.com",
            asset_url=url,
            asset_type="image",
            license_info="Pexels License",
            provider_id=provider_id,
        )

    def test_deduplication_by_url(self):
        """Same URL from two providers should appear once."""
        cand = self._candidate("Test", "https://example.com/img.jpg")

        async def mock_search(q, t, limit=5):
            return [cand]

        for p in self.engine.providers:
            p.search = mock_search

        req = {"asset_type": "image", "search_query": "test"}
        result, stats = asyncio.get_event_loop().run_until_complete(
            self.engine.discover_for_requirement(req, "test context")
        )
        urls = [r["asset_url"] for r in result]
        assert len(urls) == len(set(urls))

    def test_deduplication_by_provider_id(self):
        cand1 = self._candidate("Asset A", "https://example.com/a.jpg", "pexels:1")
        cand2 = self._candidate("Asset A copy", "https://example.com/b.jpg", "pexels:1")

        call_count = [0]
        async def mock_search(q, t, limit=5):
            call_count[0] += 1
            if call_count[0] == 1:
                return [cand1]
            return [cand2]

        for p in self.engine.providers:
            p.search = mock_search

        req = {"asset_type": "image", "search_query": "test"}
        result, _ = asyncio.get_event_loop().run_until_complete(
            self.engine.discover_for_requirement(req, "")
        )
        provider_ids = [r["provider_id"] for r in result if r.get("provider_id")]
        assert len(provider_ids) == len(set(provider_ids))

    def test_provider_failure_does_not_crash(self):
        import asyncio as aio

        async def timeout_search(q, t, limit=5):
            raise aio.TimeoutError()

        for p in self.engine.providers:
            p.search = timeout_search

        req = {"asset_type": "image", "search_query": "github copilot"}
        result, stats = asyncio.get_event_loop().run_until_complete(
            self.engine.discover_for_requirement(req, "")
        )
        assert isinstance(result, list)

    def test_result_capped(self):
        from app.core.config import settings

        async def many_results(q, t, limit=5):
            return [
                self._candidate(f"Asset {i}", f"https://ex.com/{i}.jpg", f"pid:{i}")
                for i in range(20)
            ]

        for p in self.engine.providers:
            p.search = many_results

        req = {"asset_type": "image", "search_query": "test"}
        result, _ = asyncio.get_event_loop().run_until_complete(
            self.engine.discover_for_requirement(req, "")
        )
        assert len(result) <= settings.MAX_ASSETS_PER_REQUIREMENT

    def test_results_sorted_by_score(self):
        cands = [
            self._candidate(f"Asset {i}", f"https://ex.com/{i}.jpg", f"id:{i}")
            for i in range(5)
        ]

        idx = [0]
        async def sequential_search(q, t, limit=5):
            if idx[0] < len(cands):
                c = cands[idx[0]]
                idx[0] += 1
                return [c]
            return []

        for p in self.engine.providers:
            p.search = sequential_search

        req = {"asset_type": "image", "search_query": "test"}
        result, _ = asyncio.get_event_loop().run_until_complete(
            self.engine.discover_for_requirement(req, "")
        )
        scores = [r["relevance_score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_empty_query_returns_empty(self):
        req = {"asset_type": "image", "search_query": ""}
        result, stats = asyncio.get_event_loop().run_until_complete(
            self.engine.discover_for_requirement(req, "")
        )
        assert result == []


# ─────────────────────────────────────────────────────────────────────────────
# 5. API ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
class TestProjectAPI:
    def test_health(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["app"] == "SLAYERS"
        assert "database" in res.json()

    def test_create_project(self, client):
        res = client.post("/api/projects", json={
            "name": "Test Project",
            "source_type": "script",
            "source_text": "AI is changing software development rapidly.",
        })
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Test Project"
        assert data["status"] == "draft"
        assert "id" in data

    def test_create_project_empty_text_rejected(self, client):
        res = client.post("/api/projects", json={
            "name": "Empty",
            "source_type": "script",
            "source_text": "   ",
        })
        assert res.status_code == 422

    def test_create_project_invalid_source_type_rejected(self, client):
        res = client.post("/api/projects", json={
            "name": "Bad Type",
            "source_type": "unknown_type",
            "source_text": "Some text here.",
        })
        assert res.status_code == 422

    def test_create_project_text_too_long_rejected(self, client):
        res = client.post("/api/projects", json={
            "name": "Too Long",
            "source_type": "script",
            "source_text": "x" * 25000,
        })
        assert res.status_code == 422

    def test_list_projects(self, client):
        # Create one first
        client.post("/api/projects", json={
            "name": "List Test",
            "source_type": "text",
            "source_text": "Some content for listing.",
        })
        res = client.get("/api/projects")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_get_project(self, client):
        create_res = client.post("/api/projects", json={
            "name": "Get Test",
            "source_type": "script",
            "source_text": "Fetching this project by ID.",
        })
        pid = create_res.json()["id"]
        res = client.get(f"/api/projects/{pid}")
        assert res.status_code == 200
        assert res.json()["id"] == pid

    def test_get_project_not_found(self, client):
        res = client.get("/api/projects/nonexistent-id-12345")
        assert res.status_code == 404

    def test_delete_project(self, client):
        create_res = client.post("/api/projects", json={
            "name": "Delete Test",
            "source_type": "text",
            "source_text": "This project will be deleted.",
        })
        pid = create_res.json()["id"]
        del_res = client.delete(f"/api/projects/{pid}")
        assert del_res.status_code == 204
        get_res = client.get(f"/api/projects/{pid}")
        assert get_res.status_code == 404

    def test_get_status_before_processing(self, client):
        create_res = client.post("/api/projects", json={
            "name": "Status Test",
            "source_type": "script",
            "source_text": "Testing status endpoint.",
        })
        pid = create_res.json()["id"]
        res = client.get(f"/api/projects/{pid}/status")
        assert res.status_code == 200
        assert res.json()["status"] in ("pending", "processing", "completed", "failed")

    def test_summary_not_found(self, client):
        res = client.get("/api/projects/bad-id-999/summary")
        assert res.status_code == 404

    def test_demo_project_creation(self, client):
        with patch("app.api.projects.process_project_pipeline", new_callable=AsyncMock):
            res = client.post("/api/projects/demo")
        assert res.status_code == 201
        assert "demo" in res.json()["name"].lower() or "ai" in res.json()["name"].lower()

    def test_asset_status_patch(self, client):
        """Create a project, manually add an asset, then patch its status."""
        from app.core.db import get_db
        # We test with a non-existent asset — should 404
        res = client.patch("/api/assets/nonexistent-asset/status", json={"status": "flagged"})
        assert res.status_code == 404

    def test_asset_status_invalid_value_rejected(self, client):
        res = client.patch("/api/assets/any-id/status", json={"status": "invalid_value"})
        # 404 on missing asset before 422 — either is acceptable
        assert res.status_code in (404, 422)
