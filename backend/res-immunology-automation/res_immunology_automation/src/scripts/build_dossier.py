from db.database import get_db, Base # , engine, , SessionLocal
from db.models import DiseaseDossierStatus, ErrorManagement, TargetDossierStatus

from api_models import DiseasesRequest, DiseaseRequest, TargetOnlyRequest, TargetRequest
from api import get_evidence_literature_semaphore, get_mouse_studies, \
                get_network_biology_semaphore, get_top_10_literature, \
                get_diseases_profiles, get_indication_pipeline_semaphore, \
                get_kol, get_key_influencers, get_rna_sequence_semaphore, \
                get_disease_ontology, get_diseases_profiles_llm, get_target_details, \
                get_ontology, get_protein_expressions, get_subcellular, \
                get_anatomy, get_protein_structure, get_target_mouse_studies, \
                get_targetability, get_gene_essentiality_map, get_tractability, \
                get_paralogs, get_target_pipeline_all_semaphore, get_evidence_target_literature, \
                search_patents, get_complete_indication_pipeline, get_disease_gtr_data_semaphore, \
                pgs_catalog_data, get_literature_images_evidence, get_target_literature_images_evidence, \
                get_literature_table_analysis, get_literature_supplementary_materials_analysis

from literature_enhancement.enhancement_runner import run_enhancement_pipeline
                
import logging
import time
import asyncio
from graphrag_service import get_redis
from fastapi import HTTPException
from sqlalchemy.sql import func
from sqlalchemy import select, union_all, and_, literal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import update, String
import os, sys
import tzlocal
from datetime import datetime, timezone

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/build_dossier.log",  # Log file location
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

task_started = False
WAIT_TIME = 200

POSTGRES_USER: str = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB: str = os.getenv("POSTGRES_DB")
POSTGRES_HOST: str = os.getenv("POSTGRES_HOST")
error_count_threshold = 3
if any(var is None for var in [POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST]):
    logging.info("Connection parameters not configured properly")
    sys.exit()

# Define the PostgreSQL database URL using environment variables
SQLALCHEMY_DATABASE_URL: str = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}"

engine = create_async_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession
)

async def create_models():
    # This will create the tables for all models defined with Base
    # Base.metadata.create_all(bind=engine)
    async with engine.begin() as conn:  # `engine.begin()` ensures the connection is properly initialized
        await conn.run_sync(Base.metadata.create_all)

async def fetch_processing_records(db):

    processing_records = None
    disease_result = await db.execute(
        select(DiseaseDossierStatus).where(DiseaseDossierStatus.status == "processing")
    )
    disease_processing_records = disease_result.scalars().all()

    target_result = await db.execute(
        select(TargetDossierStatus).where(TargetDossierStatus.status == "processing")
    )
    target_processing_records = target_result.scalars().all()
    
    if len(target_processing_records) > 0:
        trecord = target_processing_records[0]
        processing_records = trecord.target+'_'+trecord.disease
    
    if len(disease_processing_records) > 0:
        processing_records = disease_processing_records[0].disease

    return processing_records

async def fetch_pending_jobs(db):
    pending_jobs = {}
    disease_query = select(DiseaseDossierStatus.job_id,
        DiseaseDossierStatus.job_id.label("disease_job_id"),
        literal(None, type_=String).label("target"),
        DiseaseDossierStatus.disease.label("disease"),
        DiseaseDossierStatus.status.label("status"),
        DiseaseDossierStatus.error_count.label("error_count"),
        DiseaseDossierStatus.creation_time.label("creation_time")
        ).where(
            and_(
                DiseaseDossierStatus.status.in_(["error", "submitted"]),
                DiseaseDossierStatus.error_count < error_count_threshold)
        )
    
    target_query = select(TargetDossierStatus.job_id,
        TargetDossierStatus.job_id.label("job_id"),
        TargetDossierStatus.target.label("target"),
        TargetDossierStatus.disease.label("disease"),
        TargetDossierStatus.status.label("status"),
        TargetDossierStatus.error_count.label("error_count"),
        TargetDossierStatus.creation_time.label("creation_time")

        ).where(
            and_(
                TargetDossierStatus.status.in_(["error", "submitted"]),
                TargetDossierStatus.error_count < error_count_threshold
            )
        )
    
    combined_query = union_all(disease_query, target_query).order_by("creation_time")
    
    result =  await db.execute(combined_query)
    column_names = result.keys()
    pending_records = result.fetchall()

    if pending_records:
        for record in pending_records:
            record_dict = dict(zip(column_names, record))

            # Use named attribute access with dictionary keys
            if record_dict.get("target") is not None:
                job_id = 't' + str(record.job_id)
                pending_jobs[job_id] = {"target": record.target, "disease": record.disease, "error_count": record.error_count}
            else:
                job_id = 'd' + str(record.disease_job_id)
                pending_jobs[job_id] = {"target": None, "disease": record.disease, "error_count": record.error_count}
    return pending_jobs

