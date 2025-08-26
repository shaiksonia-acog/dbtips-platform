from db.models import LiteratureImagesAnalysis
from sqlalchemy import select, union_all, and_, literal
from typing import List, Dict, Any


def fetch_literature_images(db, disease: str="no-disease", target: str="no-target") -> List[Dict[str, Any]]:
    """
    Fetch literature images analysis data by disease and target from the database.
    Only returns records with status = 'processed'.
    """
    try:
        # Query the literature_images_analysis table for the given disease
        records = db.query(LiteratureImagesAnalysis).filter(
            and_(
                LiteratureImagesAnalysis.disease == disease,
                LiteratureImagesAnalysis.target == target,
                LiteratureImagesAnalysis.status == "processed",
                LiteratureImagesAnalysis.is_disease_pathway == True
            )
        ).all()
        
        # Convert records to dictionary format
        results = []
        for record in records:
            result_dict = {
                "pmid": record.pmid,
                "pmcid": record.pmcid,
                "url": record.url,
                "image_url": record.image_url,
                "image_caption": record.image_caption,
                "genes": record.genes.split(","),
                "insights": record.insights,
                "drugs": record.drugs,
                "keywords": record.keywords,
                "process": record.process,
            }
            results.append(result_dict)
        
        print(f"Found {len(results)} literature images records for disease: {disease}")
        return results
    except Exception as e:
        raise e
