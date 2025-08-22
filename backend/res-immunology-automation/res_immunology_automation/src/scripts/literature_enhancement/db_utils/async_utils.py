# ===== Updated async_utils.py =====
import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy import and_, update, or_
from typing import Optional
from db.models import LiteratureEnhancementPipelineStatus, ErrorManagement
from datetime import datetime
from literature_enhancement.config import LOGGING_LEVEL
logging.basicConfig(level=LOGGING_LEVEL)
module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
logger = logging.getLogger(module_name)

# Load DB credentials
POSTGRES_USER: str = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD") 
POSTGRES_DB: str = os.getenv("POSTGRES_DB")
POSTGRES_HOST: str = os.getenv("POSTGRES_HOST")

# Async DB URL
SQLALCHEMY_DATABASE_URL: str = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}"

# Create async engine and session
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

# -----------------------------
# Async function: Get metadata
# -----------------------------
async def aget_metadata(disease_name: str, target: Optional[str], status: str):
    from db.models import LiteratureImagesAnalysis
    
    stmt = select(LiteratureImagesAnalysis).where(
        and_(
            LiteratureImagesAnalysis.disease == disease_name,
            LiteratureImagesAnalysis.status == status
        )
    )
    if target:
        stmt = stmt.where(LiteratureImagesAnalysis.target == target)
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(stmt)
        return result.scalars().all()

# -----------------------------
# Async function: Fetch rows
# -----------------------------
async def afetch_rows(table_cls, disease: str = None, target: str = None, status = None):
    if not target and not disease:
        raise ValueError("At least one of 'target' or 'disease' must be specified.")
    
    filters = []
    vals = {"target": target, "disease": disease}
    
    try:
        # Handle regular string fields (target, disease)
        for k, v in vals.items():
            if v and hasattr(table_cls, k):
                filters.append(getattr(table_cls, k) == v)
        
        # Handle status separately to support multiple values
        if status and hasattr(table_cls, 'status'):
            if isinstance(status, list):
                # Use IN clause for multiple statuses
                filters.append(getattr(table_cls, 'status').in_(status))
            else:
                # Use equality for single status
                filters.append(getattr(table_cls, 'status') == status)
        
        stmt = select(table_cls).where(and_(*filters))
        async with AsyncSessionLocal() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                {col.name: getattr(row, col.name) for col in table_cls.__table__.columns}
                for row in rows
            ] if rows else []
    
    except Exception as e:
        logger.error(f"Error while fetching records from: {table_cls.__tablename__}")
        raise
        
# -----------------------------
# NEW: Async function: Fetch rows with null checks (MOVED FROM TABLE ANALYZER)
# -----------------------------
async def afetch_rows_with_null_check(table_cls, disease: str, target: Optional[str] = None, 
                                     null_columns: Optional[list] = None):
    """
    Fetch rows where specified columns are null or empty (unprocessed records)
    
    Args:
        table_cls: SQLAlchemy model class
        disease: Disease name to filter by
        target: Optional target name to filter by
        null_columns: List of column names to check for null/empty values. 
                     Defaults to ['analysis', 'keywords']
    
    Returns:
        List of dictionaries representing the rows
    """
    if not disease:
        raise ValueError("Disease must be specified.")
    
    # Default columns to check for null/empty values
    if null_columns is None:
        null_columns = ['analysis', 'keywords']
    
    filters = [table_cls.disease == disease]
    
    # Build null/empty check conditions for specified columns
    null_conditions = []
    for col_name in null_columns:
        if hasattr(table_cls, col_name):
            col = getattr(table_cls, col_name)
            null_conditions.extend([
                col.is_(None),
                col == ''
            ])
    
    # Add null check conditions (OR logic - if any column is null/empty)
    if null_conditions:
        filters.append(or_(*null_conditions))
    
    # Add target filter if provided
    if target:
        filters.append(table_cls.target == target)

    try:
        stmt = select(table_cls).where(and_(*filters))
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                {col.name: getattr(row, col.name) for col in table_cls.__table__.columns}
                for row in rows
            ] if rows else []
    
    except Exception as e:
        logger.error(f"Error while fetching unprocessed records from: {table_cls.__name__}")
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

