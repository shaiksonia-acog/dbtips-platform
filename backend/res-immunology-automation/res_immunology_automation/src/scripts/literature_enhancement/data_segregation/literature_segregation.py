"""
Literature Data Segregation Integration Module

This module integrates the three segregation modules (supplementary materials, figures, and tables)
into the build dossier process. Each module is called independently to maintain modularity.
"""

import logging
import os
import asyncio
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

# Import the three segregation modules
from supplementary_data_segregators import SupplementaryMaterialsSegregator
from figure_data_segregators import FigureDataSegregator
from table_data_segregators import TableDataSegregator

log = logging.getLogger(__name__)
openai_api_key = os.getenv("OPENAI_API_KEY")

class LiteratureDataSegregationRunner:
    """Runs all three literature data segregation modules for specific diseases/targets"""
    
    def __init__(self, db_session: Session):
        self.db = db_session 
        # Initialize all three segregators
        self.supp_segregator = SupplementaryMaterialsSegregator(db_session)
        self.figure_segregator = FigureDataSegregator(db_session)        
        self.table_segregator = TableDataSegregator(db_session, openai_api_key)
        
    async def run_segregation_for_disease(self, disease: str, batch_size: int = 50) -> Dict[str, Any]:
        """
        Run all three segregation modules for articles related to a specific disease
        
        Args:
            disease: Disease name to filter articles
            batch_size: Number of articles to process in each batch
            
        Returns:
            Dictionary with results from each segregation module
        """
        log.info(f"Starting literature data segregation for disease: {disease}")
        
        results = {
            'disease': disease,
            'supplementary_materials': 0,
            'figures': 0,
            'tables': 0,
            'errors': []
        }
        
        try:
            #Check if extraction is completed for the disease
            extraction_status = check_pipeline_status("extraction", disease)            # Print logs
            segregation_status = check_pipeline_status("segregation", disease)
            all_completed = extraction_status and segregation_status

            if all_completed:
                log.info("Data Segregation is already completed for the disease. SKIPPING...")
                return 
            
            elif not extraction_status :
                log.info(f"Extraction is not completed for target: {target}, disease: {disease}")
                raise ValueError(f"Extraction is not completed for target: {target}, disease: {disease}")

            elif not segregation_status:

                # Run supplementary materials segregation
                log.info(f"Running supplementary materials segregation for disease: {disease}")
                supp_count = await self._run_supplementary_materials_segregation(disease, batch_size)
                results['supplementary_materials'] = supp_count
                
                # Small delay between modules
                await asyncio.sleep(2)
                
                # Run figure data segregation
                log.info(f"Running figure data segregation for disease: {disease}")
                fig_count = await self._run_figure_segregation(disease, batch_size)
                results['figures'] = fig_count
                
                # Small delay between modules
                await asyncio.sleep(2)
                
                # Run table data segregation (if OpenAI API key available)
                if self.table_segregator:
                    log.info(f"Running table data segregation for disease: {disease}")
                    table_count = await self._run_table_segregation(disease, batch_size)
                    results['tables'] = table_count
                else:
                    log.warning("Skipping table segregation - OpenAI API key not available")
                    results['errors'].append("Table segregation skipped - OpenAI API key not available")
                
            except Exception as e:
                log.error(f"Error in literature data segregation for disease {disease}: {e}")
                results['errors'].append(f"General error: {str(e)}")
            
            log.info(f"Literature data segregation completed for disease {disease}. Results: {results}")
            return results
    
    async def run_segregation_for_target_disease(self, target: str, disease: Optional[str] = None, 
                                                batch_size: int = 50) -> Dict[str, Any]:
        """
        Run all three segregation modules for articles related to a specific target-disease combination
        
        Args:
            target: Target name to filter articles
            disease: Disease name to filter articles (optional)
            batch_size: Number of articles to process in each batch
            
        Returns:
            Dictionary with results from each segregation module
        """
        # Handle None disease for target-only processing (same as literature extractor)
        if disease is None:
            disease = "no-disease"
        
        log.info(f"Starting literature data segregation for target-disease: {target}-{disease}")
        
        results = {
            'target': target,
            'disease': disease,
            'supplementary_materials': 0,
            'figures': 0,
            'tables': 0,
            'errors': []
        }
        
        try:
            extraction_status = check_pipeline_status("extraction", disease)            # Print logs
            segregation_status = check_pipeline_status("segregation", disease)
            all_completed = extraction_status and segregation_status

            if all_completed:
                log.info("Data Segregation is already completed for the disease. SKIPPING...")
                return 
            
            elif not extraction_status :
                log.info(f"Extraction is not completed for target: {target}, disease: {disease}")
                raise ValueError(f"Extraction is not completed for target: {target}, disease: {disease}")

            elif not segregation_status:

            # Run supplementary materials segregation
                log.info(f"Running supplementary materials segregation for target-disease: {target}-{disease}")
                supp_count = await self._run_supplementary_materials_segregation_target(target, disease, batch_size)
                results['supplementary_materials'] = supp_count
                
                # Small delay between modules
                await asyncio.sleep(2)
                
                # Run figure data segregation
                log.info(f"Running figure data segregation for target-disease: {target}-{disease}")
                fig_count = await self._run_figure_segregation_target(target, disease, batch_size)
                results['figures'] = fig_count
                
                # Small delay between modules
                await asyncio.sleep(2)
                
                # Run table data segregation (if OpenAI API key available)
                if self.table_segregator:
                    log.info(f"Running table data segregation for target-disease: {target}-{disease}")
                    table_count = await self._run_table_segregation_target(target, disease, batch_size)
                    results['tables'] = table_count
                else:
                    log.warning("Skipping table segregation - OpenAI API key not available")
                    results['errors'].append("Table segregation skipped - OpenAI API key not available")
                
            except Exception as e:
                log.error(f"Error in literature data segregation for target-disease {target}-{disease}: {e}")
                results['errors'].append(f"General error: {str(e)}")
            
            log.info(f"Literature data segregation completed for target-disease {target}-{disease}. Results: {results}")
            return results
    
    async def _run_supplementary_materials_segregation(self, disease: str, batch_size: int) -> int:
        """Run supplementary materials segregation for disease-specific articles"""
        try:
            # Process articles filtered by disease
            total_extracted = await asyncio.get_event_loop().run_in_executor(
                None, 
                self.supp_segregator.process_disease_articles, 
                disease, 
                batch_size
            )
            log.info(f"Supplementary materials segregation completed: {total_extracted} records extracted for disease {disease}")
            return total_extracted
        
        except Exception as e:
            log.error(f"Error in supplementary materials segregation for disease {disease}: {e}")
            raise
    
    async def _run_figure_segregation(self, disease: str, batch_size: int) -> int:
        """Run figure segregation for disease-specific articles"""
        try:
            # Process articles filtered by disease
            total_extracted = await asyncio.get_event_loop().run_in_executor(
                None, 
                self.figure_segregator.process_disease_articles, 
                disease, 
                batch_size
            )
            log.info(f"Figure segregation completed: {total_extracted} figures extracted for disease {disease}")
            return total_extracted
        except Exception as e:
            log.error(f"Error in figure segregation for disease {disease}: {e}")
            raise
    
    async def _run_table_segregation(self, disease: str, batch_size: int) -> int:
        """Run table segregation for disease-specific articles"""
        try:
            # Process articles filtered by disease
            total_extracted = await asyncio.get_event_loop().run_in_executor(
                None, 
                self.table_segregator.process_disease_articles, 
                disease, 
                batch_size
            )
            log.info(f"Table segregation completed: {total_extracted} tables extracted for disease {disease}")
            return total_extracted
        except Exception as e:
            log.error(f"Error in table segregation for disease {disease}: {e}")
            raise
    
    async def _run_supplementary_materials_segregation_target(self, target: str, disease: str, batch_size: int) -> int:
        """Run supplementary materials segregation for target-disease specific articles"""
        try:
            total_extracted = await asyncio.get_event_loop().run_in_executor(
                None, 
                self.supp_segregator.process_target_disease_articles, 
                target, 
                disease, 
                batch_size
            )
            log.info(f"Supplementary materials segregation completed: {total_extracted} records extracted for target-disease {target}-{disease}")
            return total_extracted
        except Exception as e:
            log.error(f"Error in supplementary materials segregation for target-disease {target}-{disease}: {e}")
            raise
    
    async def _run_figure_segregation_target(self, target: str, disease: str, batch_size: int) -> int:
        """Run figure segregation for target-disease specific articles"""
        try:
            total_extracted = await asyncio.get_event_loop().run_in_executor(
                None, 
                self.figure_segregator.process_target_disease_articles, 
                target, 
                disease, 
                batch_size
            )
            log.info(f"Figure segregation completed: {total_extracted} figures extracted for target-disease {target}-{disease}")
            return total_extracted
        except Exception as e:
            log.error(f"Error in figure segregation for target-disease {target}-{disease}: {e}")
            raise
    
    async def _run_table_segregation_target(self, target: str, disease: str, batch_size: int) -> int:
        """Run table segregation for target-disease specific articles"""
        try:
            total_extracted = await asyncio.get_event_loop().run_in_executor(
                None, 
                self.table_segregator.process_target_disease_articles, 
                target, 
                disease, 
                batch_size
            )
            log.info(f"Table segregation completed: {total_extracted} tables extracted for target-disease {target}-{disease}")
            return total_extracted
        except Exception as e:
            log.error(f"Error in table segregation for target-disease {target}-{disease}: {e}")
            raise


# Convenience functions for easy integration
async def run_literature_segregation_for_disease(db_session: Session, disease: str, 
                                               openai_api_key: str = None, batch_size: int = 50) -> Dict[str, Any]:
    """
    Convenience function to run all literature segregation for a disease
    
    Args:
        db_session: Database session
        disease: Disease name
        openai_api_key: OpenAI API key for table segregation
        batch_size: Batch size for processing
        
    Returns:
        Dictionary with segregation results
    """
    runner = LiteratureDataSegregationRunner(db_session)
    return await runner.run_segregation_for_disease(disease, batch_size)


async def run_literature_segregation_for_target_disease(db_session: Session, target: str, disease: Optional[str] = None,
                                                       openai_api_key: str = None, batch_size: int = 50) -> Dict[str, Any]:
    """
    Convenience function to run all literature segregation for a target-disease combination
    
    Args:
        db_session: Database session
        target: Target name
        disease: Disease name (optional)
        openai_api_key: OpenAI API key for table segregation
        batch_size: Batch size for processing
        
    Returns:
        Dictionary with segregation results
    """
    runner = LiteratureDataSegregationRunner(db_session)
    return await runner.run_segregation_for_target_disease(target, disease, batch_size)