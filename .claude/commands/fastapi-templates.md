# FastAPI Templates

Generate production-ready FastAPI code for the DHG AI Factory stack: FastAPI, SQLAlchemy 2.0 (async), Pydantic 2.5, PostgreSQL 15 + pgvector.

## Capabilities

**What this command does:** Scaffolds complete, layered FastAPI code — model, schema, repository, service, and endpoint — for new resources in `langgraph_workflows/dhg-agents-cloud/src/`, using async SQLAlchemy 2.0, Pydantic 2.5, and pgvector patterns.

**Use it when you need to:**
- Scaffold a full new resource (model + schema + repository + service + routes) in the LangGraph cloud service
- Set up async database session management with proper commit/rollback lifecycle
- Implement JWT authentication dependencies and OAuth2 password flow
- Add pgvector similarity-search endpoints using L2 distance queries
- Generate pytest-asyncio test fixtures with an in-memory SQLite test database

**Example invocations:**
- `/project:fastapi-templates agent run history endpoint with pgvector similarity search`
- `/project:fastapi-templates user settings CRUD with JWT auth`
- `/project:fastapi-templates async database session setup for the dhg-agents-cloud service`

Use this command when:
- Creating a new FastAPI router, endpoint, or service in `langgraph_workflows/dhg-agents-cloud/src/`
- Adding a new resource (model + schema + repository + service + routes)
- Scaffolding database models with pgvector support
- Implementing authentication dependencies
- Setting up async database session management

$ARGUMENTS — describe what you want to build, e.g. "agent run history endpoint with pgvector similarity search" or "user settings CRUD". If no argument is given, print the project structure layout and patterns as a reference.

---

## Project Layout

All new FastAPI code belongs under:

```
langgraph_workflows/dhg-agents-cloud/src/
├── api/
│   └── v1/
│       ├── endpoints/       # One file per resource
│       └── router.py        # Aggregates all endpoint routers
├── core/
│   ├── config.py            # pydantic-settings BaseSettings
│   ├── database.py          # Async engine + session factory + get_db
│   └── security.py          # JWT creation/verification, password hashing
├── models/                  # SQLAlchemy 2.0 mapped classes
├── schemas/                 # Pydantic 2.5 request/response models
├── repositories/            # Async data access, one class per model
├── services/                # Business logic, calls repositories
└── main.py                  # FastAPI app, lifespan, middleware, routers
```

Do NOT place new code in the legacy `agents/` directory.

---

## Pattern 1 — Application Entry Point

```python
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine, Base
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: tables are managed by Alembic migrations, not create_all
    yield
    await engine.dispose()


app = FastAPI(
    title="DHG AI Factory API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
```

---

## Pattern 2 — Configuration (Pydantic 2.5)

```python
# core/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str                        # postgresql+asyncpg://...
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    API_V1_STR: str = "/api/v1"

    # pgvector
    EMBEDDING_DIMENSION: int = 1536


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---

## Pattern 3 — Async Database Session (SQLAlchemy 2.0)

```python
# core/database.py
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields a session and handles commit/rollback."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

---

## Pattern 4 — SQLAlchemy 2.0 Model with pgvector

```python
# models/item.py
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.config import get_settings

settings = get_settings()


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(nullable=True)
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(settings.EMBEDDING_DIMENSION), nullable=True
    )
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="items")
```

---

## Pattern 5 — Pydantic 2.5 Schemas

```python
# schemas/item.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ItemBase(BaseModel):
    title: str
    content: Optional[str] = None


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class ItemRead(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime


class ItemList(BaseModel):
    items: list[ItemRead]
    total: int
```

Pydantic 2.5 notes:
- Use `model_config = ConfigDict(from_attributes=True)` instead of `class Config: orm_mode = True`
- Use `.model_dump()` instead of `.dict()`
- Use `.model_dump(exclude_unset=True)` for partial updates

---

## Pattern 6 — Generic Async Repository

