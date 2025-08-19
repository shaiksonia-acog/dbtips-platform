from sqlalchemy import Column, Sequence, String,Integer, DateTime, PrimaryKeyConstraint, Text, Boolean
from .database import Base


class Target(Base):
    __tablename__ = "target"

    id = Column(String, primary_key=True, index=True)
    file_path = Column(String, nullable=False)  # Required attribute


class Disease(Base):
    __tablename__ = "disease"

    id = Column(String, primary_key=True, index=True)
    file_path = Column(String, nullable=False)  # Required attribute


class TargetDisease(Base):
    __tablename__ = "target_disease"

    id = Column(String, primary_key=True, index=True)
    file_path = Column(String, nullable=False)  # Required attribute

class DiseaseDossierStatus(Base):
    __tablename__ = "disease_dossier_status"

    job_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    disease = Column(String, nullable=False, unique=True)
    status = Column(String, nullable=False)
    error_count = Column(Integer, default=0, nullable=False)
    creation_time = Column(DateTime(timezone=True), nullable=True)  
    submission_time = Column(DateTime(timezone=True), nullable=True)  
    processed_time = Column(DateTime(timezone=True), nullable=True) 

class ErrorManagement(Base):
    __tablename__ = "error_management"

    index = Column(Integer, primary_key=True, autoincrement=True)
    job_details = Column(String, index=True)
    endpoint = Column(String, nullable=True)
    error_description = Column(String, nullable=True)
    error_encountered_time = Column(DateTime(timezone=True), nullable=True) 

class TargetDossierStatus(Base):
    __tablename__ = "target_dossier_status"

    job_id = Column(Integer, Sequence('job_id_seq'),  nullable=False, autoincrement=True, index=True)
    target = Column(String, nullable=False)
    disease = Column(String, nullable=True)
    status = Column(String, nullable=False)
    error_count = Column(Integer, default=0)
    creation_time = Column(DateTime(timezone=True), nullable=True)  
    submission_time = Column(DateTime(timezone=True), nullable=True)  
    processed_time = Column(DateTime(timezone=True), nullable=True) 
    __table_args__ = (
        PrimaryKeyConstraint('target', 'disease', name='target-disease-pk'),
    )

class Admin(Base):
    __tablename__ = "admin"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    username = Column(String, unique=True, nullable=False)  # Unique and required
    password = Column(String, nullable=False)  # Required

class ArticlesMetadata(Base):
    __tablename__ = 'articles_metadata'

    disease = Column(String, default="no-disease")
    target = Column(String, default="no-target")
    pmid = Column(String, nullable=False)
    pmcid = Column(String, nullable=False)
    title = Column(Text)
    url = Column(String)
    raw_full_text = Column(Text)

    __table_args__ = (
        PrimaryKeyConstraint('disease', 'pmid'),
    )

class LiteratureImagesAnalysis(Base):
    __tablename__ = 'literature_images_analysis'

    index = Column(Integer, primary_key=True, autoincrement=True)
    pmid = Column(String, nullable=False)
    disease = Column(String, nullable=False, default="no-disease")
    target = Column(String, nullable=False, default="no-target")
    url = Column(String)
    pmcid = Column(String)
    image_url = Column(String)
    image_caption = Column(Text)
    genes = Column(Text)
    insights = Column(Text)
    drugs = Column(Text)
    keywords = Column(Text)
    process = Column(Text)
    is_disease_pathway = Column(Boolean)  # NEW COLUMN: True/False for disease pathway relevance
    error_message = Column(Text)
    status = Column(String)

class LiteratureTablesAnalysis(Base):
    __tablename__ = 'literature_tables_analysis'

    index = Column(Integer, primary_key=True, autoincrement=True)
    pmid = Column(String, nullable=False)
    disease = Column(String, nullable=False, default="no-disease")
    target = Column(String, nullable=False, default="no-target")
    url = Column(String)
    pmcid = Column(String, nullable=False)
    table_description = Column(String)
    table_schema = Column(Text)  # renamed from "table/suppl schema schema" to valid identifier
    analysis = Column(Text)
    keywords = Column(Text)

class LiteratureSupplementaryMaterialsAnalysis(Base):
    __tablename__ = 'literature_supplmentary_materials_analysis'

    index = Column(Integer, primary_key=True, autoincrement=True)
    pmid = Column(String, nullable=False)
    disease = Column(String, nullable=False, default="no-disease" )
    target = Column(String, nullable=False, default="no-target")
    url = Column(String)
    pmcid = Column(String, nullable=False)
    description = Column(String)
    file_names = Column(Text)  # renamed from "table/suppl schema schema" to valid identifier
    analysis = Column(Text)
    keywords = Column(Text)
    title = Column(Text, nullable=True)  # <-- This is the new field you need to add

class LiteratureEnhancementPipelineStatus(Base):
    __tablename__ = 'literature_enhancement_pipeline_status'

    # composite key fields
    disease = Column(String, nullable=False)
    target = Column(String, nullable=False)
    pipeline_type = Column(String, nullable=False)

    # pipeline status (initially empty, later updated)
    pipeline_status = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint('disease', 'target', 'pipeline_type', name='uq_disease_target_pipeline'),
    )

