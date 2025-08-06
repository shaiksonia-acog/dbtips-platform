from sqlalchemy import Column, Sequence, String,Integer, DateTime, PrimaryKeyConstraint, Text
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

class DiseaseArticle(Base):
    __tablename__ = 'disease_articles'

    Disease = Column(String, nullable=False)
    Target = Column(String)
    PMID = Column(String, nullable=False)
    PMCID = Column(String)
    Title = Column(Text)
    url = Column(String)
    raw_full_text = Column(Text)

    __table_args__ = (
        PrimaryKeyConstraint('Disease', 'PMID'),
    )

class DiseaseImageAnalysis(Base):
    __tablename__ = 'disease_image_analysis'

    index = Column(Integer, primary_key=True, autoincrement=True)
    PMID = Column(String, nullable=False)
    Disease = Column(String, nullable=False)
    Target = Column(String)
    url = Column(String)
    PMCID = Column(String)
    image_url = Column(String)
    image_caption = Column(Text)
    Genes = Column(Text)
    insights = Column(Text)
    drugs = Column(Text)
    keywords = Column(Text)
    process = Column(Text)
    error_message = Column(Text)
    status = Column(String)

class DiseaseTablesAnalysis(Base):
    __tablename__ = 'disease_tables_analysis'

    index = Column(Integer, primary_key=True, autoincrement=True)
    PMID = Column(String, nullable=False)
    Disease = Column(String, nullable=False)
    Target = Column(String)
    url = Column(String)
    PMCID = Column(String)
    table_description = Column(String)
    table_schema = Column(Text)  # renamed from "table/suppl schema schema" to valid identifier
    Analysis = Column(Text)
    Keywords = Column(Text)

class DiseaseSupplementaryMaterialsAnalysis(Base):
    __tablename__ = 'disease_supplmentary_materials_analysis'

    index = Column(Integer, primary_key=True, autoincrement=True)
    PMID = Column(String, nullable=False)
    Disease = Column(String, nullable=False)
    Target = Column(String)
    url = Column(String)
    PMCID = Column(String)
    description = Column(String)
    file_names = Column(Text)  # renamed from "table/suppl schema schema" to valid identifier
    Analysis = Column(Text)
    Keywords = Column(Text)