"""
Intent-aware routing and candidate admission.

Two decisions live here so that providers, the discovery engine and the scorer
all agree on them:

  * which providers are worth querying for a given visual intent, and in what
    order of preference;
  * whether a returned candidate is even the RIGHT KIND of thing for that
    intent, independent of how well its title matches the query.

The second point is the important one. Getting the asset TYPE right has to come
before scoring — a scanned PDF that happens to share keywords with a product-UI
requirement should not compete with an actual screenshot, however good its
token overlap is.
"""
from __future__ import annotations

from typing import Dict, FrozenSet

# ── Candidate kinds ──────────────────────────────────────────────────────────
KIND_IMAGE = "image"
KIND_VIDEO = "video"
KIND_DOCUMENT = "document"
KIND_LOGO = "logo"

# Intents that want a still picture / screenshot.
_VISUAL_STILL: FrozenSet[str] = frozenset({
    "product_ui", "screenshot", "website", "diagram", "data_visualization",
    "illustration", "person", "location", "historical", "news_reference",
})
# Intents that want motion (but will accept a still as a fallback).
_VISUAL_MOTION: FrozenSet[str] = frozenset({
    "stock_footage", "screen_recording", "abstract_broll",
})
# Intents where a document IS the asset.
_DOCUMENT_INTENTS: FrozenSet[str] = frozenset({"document"})
_LOGO_INTENTS: FrozenSet[str] = frozenset({"logo"})


def is_document_kind(asset_type: str) -> bool:
    return asset_type.lower() in {KIND_DOCUMENT, "pdf", "djvu"}


def type_compatibility(intent: str, asset_type: str) -> float:
    """
    How well a candidate's kind suits the requirement, in [0, 1].

    1.0  exactly the right kind
    0.6  usable substitute (a still for a footage slot)
    0.15 wrong kind but not nonsense
    0.0  actively wrong — a scanned document for a product-UI slot
    """
    kind = (asset_type or "").lower()

    if intent in _DOCUMENT_INTENTS:
        return 1.0 if is_document_kind(kind) else 0.5

    if intent in _LOGO_INTENTS:
        if kind == KIND_LOGO:
            return 1.0
        if kind == KIND_IMAGE:
            return 0.5
        return 0.0

    if is_document_kind(kind):
        # historical / news_reference can legitimately be a scan.
        if intent in {"historical", "news_reference"}:
            return 0.6
        return 0.0

    if intent in _VISUAL_MOTION:
        if kind == KIND_VIDEO:
            return 1.0
        if kind in (KIND_IMAGE, KIND_LOGO):
            return 0.6
        return 0.15

    if intent in _VISUAL_STILL:
        if kind == KIND_IMAGE:
            return 1.0
        if kind == KIND_LOGO:
            return 0.7
        if kind == KIND_VIDEO:
            return 0.6
        return 0.15

    return 0.5


def admits(intent: str, asset_type: str) -> bool:
    """
    Whether a candidate should reach the scorer at all.

    Only kinds scoring 0.0 on compatibility are rejected, so this filters the
    clear category errors (a PDF for a screenshot) without discarding anything
    a human might still find useful.
    """
    return type_compatibility(intent, asset_type) > 0.0


# ── Provider preference ──────────────────────────────────────────────────────
# Multiplier applied to a provider's base source tier for this intent. Above
# 1.0 means "this provider is the right place to look for this kind of asset".
#
# De-prioritisation is deliberately gentle (>= 0.85 for any legitimate image
# source). The multiplier is meant to break ties between comparable candidates,
# not to sink an otherwise perfect match below a status threshold — a great
# Pexels screenshot is still a great screenshot.
_PROVIDER_AFFINITY: Dict[str, Dict[str, float]] = {
    "product_ui": {
        "web & brand reference": 1.30,
        "clearbit (brand asset api)": 1.30,
        "wikipedia": 1.10,
        "wikimedia commons": 1.00,
        "pexels": 0.90,
        "unsplash": 0.90,
    },
    "website": {
        "web & brand reference": 1.30,
        "clearbit (brand asset api)": 1.30,
        "wikipedia": 1.10,
        "pexels": 0.90,
        "unsplash": 0.90,
    },
    "screenshot": {
        "web & brand reference": 1.25,
        "wikimedia commons": 1.05,
        "pexels": 0.90,
        "unsplash": 0.90,
    },
    "logo": {
        "clearbit (brand asset api)": 1.35,
        "web & brand reference": 1.30,
        "wikimedia commons": 1.05,
        "pexels": 0.85,
        "unsplash": 0.85,
    },
    "stock_footage": {
        "pexels": 1.30,
        "unsplash": 1.25,
        "wikimedia commons": 0.95,
        "clearbit (brand asset api)": 0.85,
    },
    "abstract_broll": {
        "pexels": 1.30,
        "unsplash": 1.25,
        "wikimedia commons": 0.90,
    },
    "person": {
        "pexels": 1.15,
        "unsplash": 1.15,
        "wikipedia": 1.15,
        "wikimedia commons": 1.00,
    },
    "location": {
        "unsplash": 1.20,
        "pexels": 1.20,
        "wikimedia commons": 1.05,
    },
    "historical": {
        "wikimedia commons": 1.30,
        "wikipedia": 1.20,
        "pexels": 0.85,
        "unsplash": 0.85,
    },
    "diagram": {
        "wikimedia commons": 1.25,
        "wikipedia": 1.15,
        "pexels": 0.85,
        "unsplash": 0.85,
    },
    "data_visualization": {
        "wikimedia commons": 1.20,
        "wikipedia": 1.10,
        "pexels": 0.85,
        "unsplash": 0.85,
    },
    "document": {
        "wikimedia commons": 1.25,
        "wikipedia": 1.10,
        "pexels": 0.85,
        "unsplash": 0.85,
    },
}


def provider_affinity(intent: str, source: str) -> float:
    """Intent-aware multiplier for a source's base quality tier."""
    table = _PROVIDER_AFFINITY.get(intent)
    if not table:
        return 1.0
    return table.get((source or "").lower(), 1.0)
