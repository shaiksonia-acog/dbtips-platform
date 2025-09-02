from typing import List, Dict, Any
from sqlalchemy import text


def fetch_literature_images_data(db, target: str = "no-target", diseases: List[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch literature images analysis data from the database.
    
    Args:
        db: Database session
        target: Target value to filter by (default: "no-target")
        diseases: List of diseases to filter by (optional)
    
    Returns:
        List of literature images records
    """
    try:
        print("Fetching literature images data from database")
        
        # Base query conditions
        conditions = ["is_disease_pathway='true'", "status='processed'"]
        
        # Check if this is a target-only query (target specified but diseases is ["no-disease"])
        is_target_only = target != "no-target" and diseases == ["no-disease"]
        
        # Add target condition
        conditions.append(f"target='{target}'")
        
        # Add disease condition ONLY if it's not a target-only query
        if not is_target_only and diseases and len(diseases) > 0:
            # Convert diseases to proper format and create IN clause
            formatted_diseases = [disease.replace("_", " ") for disease in diseases]
            diseases_in_clause = "', '".join(formatted_diseases)
            conditions.append(f"disease IN ('{diseases_in_clause}')")
        
        # For target-only queries, add DISTINCT on pmid and image_caption to ensure uniqueness
        if is_target_only:
            # Use DISTINCT ON to get unique combinations of pmid and image_caption
            query = f"""
                SELECT DISTINCT ON (pmid, image_caption) * 
                FROM public.literature_images_analysis 
                WHERE {' AND '.join(conditions)}
                ORDER BY pmid, image_caption, id
            """
        else:
            # Regular query for other cases
            query = f"SELECT * FROM public.literature_images_analysis WHERE {' AND '.join(conditions)}"
        
        print(f"Executing query: {query}")
        
        result = db.execute(text(query))
        records = result.fetchall()
        
        print(f"Found {len(records)} literature images records")
        
        if len(records) == 0:
            print("No records found with the specified criteria")
            return []
        
        # Convert records to dictionary format
        results = []
        for record in records:
            # Generate figid from pmcid and image_url
            figid = ""
            if record.pmcid and record.image_url:
                image_filename = record.image_url.split("/")[-1]
                if "." in image_filename:
                    image_filename = image_filename.rsplit(".", 1)[0]
                figid = f"PMC{record.pmcid}__{image_filename}"
            
            result_dict = {
                "pmid": record.pmid or "",
                "pmcid": record.pmcid or "",
                "url": record.url or "",
                "image_url": record.image_url or "",
                "image_caption": record.image_caption or "",
                "genes": [gene.strip() for gene in record.genes.split(",")] if record.genes else [],               
                "insights": record.insights or "",
                "drugs": record.drugs or "",
                "keywords": record.keywords or "",
                "process": record.process or "",
                "figid": figid,
                "disease": record.disease or "",
                "target": record.target or "",
            }
            results.append(result_dict)
        
        print(f"Processed {len(results)} unique literature images records")
        return results
        
    except Exception as e:
        print(f"Error fetching literature images: {str(e)}")
        return []


def map_literature_to_network_biology_format(literature_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """
    Map literature data to network biology response format, grouped by disease.
    """
    try:
        print("Mapping literature data to network biology format")
        
        grouped_data = {}
        
        for item in literature_data:
            disease = item.get("disease", "unknown").replace("_", " ")
            
            # Initialize disease group if not exists
            if disease not in grouped_data:
                grouped_data[disease] = {"results": []}
            
            # Map fields according to the specification
            mapped_item = {
                "url": item.get("url", ""),
                "pmcid": item.get("pmcid", ""),
                "figtitle": item.get("image_caption", ""),  # image_caption -> figtitle
                "figid": item.get("figid", ""),
                "image_url": item.get("image_url", ""),
                "pmid": item.get("pmid", ""),
                "gene_symbols": item.get("genes", []),  # genes -> gene_symbols
                # Additional fields from literature table
                "drugs": item.get("drugs", ""),
                "keywords": item.get("keywords", ""),
                "process": item.get("process", ""),
                "insights": item.get("insights", ""),
                "data_source": "literature_images"
            }
            
            grouped_data[disease]["results"].append(mapped_item)
        
        print(f"Mapped literature data for {len(grouped_data)} diseases")
        return grouped_data
        
    except Exception as e:
        print(f"Error mapping literature data: {str(e)}")
        return {}


def combine_literature_and_network_biology_data(literature_data: Dict[str, Dict[str, List[Dict[str, Any]]]], 
                                               network_biology_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """
    Combine literature images and network biology data into a single results array per disease.
    """
    try:
        print("Combining literature and network biology data")
        
        combined_data = {}
        
        # Get all unique diseases from both datasets
        all_diseases = set(literature_data.keys()) | set(network_biology_data.keys())
        
        for disease in all_diseases:
            combined_results = []
            
            # Add literature images data (with additional fields)
            if disease in literature_data:
                lit_results = literature_data[disease].get("results", [])
                for item in lit_results:
                    if "data_source" not in item:
                        item["data_source"] = "literature_images"
                    combined_results.append(item)
            
            # Add network biology data (normalize format to match literature structure)
            if disease in network_biology_data:
                nb_results = network_biology_data[disease]
                for item in nb_results:
                    normalized_item = {
                        "url": item.get("url", ""),
                        "pmcid": item.get("pmcid", ""),
                        "figtitle": item.get("figtitle", ""),
                        "figid": item.get("figid", ""),
                        "image_url": item.get("image_url", ""),
                        "pmid": item.get("pmid", ""),
                        "gene_symbols": item.get("gene_symbols", []),
                        # Additional fields from literature table (empty for network biology)
                        "drugs": "",
                        "keywords": "",
                        "process": "",
                        "insights": "",
                        "data_source": "network_biology"
                    }
                    combined_results.append(normalized_item)
            
            combined_data[disease] = {"results": combined_results}
        
        print(f"Combined data for {len(combined_data)} diseases")
        return combined_data
        
    except Exception as e:
        print(f"Error combining data: {str(e)}")
        return {}


def process_target_literature_request(target: str, diseases: List[str] = None) -> tuple:
    """
    Process target literature request and return processed target and diseases.
    
    Args:
        target: Target string
        diseases: List of diseases (optional)
    
    Returns:
        tuple: (processed_target, processed_diseases)
    """
    processed_target = target.strip() if target else "no-target"
    
    # If no diseases provided or empty list, default to "no-disease"
    if not diseases or len(diseases) == 0:
        processed_diseases = ["no-disease"]
    else:
        # Process diseases: strip whitespace and convert spaces to underscores
        processed_diseases = [disease.strip().lower().replace(" ", "_") for disease in diseases if disease.strip()]
        # If after processing we have empty list, default to "no-disease"
        if not processed_diseases:
            processed_diseases = ["no-disease"]
    
    return processed_target, processed_diseases