from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class DiscoveredAssetCandidate(BaseModel):
    title: str
    source: str
    source_url: str
    asset_url: str
    thumbnail_url: Optional[str] = None
    asset_type: str  # image, video, logo, screenshot
    license_info: str
    raw_metadata: Optional[Dict[str, Any]] = None

class AssetSearchProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def search(self, query: str, asset_type: str, limit: int = 5) -> List[DiscoveredAssetCandidate]:
        pass
