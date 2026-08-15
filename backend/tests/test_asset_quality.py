"""
Asset-quality regression tests.

These lock in the behaviour established by the asset-quality pass:

  * entity recovery (the istitle() gate used to discard GitHub / OpenAI / AI)
  * short, entity-led search queries
  * intent-aware admission — the right KIND of asset before a high score
  * intent-aware source preference
  * unchanged status thresholds (80 / 55)
  * providers stay optional and failures stay isolated
"""
from __future__ import annotations

import asyncio

import pytest

from app.services.asset_discovery import AssetDiscoveryEngine
from app.services.entity_extraction import (
    build_search_query,
    extract_entities,
    primary_entity,
)
from app.services.intent_policy import admits, provider_affinity, type_compatibility
from app.services.providers.base import AssetSearchProvider, DiscoveredAssetCandidate
from app.services.providers.wikimedia import build_commons_search, build_search_ladder
from app.services.relevance_scorer import RelevanceScorer


def run(coro):
    """
    Run a coroutine, leaving a usable event loop behind.

    asyncio.run() closes the loop and clears it from the thread; other modules
    in this suite still call the deprecated asyncio.get_event_loop(), which
    then raises. Installing a fresh loop afterwards keeps them working.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(asyncio.new_event_loop())


def candidate(title="Asset", source="Wikimedia Commons", asset_type="image",
              url="https://commons.wikimedia.org/asset.png"):
    return DiscoveredAssetCandidate(
        title=title,
        source=source,
        source_url=url,
        asset_url=url,
        asset_type=asset_type,
        license_info="CC BY 4.0",
    )


# ── Entity extraction ────────────────────────────────────────────────────────

class TestEntityExtraction:
    @pytest.mark.parametrize("name", ["GitHub", "OpenAI", "iPhone", "PostgreSQL"])
    def test_mixed_case_names_survive(self, name):
        """These are exactly the names str.istitle() used to reject."""
        assert name in extract_entities(f"The team shipped {name} last year.")

    @pytest.mark.parametrize("acronym", ["AI", "IDE", "API"])
    def test_acronyms_survive(self, acronym):
        assert acronym in extract_entities(f"Every {acronym} tool ships faster now.")

    def test_multi_word_entity_is_merged(self):
        assert "Visual Studio" in extract_entities(
            "Inside Visual Studio Code, the editor suggests functions."
        )

    @pytest.mark.parametrize("opener", ["Inside", "Behind", "For", "Instead"])
    def test_sentence_openers_are_not_entities(self, opener):
        ents = extract_entities(f"{opener} the building sits a quiet room.")
        assert opener not in ents

    def test_sentence_initial_verb_is_not_an_entity(self):
        assert primary_entity("Showing the official OpenAI brand logo.") == "OpenAI"

    def test_mid_sentence_entity_beats_sentence_initial_one(self):
        # "Modern" opens the sentence; "Kubernetes" is the real subject.
        assert primary_entity("Modern teams deploy on Kubernetes clusters.") == "Kubernetes"

    def test_returns_none_when_nothing_is_named(self):
        assert primary_entity("the team shipped it quickly last week") is None


class TestSearchQuery:
    def test_query_is_entity_led(self):
        q = build_search_query(
            "GitHub Copilot has changed the way developers write software.", "product_ui"
        )
        assert q.startswith("GitHub Copilot")
        assert "interface" in q

    def test_query_stays_short(self):
        """Commons ANDs terms; long queries only match text-layer documents."""
        long_line = (
            "The software industry is undergoing a massive shift as intelligent "
            "coding agents analyze repositories and write multi-file features."
        )
        for intent in ("product_ui", "stock_footage", "logo", "data_visualization"):
            assert len(build_search_query(long_line, intent).split()) <= 3

    def test_compound_noun_used_when_no_entity(self):
        q = build_search_query(
            "Behind every suggestion sits a data center running inference.", "location"
        )
        assert q == "data center"

    def test_query_never_empty(self):
        assert build_search_query("", "stock_footage").strip()


# ── Commons query composition ────────────────────────────────────────────────

class TestCommonsSearch:
    @pytest.mark.parametrize(
        "intent", ["product_ui", "screenshot", "website", "stock_footage", "logo", "person"]
    )
    def test_visual_intents_exclude_documents_at_source(self, intent):
        assert "filetype:bitmap" in build_commons_search("GitHub interface", intent)

    @pytest.mark.parametrize("intent", ["document", "historical", "news_reference"])
    def test_document_intents_allow_documents(self, intent):
        assert "filetype:bitmap" not in build_commons_search("GitHub report", intent)

    def test_term_count_is_capped(self):
        expr = build_commons_search("one two three four five six seven", "product_ui")
        terms = [t for t in expr.split() if not t.startswith("filetype:")]
        assert len(terms) <= 4

    def test_ladder_relaxes_by_dropping_the_qualifier(self):
        """"GitHub Copilot interface" finds nothing; "GitHub Copilot" finds 8."""
        ladder = build_search_ladder("GitHub Copilot interface", "product_ui")
        assert ladder[0].startswith("GitHub Copilot interface")
        assert any(
            e.startswith("GitHub Copilot") and "interface" not in e for e in ladder
        )

    def test_ladder_is_bounded(self):
        """Relaxation must not multiply pipeline latency."""
        assert len(build_search_ladder("a b c d e f g", "product_ui")) <= 2

    def test_ladder_keeps_the_document_filter_consistent(self):
        for expr in build_search_ladder("GitHub Copilot interface", "product_ui"):
            assert "filetype:bitmap" in expr
        for expr in build_search_ladder("annual report summary", "document"):
            assert "filetype:bitmap" not in expr


# ── Intent-aware admission ───────────────────────────────────────────────────

class TestIntentPolicy:
    @pytest.mark.parametrize(
        "intent", ["product_ui", "website", "screenshot", "screen_recording"]
    )
    def test_documents_rejected_for_ui_intents(self, intent):
        assert type_compatibility(intent, "document") == 0.0
        assert admits(intent, "document") is False

    @pytest.mark.parametrize("intent", ["product_ui", "screenshot", "website"])
    def test_images_preferred_for_ui_intents(self, intent):
        assert type_compatibility(intent, "image") == 1.0
        assert admits(intent, "image") is True

    def test_stock_footage_prefers_motion_but_accepts_stills(self):
        assert type_compatibility("stock_footage", "video") == 1.0
        assert 0 < type_compatibility("stock_footage", "image") < 1.0
        assert admits("stock_footage", "document") is False

    def test_logo_intent_prefers_logo_assets(self):
        assert type_compatibility("logo", "logo") == 1.0
        assert type_compatibility("logo", "logo") > type_compatibility("logo", "image")

    def test_document_intent_still_allows_documents(self):
        assert type_compatibility("document", "document") == 1.0
        assert admits("document", "document") is True

    def test_historical_allows_scanned_material(self):
        assert admits("historical", "document") is True

    def test_source_preference_is_intent_aware(self):
        # Stock photography belongs on Pexels; brand references do not.
        assert provider_affinity("stock_footage", "Pexels") > provider_affinity(
            "stock_footage", "Wikimedia Commons"
        )
        assert provider_affinity("historical", "Wikimedia Commons") > provider_affinity(
            "historical", "Pexels"
        )
        assert provider_affinity("logo", "Clearbit (Brand Asset API)") > provider_affinity(
            "logo", "Pexels"
        )

    def test_deprioritised_sources_are_never_crushed(self):
        """A gentle tie-breaker, not a way to sink a good asset."""
        for intent, table in (("product_ui", "Pexels"), ("historical", "Unsplash")):
            assert provider_affinity(intent, table) >= 0.85


# ── Scoring ──────────────────────────────────────────────────────────────────

class TestScoringQuality:
    def setup_method(self):
        self.scorer = RelevanceScorer()

    def test_pdf_scores_far_below_screenshot_for_product_ui(self):
        req = {"asset_type": "product_ui", "search_query": "GitHub Copilot interface"}
        segment = "GitHub Copilot has changed how developers write software."

        pdf, _, pdf_status = self.scorer.score(
            candidate("GitHub Copilot industry report", asset_type="document"), req, segment
        )
        shot, _, shot_status = self.scorer.score(
            candidate(
                "GitHub Copilot interface screenshot",
                asset_type="image",
                url="https://commons.wikimedia.org/github_copilot.png",
            ),
            req,
            segment,
        )

        assert shot > pdf
        assert shot - pdf >= 30, "document penalty should be substantial"
        assert pdf_status == "flagged"
        assert shot_status == "recommended"

    def test_document_rationale_explains_the_penalty(self):
        _, notes, _ = self.scorer.score(
            candidate("Some scanned report", asset_type="document"),
            {"asset_type": "product_ui", "search_query": "GitHub interface"},
            "GitHub ships new tooling.",
        )
        assert "does not suit" in notes

    def test_exact_entity_match_outranks_generic_title(self):
        req = {"asset_type": "product_ui", "search_query": "GitHub Copilot interface"}
        segment = "GitHub Copilot has changed how developers write software."

        exact, _, _ = self.scorer.score(
            candidate(
                "GitHub Copilot interface",
                url="https://commons.wikimedia.org/wiki/File:GitHub_Copilot.png",
            ),
            req,
            segment,
        )
        generic, _, _ = self.scorer.score(
            candidate("Generic coding interface", url="https://commons.wikimedia.org/x.png"),
            req,
            segment,
        )
        assert exact > generic

    def test_unrelated_asset_stays_flagged(self):
        score, _, status = self.scorer.score(
            candidate("Beach sunset holiday photo"),
            {"asset_type": "product_ui", "search_query": "GitHub Copilot interface"},
            "GitHub Copilot has changed how developers write software.",
        )
        assert score < 55
        assert status == "flagged"

    def test_thresholds_are_unchanged(self):
        """80 -> recommended, 55 -> alternative, below -> flagged."""
        import inspect

        from app.services import relevance_scorer

        src = inspect.getsource(relevance_scorer.RelevanceScorer.score)
        assert "total >= 80" in src
        assert "total >= 55" in src

    def test_score_stays_in_range(self):
        for asset_type in ("image", "video", "logo", "document"):
            score, _, _ = self.scorer.score(
                candidate(asset_type=asset_type),
                {"asset_type": "product_ui", "search_query": "GitHub interface"},
                "GitHub ships tooling.",
            )
            assert 0 <= score <= 100

    def test_breakdown_is_present_and_parseable(self):
        """The frontend parses these four factors out of usage_notes."""
        _, notes, _ = self.scorer.score(
            candidate("GitHub interface"),
            {"asset_type": "product_ui", "search_query": "GitHub interface"},
            "GitHub ships tooling.",
        )
        for factor in ("Semantic=", "Type=", "Source=", "Context="):
            assert factor in notes


# ── Discovery-level filtering and isolation ──────────────────────────────────

class _StubProvider(AssetSearchProvider):
    def __init__(self, name, results=None, boom=False):
        self._name = name
        self._results = results or []
        self._boom = boom

    @property
    def name(self):
        return self._name

    async def search(self, query, asset_type, limit=5):
        if self._boom:
            raise RuntimeError("provider exploded")
        return self._results


class TestDiscoveryFiltering:
    def _engine(self, providers):
        engine = AssetDiscoveryEngine()
        engine.providers = providers
        return engine

    def test_documents_filtered_before_scoring_for_ui_intent(self):
        engine = self._engine([
            _StubProvider("Wikimedia Commons", [
                candidate("A scanned report", asset_type="document",
                          url="https://commons.wikimedia.org/a.pdf"),
                candidate("GitHub interface screenshot", asset_type="image",
                          url="https://commons.wikimedia.org/b.png"),
            ]),
        ])
        assets, stats = run(engine.discover_for_requirement(
            {"asset_type": "product_ui", "search_query": "GitHub interface"},
            "GitHub ships tooling.",
        ))
        assert len(assets) == 1
        assert assets[0]["asset_type"] == "image"
        assert stats["filtered"]["document"] == 1

    def test_documents_kept_for_document_intent(self):
        engine = self._engine([
            _StubProvider("Wikimedia Commons", [
                candidate("A scanned report", asset_type="document",
                          url="https://commons.wikimedia.org/a.pdf"),
            ]),
        ])
        assets, _ = run(engine.discover_for_requirement(
            {"asset_type": "document", "search_query": "annual report"},
            "The annual report was published.",
        ))
        assert len(assets) == 1

    def test_provider_failure_stays_isolated(self):
        engine = self._engine([
            _StubProvider("Broken Provider", boom=True),
            _StubProvider("Wikimedia Commons", [
                candidate("GitHub interface", asset_type="image",
                          url="https://commons.wikimedia.org/b.png"),
            ]),
        ])
        assets, stats = run(engine.discover_for_requirement(
            {"asset_type": "product_ui", "search_query": "GitHub interface"},
            "GitHub ships tooling.",
        ))
        assert len(assets) == 1, "a failing provider must not lose the others' results"
        assert any("Broken Provider" in w for w in stats["warnings"])


class TestProvidersStayOptional:
    """Missing API keys degrade the result set; they never break the run."""

    def test_pexels_reports_unconfigured_without_a_key(self, monkeypatch):
        from app.core.config import settings
        from app.services.providers.pexels import PexelsProvider

        monkeypatch.setattr(settings, "PEXELS_API_KEY", "")
        provider = PexelsProvider()
        assert provider.is_configured is False
        assert run(provider.search("anything", "stock_footage")) == []

    def test_unsplash_reports_unconfigured_without_a_key(self, monkeypatch):
        from app.core.config import settings
        from app.services.providers.unsplash import UnsplashProvider

        monkeypatch.setattr(settings, "UNSPLASH_ACCESS_KEY", "")
        provider = UnsplashProvider()
        assert provider.is_configured is False
        assert run(provider.search("anything", "stock_footage")) == []

    def test_unconfigured_providers_are_skipped_not_failed(self):
        """No key must not surface as a warning — it is not an error."""
        engine = AssetDiscoveryEngine()
        engine.providers = [_StubProvider("Wikimedia Commons", [
            candidate("GitHub interface", asset_type="image",
                      url="https://commons.wikimedia.org/b.png"),
        ])]
        _, stats = run(engine.discover_for_requirement(
            {"asset_type": "product_ui", "search_query": "GitHub interface"},
            "GitHub ships tooling.",
        ))
        assert stats["warnings"] == []

    def test_intent_engine_works_without_gemini(self, monkeypatch):
        from app.core.config import settings
        from app.services.visual_intent import VisualIntentEngine

        monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
        reqs = run(VisualIntentEngine().generate_requirements({
            "text": "GitHub Copilot has changed how developers write software.",
            "visual_intent": "product_ui",
            "scene_description": "",
        }))
        assert reqs
        assert reqs[0]["search_query"].startswith("GitHub Copilot")
