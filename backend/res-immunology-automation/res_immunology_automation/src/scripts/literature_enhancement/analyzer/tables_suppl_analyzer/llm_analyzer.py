from openai import OpenAI
import json
import os
from abc import ABC, abstractmethod
from typing import Dict, List
from enum import Enum
from pydantic import BaseModel, Field, constr

class LLMResponse:
    analysis: str
    keywords: List[str] = Field(default_factory=list)

class SectionTypeEnum(str, Enum):
    tables = "Tables"
    suppl_mater = "Supplementary Materials"

LLM = os.getenv('LLM_MODEL','gpt-4o-mini')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', None)

table_schema_prompt = f"""
        You are an expert in HTML table analysis and schema extraction. Given an HTML snippet containing one or more tables, your task is to accurately extract the schema of each table. Tables may include:
            - Nested or hierarchical column headers (using colspan)
            - Grouped or sectioned rows (using rowspan)
            - Flat or deeply nested tables
            - Multiline headers or complex formatting

        Your output should be a structured JSON schema representing only the structure of each table — not the data.

        Extraction Requirements:
        1.Columns:
            - Extract all top-level column headers
            - Capture header nesting hierarchy using "children" fields when headers span multiple sub-columns.
            - Flatten merged cells in headers into a logical tree structure.

        2.Rows (Row Hierarchy):
            - Identify grouping of rows based on repeating or merged values in row header columns.
            - For each grouping key (usually the first few columns), include:
                - All unique values in that column
                - How many rows each value spans (row_count)
                - Whether that value uses an explicit rowspan in HTML (uses_rowspan: true or false)

        3.Merged Cell Handling:
            - Accurately resolve rowspan and colspan to reflect the actual visual/logical structure.
            - Do not include visual formatting (alignment, bold, etc.).

        4.Multiple Tables:
            - If multiple tables are present, extract each as a separate schema object with its:
                - Title (if available)
                - Caption or description (if present near the table)

        5.No Data Extraction:
            - Do not extract or return any actual data values from the table body.
            - Focus only on structure and logical organization.

        Here's the HTML Snippet: {input}


        Output Format:
            json```
            {{
            "title": "<Table Title or Number>",
            "description": "<Optional caption or description>",
            "columns": [
                {{ "name": "Column A" }},
                {{
                "name": "Grouped Column B",
                "children": [
                    {{ "name": "Subcolumn B1" }},
                    {{ "name": "Subcolumn B2" }}
                ]
                }},
                ...
            ],
            "row_hierarchy": {{
                "<Row Grouping Column>": {{
                "<Value1>": {{ "row_count": N , "uses_rowspan": true|false }},
                "<Value2>": {{ "row_count": M , "uses_rowspan": true|false}}
                }}
            }}
            }}
            ```
        """

class Analyzer(ABC):
    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("API Key not found in environment variables")            

    @abstractmethod
    def create_client(self):
        pass

    @abstractmethod
    def get_llm_response(self, table_schema: Dict, table_description: str):
        pass


class AnalyzerOpenAI(Analyzer):
    def create_client(self):
        self.client = client = OpenAI(api_key=OPENAI_API_KEY)

    def get_llm_response(self, schema: str, description: str, section_type: SectionTypeEnum)-> LLMResponse:
        prompts = {"table": table_prompt + f"\n Here's the schema: {schema} and the description of the table: {description}",
                    "supplementary materials": suppl_prompt + f"\n Here's the available supplmentary materials references: {schema} and the description of the section : {description}"}
        
        prompt = prompts[section_type.lower()] 

        response = client.chat.completions.create(
        model=LLM,
        messages=[
            {"role": "system", "content": "You are an expert in analyzing and classifying scientific research."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=4096,
        temperature=0.2
        )

        response_content = response.choices[0].message.content
        
        if "json" in response_content:
            print("recieved markdown response")
            response_content = response_content.strip("```").replace("json", "", 1).strip()
        
        insights = json.loads(response_content)
        return insights

class LLMAnalyzerFactory:
    def create_analyzer_client()->Analyzer:
        if 'gpt' in LLM:
            return AnalyzerOpenAI()