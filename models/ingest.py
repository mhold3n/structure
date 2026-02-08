from datetime import date
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl, field_validator
import uuid


class Provenance(BaseModel):
    source_name: str
    date_acquired: date
    author: Optional[str] = None
    url: Optional[HttpUrl] = None


class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provenance: Provenance
    license: Literal["CC-BY", "CC-BY-SA", "Public Domain", "Proprietary", "Unknown"]
    source_path: str
    content: str
    metadata: dict = Field(default_factory=dict)

    @field_validator("content")
    def content_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Document content cannot be empty")
        return v


class Span(BaseModel):
    start: int
    end: int

    @field_validator("end")
    def end_gt_start(cls, v, values):
        if "start" in values.data and v <= values.data["start"]:
            raise ValueError("Span end must be greater than start")
        return v


class Chunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str
    text: str
    span: Span
    section: Optional[str] = None
    page: Optional[int] = None
    token_count: Optional[int] = None


class Figure(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str
    page: int
    caption: str
    bbox: Optional[List[int]] = None  # [x1, y1, x2, y2]
    image_path: str
    phash: Optional[str] = None  # Perceptual hash for dedup
