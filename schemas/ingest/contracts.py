from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Literal, Any
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator


class Partition(str, Enum):
    TRAIN = "train"
    DEV = "dev"
    TEST = "test"
    UNASSIGNED = "unassigned"


class License(str, Enum):
    CC_BY = "CC-BY"
    CC_BY_SA = "CC-BY-SA"
    PUBLIC_DOMAIN = "Public Domain"
    PROPRIETARY = "Proprietary"
    UNKNOWN = "Unknown"


class Provenance(BaseModel):
    """
    Tracks the origin and lineage of a data artifact.
    """

    source_name: str = Field(..., description="Name of the data source (e.g., 'OpenStax_Physics')")
    source_uri: str = Field(..., description="URI or path to the original source")
    author: Optional[str] = Field(None, description="Original author or creator")
    date_acquired: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when data was acquired",
    )
    license: License = Field(default=License.UNKNOWN, description="License of the source data")
    ingestion_id: str = Field(..., description="ID of the ingestion event/run")


class BaseArtifact(BaseModel):
    """
    Base class for all ingested artifacts.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique artifact ID")
    partition: Partition = Field(
        default=Partition.UNASSIGNED, description="Assigned data partition"
    )
    provenance: Provenance
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata")


class Document(BaseArtifact):
    """
    Canonical representation of a whole document.
    """

    content: str = Field(..., description="Full text content of the document")
    content_hash: str = Field(..., description="MD5 hash of the content for exact dedup")

    @field_validator("content")
    def content_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Document content cannot be empty")
        return v


class Span(BaseModel):
    start: int
    end: int


class Chunk(BaseArtifact):
    """
    A specific segment of a document (e.g., paragraph, section).
    """

    doc_id: str = Field(..., description="ID of the parent Document")
    text: str = Field(..., description="Text content of the chunk")
    span: Span = Field(..., description="Character range in original document")
    token_count: Optional[int] = None


class AssetType(str, Enum):
    FIGURE = "figure"
    TABLE = "table"
    EQUATION = "equation"


class Asset(BaseArtifact):
    """
    Extracted non-text asset like a figure or table.
    """

    doc_id: str = Field(..., description="ID of the parent Document")
    asset_type: AssetType
    caption: Optional[str] = None
    content_uri: Optional[str] = Field(None, description="Path to valid asset file (e.g. image)")
    bbox: Optional[List[int]] = Field(None, description="[x1, y1, x2, y2] bounding box")
    phash: Optional[str] = Field(None, description="Perceptual hash for deduplication")
