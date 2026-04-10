"""
Frontend Design Specs API — CRUD for design spec tracking.
"""
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import FrontendDesignSpec

logger = logging.getLogger("dhg.frontend_specs")

router = APIRouter(prefix="/api/v1/frontend-specs", tags=["frontend-specs"])


class SpecCreate(BaseModel):
    feature_name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=255)
    status: str = Field(default="draft", max_length=50)
    spec_path: str = Field(..., max_length=512)
    comp_path: Optional[str] = Field(default=None, max_length=512)
    description: str
    components: list = Field(default_factory=list)
    design_tokens: dict = Field(default_factory=dict)
    visual_polish: dict = Field(default_factory=dict)


class SpecUpdate(BaseModel):
    feature_name: Optional[str] = Field(default=None, max_length=255)
    status: Optional[str] = Field(default=None, max_length=50)
    spec_path: Optional[str] = Field(default=None, max_length=512)
    comp_path: Optional[str] = Field(default=None, max_length=512)
    description: Optional[str] = None
    components: Optional[list] = None
    design_tokens: Optional[dict] = None
    visual_polish: Optional[dict] = None
    approved_by: Optional[str] = Field(default=None, max_length=255)
    approved_at: Optional[datetime] = None
    implemented_at: Optional[datetime] = None


class SpecResponse(BaseModel):
    id: str
    feature_name: str
    slug: str
    status: str
    spec_path: str
    comp_path: Optional[str]
    description: str
    components: list
    design_tokens: dict
    visual_polish: dict
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    implemented_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[SpecResponse])
async def list_specs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    specs = db.query(FrontendDesignSpec).offset(skip).limit(limit).all()
    return [_to_response(s) for s in specs]


@router.get("/{slug}", response_model=SpecResponse)
async def get_spec_by_slug(slug: str, db: Session = Depends(get_db)):
    spec = db.query(FrontendDesignSpec).filter(FrontendDesignSpec.slug == slug).first()
    if not spec:
        raise HTTPException(status_code=404, detail=f"Spec with slug '{slug}' not found")
    return _to_response(spec)


@router.post("", response_model=SpecResponse, status_code=status.HTTP_201_CREATED)
async def create_spec(payload: SpecCreate, db: Session = Depends(get_db)):
    existing = db.query(FrontendDesignSpec).filter(FrontendDesignSpec.slug == payload.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Spec with slug '{payload.slug}' already exists")
    spec = FrontendDesignSpec(**payload.model_dump())
    db.add(spec)
    db.commit()
    db.refresh(spec)
    return _to_response(spec)


@router.patch("/{slug}", response_model=SpecResponse)
async def update_spec(slug: str, payload: SpecUpdate, db: Session = Depends(get_db)):
    spec = db.query(FrontendDesignSpec).filter(FrontendDesignSpec.slug == slug).first()
    if not spec:
        raise HTTPException(status_code=404, detail=f"Spec with slug '{slug}' not found")
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(spec, field, value)
    db.commit()
    db.refresh(spec)
    return _to_response(spec)


def _to_response(spec: FrontendDesignSpec) -> dict:
    return {
        "id": str(spec.id),
        "feature_name": spec.feature_name,
        "slug": spec.slug,
        "status": spec.status,
        "spec_path": spec.spec_path,
        "comp_path": spec.comp_path,
        "description": spec.description,
        "components": spec.components or [],
        "design_tokens": spec.design_tokens or {},
        "visual_polish": spec.visual_polish or {},
        "approved_by": spec.approved_by,
        "approved_at": spec.approved_at,
        "implemented_at": spec.implemented_at,
        "created_at": spec.created_at,
        "updated_at": spec.updated_at,
    }