async def fetch_error_count(db, **values):
    disease = values.get('disease')
    target = values.get('target', None)
    if target is None:
        query = select(DiseaseDossierStatus).where(
            DiseaseDossierStatus.disease == disease)
        
    else:
        query = select(TargetDossierStatus).where(
            and_(
        TargetDossierStatus.disease == disease,
        TargetDossierStatus.target == target
            )
        )
    
    result =  await db.execute(query)
    
    pending_records = result.scalars().all()
    
    if pending_records:
        error_count = pending_records[0].error_count
    return error_count

async def update_record_status(db, table, **values): 
    disease = values.get('disease')
    target = values.get('target', None)
    if target is None:
        params = {k:v for k,v in values.items() if k not in ['disease','target']}
        update_stmt = (
            update(table)
            .where(table.disease == disease)
            .values(**params)
        )

        logging.info(f"updating status for Disease Record for {disease} to {params['status']}")
    
    else:
        params = {k: v for k, v in values.items() if k not in ['disease', 'target']}

        update_stmt = (
            update(table)
            .where(and_(table.disease == disease, table.target == target))
            .values(**params)
        )

        logging.info(f"updating status for Target Record for {target}-{disease} to {params['status']}")

    await db.execute(update_stmt) 
    await db.commit()
    
async def build_dossier():
    logging.info("dossier started")
    global task_started
    if task_started:
        return  # Prevent multiple instances from starting
    task_started = True

    # db = get_db()
    while True:

        async with SessionLocal() as db:
            logging.info("connection created")
            processing_records = await fetch_processing_records(db)

            # processing_records = [record for record in processing_records if record]
            logging.info(f"Processing jobs: {processing_records}")
            
            try:
                if not processing_records:
                    pending_jobs = await fetch_pending_jobs(db)
                    logging.info(f"pending jobs: {pending_jobs}")
                    for job_id, job in pending_jobs.items():
                        local_time = datetime.now(tzlocal.get_localzone())    
                        values = {'status': 'processing', 'submission_time': local_time}
                        
                        if job['target'] is None:
                            job_type = DiseaseDossierStatus
                            values['disease'] = job['disease']
                        else:
                            job_type = TargetDossierStatus
                            values['target'] = job['target']
                            values['disease'] = job['disease']
                        logging.info(f"processing jobs: {job}")

                        #change the status of current building disease to processing and processing_time
                        await update_record_status(db, job_type, **values)
                        
                        # run all endpoints for the disease
                        build_status, endpoint, e= await run_endpoints(values)
                        local_time = datetime.now(tzlocal.get_localzone())

                        # update the status and processed_time according to the build status
                        if build_status != 'error':
                            values.update({'status':build_status, 'processed_time':local_time})
                            await update_record_status(db, job_type, **values)
                            
                        else:
                            # update the corresponding status record to error
                            error_count = job['error_count'] + 1
                            values.update({'status':build_status, 'processed_time':local_time, 'error_count': error_count})
                            await update_record_status(db, job_type, **values)
                            
                            # make an entry in error management table
                            new_record = ErrorManagement(job_details=job_id,
                                    endpoint=endpoint, error_description=e, error_encountered_time=local_time)  # Create a new instance of the identified model
                            db.add(new_record)  # Add the new record to the session

                            await db.commit()
                        logging.info(f"updated status: {job}")

                await asyncio.sleep(WAIT_TIME)
            except Exception as e:
                logging.error(f"Error in build_dossier: {e}")

            finally:
                await db.close()
                logging.info("connection closed")
        break

