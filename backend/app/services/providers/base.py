"""
Asset provider base contract.

All providers return List[DiscoveredAssetCandidate].
Provider-specific fields live inside `raw_metadata`.
The rest of the pipeline never imports provider-specific classes.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, field_validator
import re

# Allowed URL schemes for external assets
_ALLOWED_SCHEMES = ("https://", "http://")
_BLOCKED_SCHEMES = ("javascript:", "data:", "file:", "blob:")


def _validate_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return url
    url = url.strip()
    lower = url.lower()
    for blocked in _BLOCKED_SCHEMES:
        if lower.startswith(blocked):
            raise ValueError(f"Unsafe URL scheme rejected: {url[:60]}")
    if not any(lower.startswith(s) for s in _ALLOWED_SCHEMES):
        raise ValueError(f"URL must start with https:// or http://: {url[:60]}")
    return url


class DiscoveredAssetCandidate(BaseModel):
    """Normalized representation returned by every provider."""
    title: str
    source: str
    source_url: str
    asset_url: str
    thumbnail_url: Optional[str] = None
    asset_type: str       # image | video | logo | screenshot
    license_info: str
    license_url: Optional[str] = None
    usage_status: str = "verify_manually"   # public_domain | cc_licensed | provider_license | verify_manually
    provider_id: Optional[str] = None       # provider's own ID for deduplication
    raw_metadata: Optional[Dict[str, Any]] = None

    @field_validator("asset_url")
    @classmethod
    def validate_asset_url(cls, v: str) -> str:
        result = _validate_url(v)
        if result is None:
            raise ValueError("asset_url is required")
        return result

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, v: str) -> str:
        result = _validate_url(v)
        if result is None:
            raise ValueError("source_url is required")
        return result

    @field_validator("thumbnail_url")
    @classmethod
    def validate_thumbnail_url(cls, v: Optional[str]) -> Optional[str]:
        return _validate_url(v)


class AssetSearchProvider(ABC):
    """Abstract base class all asset providers must implement."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def search(
        self,
        query: str,
        asset_type: str,
        limit: int = 5
    ) -> List[DiscoveredAssetCandidate]: ...

    @property
    def is_configured(self) -> bool:
        """Returns True if the provider has all required credentials."""
        return True
