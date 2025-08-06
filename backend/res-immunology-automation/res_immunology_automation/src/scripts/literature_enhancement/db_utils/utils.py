import os
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine, and_

POSTGRES_USER: str = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB: str = os.getenv("POSTGRES_DB")
POSTGRES_HOST: str = os.getenv("POSTGRES_HOST")

SQLALCHEMY_DATABASE_URL: str = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Use a session
session: Session = SessionLocal()

def get_metadata(disease_name: str, target: str, status: str):
    if target:
        return session.query(DiseaseImageMetadata).filter(and_(
            DiseaseImageMetadata.Disease == disease_name,
            DiseaseImageMetadata.Target == target,
            DiseaseImageMetadata.status == status
        )).all()

    return session.query(DiseaseImageMetadata).filter(and_(
            DiseaseImageMetadata.Disease == disease_name,
            DiseaseImageMetadata.status == status
        )).all()


def fetch_rows(table_cls, target: str = None, disease: str = None, status: str = None):
    """
    Fetch rows from a given SQLAlchemy table with optional filters.
    
    Args:
        session (Session): SQLAlchemy session.
        table_cls (Base): SQLAlchemy ORM table class.
        target (str, optional): Target value to filter.
        disease (str, optional): Disease value to filter.
        status (str, optional): Status value to filter.

    Returns:
        List[table_cls]: Filtered rows.

    Raises:
        ValueError: If both target and disease are None.
    """
    if not target and not disease:
        raise ValueError("At least one of 'target' or 'disease' must be specified.")

    filters = []
    vals = {"target": target, "disease": disease, "status": status}
    for k,v in vals.items():
        if v and hasattr(table_cls, k):
            filters.append(getattr(table_cls, k) == v)
    
    rows = session.query(table_cls).filter(and_(*filters)).all()
    #convert sqlAlchemy rows to Dict
    return [
        {column.name: getattr(row, column.name) for column in table_cls.__table__.columns}
        for row in rows
    ]

def update_table_rows(table_cls, update_values: dict, filter_conditions: dict):
    """
    Generic function to update rows in a table.
    
    Args:
        session (Session): SQLAlchemy session.
        table_cls (Base): SQLAlchemy ORM table class.
        update_values (dict): Columns and values to update.
        filter_conditions (dict): Columns and values to filter on.
        
    Returns:
        int: Number of rows updated.
    """
    stmt = update(table_cls).where(
        *[
            getattr(table_cls, key) == value
            for key, value in filter_conditions.items()
        ]
    ).values(**update_values)
    try:
        result = session.execute(stmt)
        session.commit()
    except Exception as e:
        raise e
    return result.rowcount