```python
# repositories/base_repository.py
from typing import Any, Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]) -> None:
        self.model = model

    async def get(self, db: AsyncSession, id: int) -> Optional[ModelType]:
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalars().first()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> Sequence[ModelType]:
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return result.scalars().all()

    async def create(self, db: AsyncSession, obj_in: Any) -> ModelType:
        data = obj_in.model_dump() if hasattr(obj_in, "model_dump") else dict(obj_in)
        db_obj = self.model(**data)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, db_obj: ModelType, obj_in: Any
    ) -> ModelType:
        data = (
            obj_in.model_dump(exclude_unset=True)
            if hasattr(obj_in, "model_dump")
            else dict(obj_in)
        )
        for field, value in data.items():
            setattr(db_obj, field, value)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, id: int) -> bool:
        obj = await self.get(db, id)
        if obj is None:
            return False
        await db.delete(obj)
        return True
```

```python
# repositories/item_repository.py
from typing import Optional, Sequence

from pgvector.sqlalchemy import Vector
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item
from app.repositories.base_repository import BaseRepository


class ItemRepository(BaseRepository[Item]):

    async def get_by_owner(
        self, db: AsyncSession, owner_id: int, *, skip: int = 0, limit: int = 100
    ) -> Sequence[Item]:
        result = await db.execute(
            select(Item)
            .where(Item.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def similarity_search(
        self,
        db: AsyncSession,
        query_embedding: list[float],
        *,
        limit: int = 10,
        owner_id: Optional[int] = None,
    ) -> Sequence[Item]:
        """Return items ordered by L2 distance to query_embedding."""
        stmt = select(Item).order_by(Item.embedding.l2_distance(query_embedding))
        if owner_id is not None:
            stmt = stmt.where(Item.owner_id == owner_id)
        result = await db.execute(stmt.limit(limit))
        return result.scalars().all()


item_repository = ItemRepository(Item)
```

---

## Pattern 7 — Service Layer

```python
# services/item_service.py
from typing import Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item
from app.repositories.item_repository import item_repository
from app.schemas.item import ItemCreate, ItemUpdate


class ItemService:

    async def get(self, db: AsyncSession, id: int) -> Optional[Item]:
        return await item_repository.get(db, id)

    async def list_for_owner(
        self, db: AsyncSession, owner_id: int, *, skip: int = 0, limit: int = 100
    ) -> Sequence[Item]:
        return await item_repository.get_by_owner(db, owner_id, skip=skip, limit=limit)

    async def create(
        self, db: AsyncSession, item_in: ItemCreate, owner_id: int
    ) -> Item:
        data = item_in.model_dump()
        data["owner_id"] = owner_id
        from app.schemas.item import ItemCreate as _IC
        return await item_repository.create(db, _IC.model_validate(data))

    async def update(
        self, db: AsyncSession, id: int, item_in: ItemUpdate, requester_id: int
    ) -> Item:
        item = await item_repository.get(db, id)
        if item is None:
            raise ValueError(f"Item {id} not found")
        if item.owner_id != requester_id:
            raise PermissionError("Not authorized to update this item")
        return await item_repository.update(db, item, item_in)

    async def delete(
        self, db: AsyncSession, id: int, requester_id: int
    ) -> None:
        item = await item_repository.get(db, id)
        if item is None:
            raise ValueError(f"Item {id} not found")
        if item.owner_id != requester_id:
            raise PermissionError("Not authorized to delete this item")
        await item_repository.delete(db, id)

    async def similarity_search(
        self,
        db: AsyncSession,
        query_embedding: list[float],
        *,
        limit: int = 10,
        owner_id: Optional[int] = None,
    ) -> Sequence[Item]:
        return await item_repository.similarity_search(
            db, query_embedding, limit=limit, owner_id=owner_id
        )


item_service = ItemService()
```

---

## Pattern 8 — Router and Endpoints

```python
# api/v1/endpoints/items.py
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.item import ItemCreate, ItemList, ItemRead, ItemUpdate
from app.services.item_service import item_service

router = APIRouter(prefix="/items", tags=["items"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_in: ItemCreate,
    db: DbDep,
    current_user: CurrentUser,
):
    try:
        return await item_service.create(db, item_in, owner_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/", response_model=ItemList)
async def list_items(
    db: DbDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    items = await item_service.list_for_owner(
        db, owner_id=current_user.id, skip=skip, limit=limit
    )
    return ItemList(items=list(items), total=len(items))


@router.get("/{item_id}", response_model=ItemRead)
async def get_item(item_id: int, db: DbDep, current_user: CurrentUser):
    item = await item_service.get(db, item_id)
    if item is None or item.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.patch("/{item_id}", response_model=ItemRead)
async def update_item(
    item_id: int,
    item_in: ItemUpdate,
    db: DbDep,
    current_user: CurrentUser,
):
    try:
        return await item_service.update(db, item_id, item_in, requester_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: int, db: DbDep, current_user: CurrentUser):
    try:
        await item_service.delete(db, item_id, requester_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
```

