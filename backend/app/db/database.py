from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "sqlite+aiosqlite:///./data/gluemigrator.db"

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Add columns introduced after initial schema (no-op if already present)
        from sqlalchemy import text
        try:
            await conn.execute(text(
                "ALTER TABLE migration_job_items ADD COLUMN error_message TEXT"
            ))
        except Exception:
            pass  # column already exists


@asynccontextmanager
async def get_session():
    async with AsyncSessionLocal() as session:
        yield session