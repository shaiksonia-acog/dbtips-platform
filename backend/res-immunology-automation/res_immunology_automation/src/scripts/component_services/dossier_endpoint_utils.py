from datetime import datetime
from typing import List, Dict
from sqlalchemy.orm import Session
from db.models import TargetDossierStatus, DiseaseDossierStatus, DossierEndpointStatus
import logging
import tzlocal


def get_endpoints_for_job_type(target: str, disease: str) -> List[str]:
    """Returns list of endpoints based on job type"""
    logging.info(f"Getting endpoints for target='{target}', disease='{disease}'")
    
    if target == "" or target is None:  # Disease only
        if disease == "":
            logging.warning("Both target and disease are empty, returning empty endpoint list")
            return []
        disease_endpoints = [
            'get_evidence_literature_semaphore',
            'get_mouse_studies',
            'get_network_biology_semaphore',
            'get_top_10_literature',
            'get_diseases_profiles',
            'get_indication_pipeline_semaphore',
            'get_kol',
            'get_key_influencers',
            'get_rna_sequence_semaphore',
            'get_diseases_profiles_llm',
            'pgs_catalog_data',
            'get_disease_gtr_data_semaphore',
            'get_disease_ontology',
            'run_enhancement_pipeline',
            'get_literature_images_evidence',
            'get_literature_table_analysis',
            'get_literature_supplementary_materials_analysis'
        ]
        logging.info(f"Disease-only endpoints: {len(disease_endpoints)} endpoints")
        return disease_endpoints
    else:  # Target with or without disease
        target_endpoints = [
            'get_target_details',
            'get_ontology',
            'get_protein_expressions',
            'get_subcellular',
            'get_anatomy',
            'get_protein_structure',
            'get_target_mouse_studies',
            'get_targetability',
            'get_gene_essentiality_map',
            'get_tractability',
            'get_paralogs',
            'get_target_pipeline_all_semaphore',
            'get_evidence_target_literature',
            'search_patents',
            'run_enhancement_pipeline',
            'get_target_literature_images_evidence',
            'get_literature_table_analysis',
            'get_literature_supplementary_materials_analysis'
        ]
        logging.info(f"Target endpoints: {len(target_endpoints)} endpoints")
        return target_endpoints


def create_endpoint_records(db: Session, target_key: str, disease_key: str, endpoints: List[str]):
    """Create endpoint records for the given target-disease combination"""
    logging.info(f"Creating endpoint records for target='{target_key}', disease='{disease_key}'")
    local_time = datetime.now(tzlocal.get_localzone())
    
    for endpoint_name in endpoints:
        endpoint_record = DossierEndpointStatus(
            target=target_key,
            disease=disease_key,
            endpoint_name=endpoint_name,
            status="submitted",
            creation_time=local_time
        )
        db.add(endpoint_record)


def get_friendly_endpoint_name(endpoint_name: str) -> str:
    """Convert technical endpoint names to user-friendly display names"""
    endpoint_mapping = {
        'get_disease_gtr_data_semaphore': 'Genetic Testing Registry',
        'get_disease_ontology': 'Ontology',
        'get_diseases_profiles': 'Disease Profile',
        'get_diseases_profiles_llm': 'Disease Profile LLM Generated',
        'get_evidence_literature_semaphore': 'Literature',
        'get_indication_pipeline_semaphore': 'Therapeutic Pipeline',
        'get_key_influencers': 'Key Influencers',
        'get_kol': 'Key Opinion Leaders',
        'get_literature_images_evidence': 'Literature Images Analysis',
        'get_literature_supplementary_materials_analysis': 'Literature Supplementary Analysis',
        'get_literature_table_analysis': 'Literature Table Analysis',
        'get_mouse_studies': 'Animal Models',
        'get_network_biology_semaphore': 'Disease Pathways',
        'get_rna_sequence_semaphore': 'RNA Seq Data',
        'get_top_10_literature': 'Top 10 Literature',
        'pgs_catalog_data': 'PGS Catalog',
        'run_enhancement_pipeline': 'Literature Enhancement Pipeline',
        'get_target_details': 'Target Description',
        'get_ontology': 'Target Ontology',
        'get_protein_expressions': 'RNA/Protein Expressions',
        'get_subcellular': 'Subcellular Localization',
        'get_anatomy': 'Anatomical Expression',
        'get_protein_structure': 'Protein Structure',
        'get_target_mouse_studies': 'Animal Models',
        'get_targetability': 'Targetability',
        'get_gene_essentiality_map': 'Gene Essentiality Map',
        'get_tractability': 'Target Tractability',
        'get_paralogs': 'Paralogs Analysis',
        'get_target_pipeline_all_semaphore': 'Therapeutic Pipeline',
        'get_evidence_target_literature': 'Literature',
        'search_patents': 'Patents',
        'get_target_literature_images_evidence': 'Literature Images',
    }
    return endpoint_mapping.get(endpoint_name, endpoint_name.replace('_', ' ').title())


def fetch_records_by_status(db: Session, job_type, record_status: str) -> List[Dict[str, str]]:
    """Fetch records by status for progression tracker"""
    all_records = []
    records = db.query(job_type).filter_by(status=record_status).all()
    
    for record in records:
        data = {'target': None, 'disease': None}
        if job_type.__tablename__ == "target_dossier_status":
            data['target'] = record.target
        data['disease'] = record.disease
        data['submission_time'] = record.submission_time
        data['processed_time'] = record.processed_time
        data['error_count'] = record.error_count
        data['id'] = record.job_id
        
        # Add endpoint status if processing or error
        if record_status in ['processing', 'error']:
            endpoint_status = {}
            # Query endpoint status for this record
            target_key = record.target if job_type.__tablename__ == "target_dossier_status" else "no-target"
            disease_key = record.disease
            
            endpoint_records = db.query(DossierEndpointStatus).filter_by(
                target=target_key, 
                disease=disease_key
            ).all()
            
            for endpoint_record in endpoint_records:
                friendly_name = get_friendly_endpoint_name(endpoint_record.endpoint_name)
                endpoint_status[friendly_name] = {
                    'status': endpoint_record.status,
                    'creation_time': endpoint_record.creation_time,
                    'updated_at': endpoint_record.updated_at
                }
            
            if endpoint_status:
                data['endpointStatus'] = endpoint_status
        
        all_records.append(data)
    return all_records