"""
Literature cache updater module
Contains helper functions for updating literature caches with analysis data
"""

import os
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session


async def update_literature_caches_with_analysis(
    target: str, 
    diseases: List[str], 
    db: Session, 
    analysis_type: str,
    # Helper functions passed as parameters to avoid circular imports
    load_response_from_file,
    save_response_to_file,
    # Models passed as parameters
    Disease,
    TargetDisease
):
    """
    Update literature caches with table and supplementary analysis data
    analysis_type: "table" or "supplementary"
    """
    
    is_target_only = target != "no-target" and not diseases
    is_disease_only = target == "no-target" and diseases
    is_combination = target != "no-target" and diseases
    
    # Determine which literature endpoint to update
    if is_disease_only:
        literature_endpoint = "/evidence/literature/"
        literature_table_model = Disease
        literature_cache_dir = "cached_data_json/disease"
        items_to_update = diseases
    else:  # target_only or combination
        literature_endpoint = "/evidence/target-literature/"
        literature_table_model = TargetDisease
        literature_cache_dir = "cached_data_json/target_disease"
        if is_target_only:
            items_to_update = [f"{target}-no-disease"]
        else:  # combination
            items_to_update = [f"{target}-{disease}" for disease in diseases]
    
    # Get analysis endpoint
    if analysis_type == "table":
        analysis_endpoint = "/evidence/literature-table-analysis/"
        analysis_field = "tables_analysis"
    else:  # supplementary
        analysis_endpoint = "/evidence/literature-supplementary-materials-analysis/"
        analysis_field = "supplementary_analysis"
    
    for item in items_to_update:
        try:
            # For file operations, convert spaces to underscores
            clean_item = item.strip().lower().replace(" ", "_")
            
            # Load literature cache
            literature_record = db.query(literature_table_model).filter_by(id=clean_item).first()
            if not literature_record or not os.path.exists(literature_record.file_path):
                print(f"Literature cache not found for {clean_item}")
                continue
                
            literature_responses = load_response_from_file(literature_record.file_path)
            if literature_endpoint not in literature_responses:
                print(f"Literature endpoint {literature_endpoint} not found in cache for {clean_item}")
                continue
                
            # Get literature data and extract PMIDs
            literature_data = literature_responses[literature_endpoint]
            if "literature" not in literature_data:
                print(f"No literature data found for {clean_item}")
                continue
                
            literature_pmids = set()
            for lit_item in literature_data["literature"]:
                if "pmid" in lit_item:
                    literature_pmids.add(lit_item["pmid"])
                elif "PMID" in lit_item:  # Handle both cases
                    literature_pmids.add(lit_item["PMID"])
            
            if not literature_pmids:
                print(f"No PMIDs found in literature data for {clean_item}")
                continue
            
            print(f"Found {len(literature_pmids)} PMIDs in literature data for {clean_item}")
            
            # Load analysis cache
            if is_disease_only:
                # For disease-only, analysis is stored in disease cache
                analysis_record = literature_record
                analysis_responses = literature_responses
            else:
                # For target-only and combination, analysis is stored in target_disease cache
                analysis_record = db.query(TargetDisease).filter_by(id=clean_item).first()
                if not analysis_record or not os.path.exists(analysis_record.file_path):
                    print(f"Analysis cache not found for {clean_item}")
                    continue
                analysis_responses = load_response_from_file(analysis_record.file_path)
            
            if analysis_endpoint not in analysis_responses:
                print(f"Analysis endpoint {analysis_endpoint} not found in cache for {clean_item}")
                continue
                
            # Get analysis data
            analysis_data = analysis_responses[analysis_endpoint]
            if "results" not in analysis_data:
                print(f"No analysis results found for {clean_item}")
                continue
            
            print(f"Found {len(analysis_data['results'])} analysis results for {clean_item}")
            
            # Update literature data with analysis
            updated = False
            for lit_item in literature_data["literature"]:
                # Handle both pmid and PMID keys
                lit_pmid = lit_item.get("pmid") or lit_item.get("PMID")
                if not lit_pmid:
                    continue
                
                # Initialize analysis fields if they don't exist
                if "tables_analysis" not in lit_item:
                    lit_item["tables_analysis"] = []
                if "supplementary_analysis" not in lit_item:
                    lit_item["supplementary_analysis"] = ""
                if "pmc_url" not in lit_item:
                    lit_item["pmc_url"] = ""
                
                # Update with matching analysis
                for analysis_item in analysis_data["results"]:
                    analysis_pmid = analysis_item.get("pmid") or analysis_item.get("PMID")
                    if analysis_pmid and str(analysis_pmid) == str(lit_pmid):
                        if analysis_type == "table" and "analysis" in analysis_item:
                            if analysis_item["analysis"] not in lit_item["tables_analysis"]:
                                lit_item["tables_analysis"].append(analysis_item["analysis"])
                                updated = True
                                print(f"Added table analysis for PMID {lit_pmid}")
                            
                            # Update pmc_url only if it's empty (first endpoint wins)
                            if "url" in analysis_item and not lit_item["pmc_url"]:
                                lit_item["pmc_url"] = analysis_item["url"]
                                updated = True
                                print(f"Added PMC URL for PMID {lit_pmid}: {analysis_item['url']}")
                                
                        elif analysis_type == "supplementary" and "analysis" in analysis_item:
                            if not lit_item["supplementary_analysis"]:
                                lit_item["supplementary_analysis"] = analysis_item["analysis"]
                                updated = True
                                print(f"Added supplementary analysis for PMID {lit_pmid}")
                            
                            # Update pmc_url only if it's empty (first endpoint wins)
                            if "url" in analysis_item and not lit_item["pmc_url"]:
                                lit_item["pmc_url"] = analysis_item["url"]
                                updated = True
                                print(f"Added PMC URL for PMID {lit_pmid}: {analysis_item['url']}")
                            elif "url" in analysis_item and lit_item["pmc_url"]:
                                # URL already exists, skip updating
                                print(f"PMC URL already exists for PMID {lit_pmid}, skipping update")
            
            # Save updated literature cache if changes were made
            if updated:
                literature_responses[literature_endpoint] = literature_data
                save_response_to_file(literature_record.file_path, literature_responses)
                print(f"Updated literature cache with {analysis_type} analysis for {clean_item}")
            else:
                print(f"No matching PMIDs found for {analysis_type} analysis update for {clean_item}")
                
        except Exception as e:
            logging.error(f"Error updating literature cache for {item}: {e}")
            continue