# -----------------------------
# Check Pipeline Status
# -----------------------------
async def check_pipeline_status(
    disease: str, 
    target: str, 
    pipeline_type: str
) -> str | None:
    """
    Check the current status of a pipeline
    
    Args:
        disease: Disease name
        target: Target name
        pipeline_type: Type of pipeline (e.g., 'literature_extraction', 'image_analysis', etc.)
    
    Returns:
        str | None: Current pipeline status or None if no record exists
    """
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(LiteratureEnhancementPipelineStatus).where(
                and_(
                    LiteratureEnhancementPipelineStatus.disease == disease,
                    LiteratureEnhancementPipelineStatus.target == target,
                    LiteratureEnhancementPipelineStatus.pipeline_type == pipeline_type
                )
            )
            
            result = await session.execute(stmt)
            existing_record = result.scalar_one_or_none()
            
            if existing_record:
                logger.info(f"Pipeline status for {disease}-{target} for pipeline: {pipeline_type.upper()}: {existing_record.pipeline_status}")
                return existing_record.pipeline_status
            else:
                logger.info(f"No pipeline status record found for {disease}-{target} for pipeline: {pipeline_type.upper()}")
                return None
                
    except Exception as e:
        logger.error(f"Failed to check pipeline status for {disease}-{target}-{pipeline_type}: {e}")
        return None

# -----------------------------
# Generic Pipeline Status Update (REFACTORED)
# -----------------------------
async def create_pipeline_status(
    disease: str, 
    target: str, 
    pipeline_type: str,
    status: str
) -> bool:
    """
    Generic function to create or update pipeline status in literature_enhancement_pipeline_status table
    
    Args:
        disease: Disease name
        target: Target name
        pipeline_type: Type of pipeline (e.g., 'literature_extraction', 'image_analysis', etc.)
        status: Pipeline status 
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        async with AsyncSessionLocal() as session:
            # Check if record exists
            stmt = select(LiteratureEnhancementPipelineStatus).where(
                and_(
                    LiteratureEnhancementPipelineStatus.disease == disease,
                    LiteratureEnhancementPipelineStatus.target == target,
                    LiteratureEnhancementPipelineStatus.pipeline_type == pipeline_type
                )
            )
            
            result = await session.execute(stmt)
            existing_record = result.scalar_one_or_none()
            
            if existing_record:
                # Update existing record
                existing_record.pipeline_status = status
                logger.info(f"Updated pipeline status for {disease}-{target}-{pipeline_type} to '{status}'")
            else:
                # Create new record
                new_record = LiteratureEnhancementPipelineStatus(
                    disease=disease,
                    target=target,
                    pipeline_type=pipeline_type,
                    pipeline_status=status
                )
                session.add(new_record)
                logger.info(f"Created new pipeline status record for {disease}-{target}-{pipeline_type} with status '{status}'")
            
            await session.commit()
            return True
            
    except Exception as e:
        logger.error(f"Failed to update pipeline status for {disease}-{target}-{pipeline_type}: {e}")
        return False

# -----------------------------
# Log Error to Error Management
# -----------------------------
async def log_error_to_management(
    job_details: str,
    endpoint: str,
    error_description: str
) -> bool:
    """
    Log error to error_management table
    
    Args:
        job_details: Details about the job that failed
        endpoint: Endpoint where error occurred
        error_description: Description of the error
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        async with AsyncSessionLocal() as session:
            error_record = ErrorManagement(
                job_details=job_details,
                endpoint=endpoint,
                error_description=error_description,
                error_encountered_time=datetime.utcnow()
            )
            
            session.add(error_record)
            await session.commit()
            logger.info(f"Logged error to management table: {job_details}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to log error to management table: {e}")
        return False

async def fetch_total_rows_count(table_cls, disease: str, target: str)->int:
    """
    Fetch total rows for a given disease and optional target
    
    Args:
        table_cls: SQLAlchemy model class
        disease: Disease name to filter by
        target: Optional target name to filter by
    
    Returns:
        List of dictionaries representing the rows
    """
    async with AsyncSessionLocal() as session:
        total_stmt = select(table_cls).where(and_(table_cls.disease == disease, table_cls.target == target))
        total_result = await session.execute(total_stmt)
        total_records = total_result.scalars().all()
        return total_records
