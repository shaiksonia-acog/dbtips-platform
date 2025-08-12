import os
import sys
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
from abc import ABC, abstractmethod
import logging

sys.path.append('/app/res-immunology-automation/res_immunology_automation/src/scripts/')
print("path: ", sys.path)

from literature_enhancement.db_utils.async_utils import afetch_rows, aupdate_table_rows
from llm_analyzer import LLMAnalyzerFactory
from db.models import LiteratureTablesAnalysis, LiteratureSupplementaryMaterialsAnalysis


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

analyzer = LLMAnalyzerFactory.create_analyzer_client()

class AbstractAnalyzerWorkflow(ABC):
    def __init__(self, disease: str, target: Optional[str] = None):
        self.disease = disease
        self.target = target
        self.analyzer = LLMAnalyzerFactory.create_analyzer_client()

    async def run(self):
        self.current_section_type, self.current_db_model  = self.section_type_label()
        
        logger.info(f"Fetching {self.current_section_type} records from the DB")
        records = await self.fetch_records()
        
        if records:
            
            if self.current_section_type == 'Tables':
                self.description_field = 'table_description'
                self.content_field = 'table_schema'

            if self.current_section_type == 'Supplementary Materials':
                self.description_field = 'description'
                self.content_field = 'file_names'

            logger.info(f"Analyzing {self.current_section_type}")
            await self.analyze(records)
            return

        else:
            logger.info("=== SKIPPING ===")
            logger.info(f"No records to Analyse for given Disease: {self.disease} and Target: {self.target}")
            return

    async def fetch_records(self) -> List[Dict]:
        return await afetch_rows(self.current_db_model, self.disease, self.target)

    async def analyze(self, records: List[Dict]):
        for record in records:
            section_description = record.get("section_description")
            section_content = record.get("section_content")
            pmcid = record.get("PMCID")
            try:
                logger.info(f"Processing {self.current_section_type}: {record.get(self.description_field)} from PMCID: {record.get('pmcid')}")
                analysis = self.analyzer.get_llm_response(
                    section_content, section_description, self.current_section_type
                )
                await self.update_analysis(analysis, record)
            except Exception as e:
                logger.error(
                    f"Error {self.current_section_type}: {record.get(self.description_field)} from PMCID: {record.get('pmcid')}. "
                    f"Skipping. Error: {e}"
                )
                continue

    async def update_analysis(self, analysis_data: Dict, metadata: Dict, pmcid: str):
        try:
            await aupdate_table_rows(self.current_db_model, analysis_data, metadata)
            logger.info(f"Updated the analysis: {analysis_data} for: {metadata} for PMCID: {pmcid} in DB.")
        except Exception as e:
            logger.error(f"Error updating the analysis: {analysis_data} for: {metadata} for PMCID: {pmcid} in the DB")
            raise e

    @abstractmethod
    def section_type_label(self) -> Tuple[str, BaseModel]:
        pass

class TablesAnalyzerWorkflow(AbstractAnalyzerWorkflow):      
    def section_type_label(self) -> str:
        return "Tables", LiteratureTablesAnalysis

class SupplementaryAnalyzerWorkflow(AbstractAnalyzerWorkflow):
    def section_type_label(self) -> str:
        return "Supplementary Materials", LiteratureSupplementaryMaterialsAnalysis

# -------------------------
# Fetch unprocessed images
# -------------------------
# async def fetch_tables(disease: str, target: Optional[str]):
#     return await afetch_rows(DiseaseTablesAnalysis, disease, target)

# # -------------------------
# # Analyze each image
# # -------------------------
# async def analyse_tables(tables_data: List[Dict]):
#     for table_data in tables:
#         try:
#             logger.info(f"Processing image: {table_data.get('description')} from PMCID: {table_data.get('PMCID')}")
#             table_analysis = analyzer.get_llm_response(table_data.get('table_schema'), table_data.get('table_description'))
#             await update_table_analysis(table_analysis, table_data)
#         except Exception as e:
#             logger.error(f"Error processing image: {table_data.get('image_caption')} from PMCID: {table_data.get('PMCID')}. Skipping. Error: {e}")
#             continue

# # -------------------------
# # Update analysis to DB
# # -------------------------
# async def update_tables_analysis(table_analysis_data: Dict, table_metadata: Dict):
#     try:
#         await aupdate_table_rows(DiseaseTablesAnalysis, table_analysis_data, table_metadata)
#         logger.info("Updated analysis in DB.")
#     except Exception as e:
#         logger.error("Error updating the Image Analysis data to the DB")
#         raise e

# -------------------------
# Main entrypoint
# -------------------------
async def main(disease: str, target: str = 'no-target'):
    tables_workflow = TablesAnalyzerWorkflow(disease, target)
    await tables_workflow.run()
    suppl_materials_workflow = SupplementaryAnalyzerWorkflow(disease, target)
    await suppl_materials_workflow.run()

if __name__ == "__main__":
    asyncio.run(main("migraine disorder"))
