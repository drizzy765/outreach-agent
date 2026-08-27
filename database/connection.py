import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from config import settings

logger = logging.getLogger(__name__)
Base = declarative_base()

def _normalize_db_url(url: str) -> str:
    """Normalize database URL for SQLAlchemy asyncpg or sqlite engine."""
    if not url:
        return "sqlite+aiosqlite:///./crm.db"
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url

db_url = _normalize_db_url(settings.database_url)

try:
    engine = create_async_engine(
        db_url,
        echo=False,
        future=True,
        pool_pre_ping=True
    )
except Exception:
    db_url = "sqlite+aiosqlite:///./crm.db"
    engine = create_async_engine(db_url, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_async_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    global engine, AsyncSessionLocal
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info(f"✓ Database tables initialized ({engine.url.drivername}).")
    except Exception as e:
        logger.warning(f"Primary database connection failed ({e}). Switching to local SQLite engine (./crm.db)...")
        fallback_url = "sqlite+aiosqlite:///./crm.db"
        engine = create_async_engine(fallback_url, echo=False, future=True)
        AsyncSessionLocal.configure(bind=engine)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ Local SQLite fallback database initialized successfully (./crm.db).")