```python
# api/v1/router.py
from fastapi import APIRouter

from app.api.v1.endpoints import items, users, auth

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(items.router)
```

---

## Pattern 9 — Authentication Dependencies

```python
# core/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def create_access_token(subject: int | str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return jwt.encode({"sub": str(subject), "exp": expire}, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_password_hash(plain: str) -> str:
    return pwd_context.hash(plain)
```

```python
# api/dependencies.py
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.repositories.user_repository import user_repository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    subject = decode_access_token(token)
    if subject is None:
        raise credentials_exception

    user = await user_repository.get(db, int(subject))
    if user is None:
        raise credentials_exception
    return user
```

---

## Pattern 10 — Testing (pytest-asyncio)

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def engine():
    _engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield _engine
    await _engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()
```

```python
# tests/test_items.py
import pytest


@pytest.mark.asyncio
async def test_create_item(client, auth_headers):
    response = await client.post(
        "/api/v1/items/",
        json={"title": "Test item", "content": "Some content"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test item"
    assert "id" in data
```

---

## Implementation Checklist

When adding a new resource, complete every step — no partial scaffolding:

- [ ] SQLAlchemy model in `models/<resource>.py` with all columns and relationships
- [ ] Pydantic schemas in `schemas/<resource>.py`: Base, Create, Update, Read, List
- [ ] Repository in `repositories/<resource>_repository.py` extending `BaseRepository`
- [ ] Service in `services/<resource>_service.py` with business logic and authorization checks
- [ ] Endpoint file in `api/v1/endpoints/<resource>.py` with all CRUD routes
- [ ] Router registered in `api/v1/router.py`
- [ ] Alembic migration generated (`alembic revision --autogenerate -m "add <resource>"`)
- [ ] Tests in `tests/test_<resource>.py` covering create, read, update, delete, auth failure

---

## Project-Specific Conventions

- **SQLAlchemy 2.0**: Use `Mapped` and `mapped_column` for all columns. Never use the legacy `Column()` style.
- **Pydantic 2.5**: Use `model_config = ConfigDict(...)`, `.model_dump()`, `.model_validate()`. Never use the Pydantic v1 API.
- **pgvector**: Import `from pgvector.sqlalchemy import Vector`. Use `.l2_distance()` for nearest-neighbour queries. Index vectors with `CREATE INDEX ... USING ivfflat`.
- **Sessions**: Never call `session.commit()` inside a repository. The `get_db` dependency owns the transaction boundary.
- **No sync drivers**: Always use `asyncpg` for PostgreSQL and `aiosqlite` for tests.
- **Error mapping**: Raise `ValueError` for not-found / business errors and `PermissionError` for authorization failures in services. Convert to `HTTPException` only at the endpoint layer.
- **DHG container network**: The service connects to PostgreSQL at `dhg-postgres:5432` on `dhgaifactory35_dhg-network`. The registry API is at `http://dhg-registry-api:8000`.

---

## Common Pitfalls to Avoid

- **Blocking calls in async routes**: Do not use synchronous ORMs, `requests`, or `time.sleep` inside async functions.
- **Business logic in endpoints**: Route handlers should call a service method and map exceptions to HTTP status codes — nothing more.
- **Missing `expire_on_commit=False`**: Required on `async_sessionmaker` when returning ORM objects after commit.
- **`obj.dict()` in Pydantic 2.5**: Use `obj.model_dump()`. The `.dict()` method is removed.
- **`declarative_base()` in SQLAlchemy 2.0**: Use `class Base(DeclarativeBase): pass` instead.
- **`datetime.utcnow()`**: Use `datetime.now(timezone.utc)` — `utcnow()` is deprecated in Python 3.12.
