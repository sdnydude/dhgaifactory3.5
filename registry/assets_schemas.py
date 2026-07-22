"""Pydantic schemas for the assets API."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

VALID_CATEGORIES = {
    "brand", "product", "docs", "vector", "font", "design-source", "other",
}


class AssetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str = Field(..., max_length=512)
    filepath: Optional[str] = Field(default=None, max_length=1024)
    source_path: Optional[str] = Field(default=None, max_length=1024)
    source_drive: Optional[str] = Field(default=None, max_length=32)
    project_name: str = Field(..., max_length=100)
    design_system: Optional[str] = Field(default=None, max_length=64)
    category: Optional[str] = Field(default=None, max_length=64)
    mime_type: Optional[str] = Field(default=None, max_length=128)
    file_size_bytes: Optional[int] = None
    sha256: str = Field(..., max_length=64)
    width: Optional[int] = None
    height: Optional[int] = None
    dominant_color: Optional[str] = Field(default=None, max_length=9)
    alt_text: Optional[str] = None
    exif: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    model_name: Optional[str] = Field(default=None, max_length=64)
    meta_data: Optional[dict[str, Any]] = None


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    filepath: Optional[str]
    source_path: Optional[str]
    source_drive: Optional[str]
    project_name: str
    design_system: Optional[str]
    category: Optional[str]
    mime_type: Optional[str]
    file_size_bytes: Optional[int]
    sha256: str
    width: Optional[int]
    height: Optional[int]
    dominant_color: Optional[str]
    alt_text: Optional[str]
    exif: Optional[dict[str, Any]]
    tags: Optional[list[str]]
    model_name: Optional[str]
    meta_data: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class AssetList(BaseModel):
    assets: list[AssetResponse]
    total: int


class AssetBulkIngest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: str = Field(..., max_length=100)
    assets: list[AssetCreate]


class AssetSearch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2000)
    project_name: Optional[str] = None
    category: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)