async def run_endpoints(job_data):
    
    try:
        db = next(get_db())
        redis = get_redis()
        logging.info("="*80)
        logging.info("\t\t\tconnection created in end points")

        # Define endpoint categories 
        diseases_only_endpoints = [
            get_evidence_literature_semaphore, 
            get_mouse_studies, 
            get_network_biology_semaphore, 
            get_top_10_literature, 
            get_diseases_profiles, 
            get_indication_pipeline_semaphore, 
            get_kol, 
            get_key_influencers, 
            get_rna_sequence_semaphore,
            get_diseases_profiles_llm,
            # get_complete_indication_pipeline,
            pgs_catalog_data,
            get_disease_gtr_data_semaphore,
        
        ]

        disease_only_endpoints = [
            get_disease_ontology,
            run_enhancement_pipeline,
            get_literature_images_evidence,
            get_literature_table_analysis,
            get_literature_supplementary_materials_analysis
        ]

        target_only_endpoints = [
            get_target_details,
            get_ontology,
            get_protein_expressions,
            get_subcellular,
            get_anatomy,
            get_protein_structure,
            get_target_mouse_studies,
            get_targetability,
            get_gene_essentiality_map,
            get_tractability,
            get_paralogs
        ]

        target_disease_endpoints = [
            # get_target_pipeline_semaphore,
            get_target_pipeline_all_semaphore,
            get_evidence_target_literature,
            search_patents,
            run_enhancement_pipeline,
            get_target_literature_images_evidence,
            get_literature_table_analysis,
            get_literature_supplementary_materials_analysis
        ]
        
        target = job_data.get('target', None)
        disease = job_data.get('disease', None)

        if target is None: # Disease Dossier
            unique_diseases = [disease]

            # Call diseases-only endpoint 
            for endpoint in diseases_only_endpoints:
                try:
                    request_data = DiseasesRequest(diseases=unique_diseases)
                    logging.info(f"\t\t\tCalling {endpoint.__name__} with all diseases: {unique_diseases}")
                    
                    if endpoint.__name__ in ['get_network_biology_semaphore', 'get_indication_pipeline_semaphore']:
                        response = await endpoint(request_data, db=db, build_cache=True)
                    elif endpoint.__name__ in ["get_top_10_literature", 'get_key_influencers']:
                        response = await endpoint(request_data)
                    elif endpoint.__name__ in ['get_evidence_literature_semaphore', 'get_diseases_profiles_llm', 'get_disease_gtr_data_semaphore', 'pgs_catalog_data']:
                        response = await endpoint(request_data, redis=redis, db=db, build_cache=True)
                    elif endpoint.__name__ in ['get_literature_images_evidence']:
                        response = await endpoint(request_data, db=db, build_cache=True)
                    elif endpoint.__name__ in ['get_rna_sequence_semaphore']:
                        response = await endpoint(request_data, redis=redis, db=db, build_cache=True)
                    else:
                        response = await endpoint(request_data, redis=redis, db=db)
                    
                    logging.info("\t\t\t\tResponse received")
                    
                except Exception as e:
                    if isinstance(e, HTTPException) and e.status_code == 404 and 'EFO ID not found' in e.detail:
                        continue 
                    logging.error(f"\t\t\t\tError calling {endpoint.__name__} for {unique_diseases}: {e}")
                    return 'error', endpoint.__name__ if callable(endpoint) else str(endpoint), str(e)
                await asyncio.sleep(5)

            # Call disease-only endpoints
            for disease in unique_diseases:
                for endpoint in disease_only_endpoints:
                    try:
                        if endpoint.__name__ == 'run_enhancement_pipeline':
                            logging.info(f"\t\t\tCalling {endpoint.__name__} for disease: {disease}")
                            response = await endpoint(disease=disease)
                        elif endpoint.__name__ in ['get_literature_images_evidence', 'get_literature_table_analysis', 'get_literature_supplementary_materials_analysis']:
                            request_data = TargetRequest(target="no-target", diseases=[disease])
                            logging.info(f"\t\t\tCalling {endpoint.__name__} for disease: {disease}")
                            response = await endpoint(request_data, db=db, build_cache=True)
                        else:
                            request_data = DiseaseRequest(disease=disease)
                            logging.info(f"\t\t\tCalling {endpoint.__name__} for disease: {disease}")
                            response = await endpoint(request_data, redis=redis, db=db)
                    except Exception as e:
                        logging.error(f"\t\t\t\tError calling {endpoint.__name__} for disease {disease}: {e}")
                        return 'error', endpoint.__name__ if callable(endpoint) else str(endpoint), str(e)
        
        else: # Target Dossier
            # Target-only endpoints
            for endpoint in target_only_endpoints:
                try:
                    request_data = TargetOnlyRequest(target=target)
                    logging.info(f"\t\t\tCalling {endpoint.__name__} for target: {target}")
                    response = await endpoint(request_data, redis=redis, db=db)
                except Exception as e:
                    logging.error(f"\t\t\t\tError calling {endpoint.__name__} for target {target}: {e}")
                    return 'error', endpoint.__name__ if callable(endpoint) else str(endpoint), str(e)

                await asyncio.sleep(5)

            if disease == 'no-disease':
                pipeline_inp = [""]
                oth_inp = []
                literature_inp = ["no-disease"]  # For literature analysis endpoints
            else:
                pipeline_inp = [disease]
                oth_inp = [disease]
                literature_inp = [disease]

            # Target-disease endpoints
            for endpoint in target_disease_endpoints:
                try:
                    if endpoint.__name__ == "get_target_pipeline_all_semaphore":
                        request_data = TargetRequest(target=target, diseases=pipeline_inp)
                        logging.info(f"\t\t\tCalling {endpoint.__name__} for target: {target} and disease: {pipeline_inp}")
                    elif endpoint.__name__ == 'get_target_literature_images_evidence':
                        # Skip target-literature-images endpoint if it's target only (no-disease)
                        if disease == 'no-disease':
                            logging.info(f"\t\t\tSkipping {endpoint.__name__} for target-only case: {target}")
                            continue
                        request_data = TargetRequest(target=target, diseases=oth_inp)
                        logging.info(f"\t\t\tCalling {endpoint.__name__} for target: {target} and disease: {oth_inp}")
                    elif endpoint.__name__ in ['get_literature_table_analysis', 'get_literature_supplementary_materials_analysis']:
                        request_data = TargetRequest(target=target, diseases=literature_inp)
                        logging.info(f"\t\t\tCalling {endpoint.__name__} for target: {target} and disease: {literature_inp}")
                    else:
                        request_data = TargetRequest(target=target, diseases=oth_inp)
                        logging.info(f"\t\t\tCalling {endpoint.__name__} for target: {target} and disease: {oth_inp}")
                    
                    if endpoint.__name__ in ['get_evidence_target_literature']:
                        response = await endpoint(request_data, db=db, build_cache=True)
                    elif endpoint.__name__ in ['get_target_literature_images_evidence', 'get_literature_table_analysis', 'get_literature_supplementary_materials_analysis']:
                        response = await endpoint(request_data, db=db, build_cache=True)
                    elif endpoint.__name__ == 'run_enhancement_pipeline':
                        logging.info(f"\t\t\tCalling {endpoint.__name__} for target: {target} and disease: {disease}")
                        response = await endpoint(disease=disease, target=target)
                    else:
                        response = await endpoint(request_data, redis=redis, db=db, build_cache=True)

                except Exception as e:
                    logging.error(f"\t\t\t\tError calling {endpoint.__name__} for  {target} and {disease}: {e}")
                    return 'error', endpoint.__name__ if callable(endpoint) else str(endpoint), str(e)

            await asyncio.sleep(5)

        await asyncio.sleep(5)
        
        return 'processed', None, None

    finally:
        db.close()
        logging.info("\t\tconnection closed in endpoints")
        logging.info("="*80)


async def main():
    """Main entry point to initialize database and start dossier processing."""
    await create_models()
    await build_dossier()


if __name__ == "__main__":
    # time.sleep(100)
    asyncio.run(main())