import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy import and_, update
from typing import Optional

# Load DB credentials
POSTGRES_USER: str = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB: str = os.getenv("POSTGRES_DB")
POSTGRES_HOST: str = os.getenv("POSTGRES_HOST")

# Async DB URL
SQLALCHEMY_DATABASE_URL: str = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}"

# Create async engine and session
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

# -----------------------------
# Async function: Get metadata
# -----------------------------
async def aget_metadata(disease_name: str, target: Optional[str], status: str):
    stmt = select(LiteratureImagesAnalysis).where(
        and_(
            LiteratureImagesAnalysis.Disease == disease_name,
            LiteratureImagesAnalysis.status == status
        )
    )
    if target:
        stmt = stmt.where(LiteratureImagesAnalysis.Target == target)

    async with AsyncSessionLocal() as session:
        result = await session.execute(stmt)
    return result.scalars().all()

# -----------------------------
# Async function: Fetch rows
# -----------------------------
async def afetch_rows(table_cls, disease: str = None, target: str = None, status: str = None):
    if not target and not disease:
        raise ValueError("At least one of 'target' or 'disease' must be specified.")

    filters = []
    vals = {"target": target, "disease": disease, "status": status}
    try:
        for k, v in vals.items():
            if v and hasattr(table_cls, k):
                filters.append(getattr(table_cls, k) == v)

        stmt = select(table_cls).where(and_(*filters))
        async with AsyncSessionLocal() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                {col.name: getattr(row, col.name) for col in table_cls.__table__.columns}
                for row in rows
            ] if rows else []
    
    except Exception as e:
        logger.error(f"Error while fetching records from: {table_cls.__name__}")
        raise 
    
# -----------------------------
# Async function: Update rows
# -----------------------------
async def aupdate_table_rows(table_cls, update_values: dict, filter_conditions: dict):
    stmt = update(table_cls).where(
        *[
            getattr(table_cls, key) == value
            for key, value in filter_conditions.items()
        ]
    ).values(**update_values)
    
    async with AsyncSessionLocal() as session:
        
        try:
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount
        except Exception as e:
            await session.rollback()
            raise e
