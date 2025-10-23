import json
from typing import List, Dict
from Bio import Entrez
from typing import List
import GEOparse
from typing import Dict, List, Any,Tuple
import requests
from typing import Optional
import pprint
import os
import requests
from typing import List, Dict,Any
import json
from datetime import datetime
import requests
import csv
from typing import Optional
from Bio import Entrez
import requests
from xml.etree import ElementTree
import xml.etree.ElementTree as ET
import time
from xml.etree.ElementTree import Element
import pandas as pd
import io
from fastapi import HTTPException
from Bio.Entrez import HTTPError
from .pubmed_utils import get_data_from_pubmed
import logging
import socket
from urllib.error import URLError
from .disease_area_mapping_utils import get_mesh_tree_numbers_of_disease, pmid_to_meshid_mapper
from .ollama_llm_client import LLMClient

MAX_RESULTS=500
# NCBI API Base URL
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

logging.basicConfig(level=logging.INFO)
NCBI_API_KEY = os.getenv('NCBI_API_KEY')
RATE_LIMIT_RETRY_PERIOD = 300
EMAIL = os.getenv('NCBI_EMAIL')
JOURNAL_DATA_PATH = "/app/res-immunology-automation/res_immunology_automation/src/disease_data/scimagojr-journal-2023-cleaned.csv"
OPEN_CITATIONS_API = os.getenv('OPEN_CITATIONS_API')

def get_mesh_term_for_disease(disease_name):
    """
    Fetch the MeSH term for a given disease name from the NCBI MeSH database.
    
    Args:
        disease_name (str): The disease name to search for.
        
    Returns:
        str: The MeSH term for the disease, or None if not found.
    """
    params = {
        "db": "mesh",           
        "term": disease_name,   
        "retmode": "xml",
        "api_key": NCBI_API_KEY      
    }

    try:
        url = BASE_URL + "esearch.fcgi"
        response = get_data_from_pubmed(url, params)

        root = ET.fromstring(response.content)
        
        for term_set in root.findall(".//TermSet"):
            field = term_set.find("Field")
            term = term_set.find("Term")
            if field is not None and term is not None and field.text == "MeSH Terms":
                return term.text.replace('"', '').replace("[MeSH Terms]", "").strip()

        return None
    
    except HTTPException as e:
        raise e

    except requests.RequestException as e:
        print(f"An error occurred while fetching the MeSH term: {e}")
        return None
    
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return None



def build_query(target: str, disease: str, target_terms_file: str, disease_synonyms_file: str) -> str:
    """
    Build a query string using a target and disease name, 
    Include the synonyms of the disease from a JSON file.
    Include the target terms from a JSON file.

    Args:
        target (str): The target (e.g., OX40).
        disease (str): The disease name (e.g., systemic scleroderma).
        target_terms_file (str): Path to the JSON file containing target terms.

        disease_synonyms_file (str): Path to JSON file containing alternate diseese terms to search for
        E.g. For AD, the term we get from the front-end is Dermatitis, atopic. This term doesn't return any patents.
        Therefore, we look up the disease synonyms JSON file and instead use Atopic Dermatitis as search term which works.

    Returns:
        str: The constructed query string with target, disease, and synonyms in double quotes.
    """
    
    # Load disease synonyms from the JSON file, load target terms    
    with open(disease_synonyms_file, 'r') as f, open(target_terms_file, 'r') as j:
        disease_data: Dict = json.load(f).get("diseases", {})
        target_data: Dict[str, List[str]] = json.load(j)

    # Get the synonyms of the disease
    synonyms: List[str] = disease_data.get(disease.lower(), {}).get("patent_synonyms", [])

    # Create the query for the disease and its synonyms
    disease_query = ""
    if synonyms:
        synonym_query = " OR ".join([f'TI="{syn.strip()}" OR AB="{syn.strip()}"' for syn in synonyms])
        disease_query += f' ({synonym_query})'
    else:
    	# if no synonyms are found, use the disease name directly
        disease_query = f'(TI="{disease}" OR AB="{disease}")'    

    terms: List[str] = target_data.get(target.lower(), [])
    # filter synonyms which has multiple words
    terms = [term for term in terms if ' ' not in term]
    # print(terms)

    if terms:
        # Include the original target along with the terms
        terms_with_target = [target] + terms
        target_query = " OR ".join([f'TI="{term.strip()}" OR AB="{term.strip()}"' for term in terms_with_target])
        target_query = f'({target_query})'  # Wrap in parentheses only if there are multiple terms
    else:
        # If no terms are found, use the target directly
        target_query = f'(TI="{target}" OR AB="{target}")'


    # Build the final query
    query: str = f'{target_query} AND {disease_query}'
    # print(query)

    return query

def build_query_target(target: str, target_terms_file: str) -> str:
    """
    Build a query string using only the target name.
    Include the synonyms of the target from a JSON file.

    Args:
        target (str): The target (e.g., IAPP).
        target_terms_file (str): Path to the JSON file containing target terms.

    Returns:
        str: The constructed query string with the target and its synonyms.
    """
    # Load target terms from the JSON file
    with open(target_terms_file, 'r') as f:
        target_data: Dict[str, List[str]] = json.load(f)

    # Get the synonyms of the target
    terms: List[str] = target_data.get(target.lower(), [])

    # filter synonyms which has multiple words
    terms = [term for term in terms if ' ' not in term]

    if terms:
        # Include the original target along with the terms
        terms_with_target = [target] + terms
        target_query = " OR ".join([f'TI="{term.strip()}" OR AB="{term.strip()}"' for term in terms_with_target])
        target_query = f'({target_query})'  # Wrap in parentheses only if there are multiple terms
    else:
        # If no terms are found, use the target directly
        target_query = f'TI="{target.strip()}" OR AB="{target}"'

    # Define the additional terms for the second part of the query
    additional_terms: List[str] = [
        "Antigen binding", "Antibody", "Antibodies", "Compound", "Formula", "Compounds", "Analogue"
    ]

    # Build the second part of the query
    additional_query = " OR ".join([f'AB="{term.strip()}"' for term in additional_terms])
    additional_query = f'({additional_query})'  # Wrap in parentheses

    # Build the final query
    query: str = f'{target_query} AND {additional_query}'
    print(query)

    return query

def pubmed_to_pmc(pmid: str, tool: str = "my_tool", email: str = EMAIL) -> Optional[str]:
    """
    Converts a PubMed ID (PMID) to a PubMed Central ID (PMC ID) using the NCBI ID conversion API.

    Args:
        pmid (str): The PubMed ID to convert.
        tool (str, optional): The name of the tool making the request. Defaults to "my_tool".
        email (str, optional): User's email address for NCBI API usage.

    Returns:
        Optional[str]: The corresponding PMC ID if available, otherwise None.
    """
    base_url = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
    params = {
        "tool": tool,
        "email": email,
        "ids": pmid,
        "format": "json",
        "api_key": NCBI_API_KEY
    }

    try:
        url = base_url
        response = get_data_from_pubmed(url, params)
        data = response.json()  # Parse JSON response

        # Check for successful response
        if data["status"] == "ok":
            records = data.get("records", [])
            if records:
                pmc_id = records[0].get("pmcid", None)  # Get the first record's PMC ID
                return pmc_id  # Return the PMC ID if found
            else:
                print(f"No PMC ID found for PMID: {pmid}")
                return None  # No records found
        else:
            print(f"Error in response: {data.get('error', 'Unknown error')}")
            return None  # Error in response
    
    except HTTPException as e:
        raise e
    
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None  # Return None in case of request failure


def fetch_gse_summary(gse_id):
    """
    Fetch the summary of a GSE dataset using its GSE ID.
    
    Args:
        gse_id (str): The GSE ID of the dataset.
    
    Returns:
        str: The summary of the GSE dataset.
    """
    if not gse_id:
        return ""
        
    Entrez.email = EMAIL  # Replace with your email for NCBI access
    Entrez.api_key = NCBI_API_KEY
    try:
        # Fetch the GSE dataset
        handle = Entrez.esearch(db="gds", term=gse_id)
        record = Entrez.read(handle)
        handle.close()
        
        # Extract the dataset ID
        if record["IdList"]:
            dataset_id = record["IdList"][0]
            
            # Fetch the summary for the dataset
            summary_handle = Entrez.esummary(db="gds", id=dataset_id)
            summary = Entrez.read(summary_handle)
            summary_handle.close()
            
            return summary[0]["summary"]  # Return the summary field
        else:
            print("GSE ID not found in the GDS database.")
            return ""
        
    except HTTPError as e:
        if e.code == 429:
            raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Try again after {RATE_LIMIT_RETRY_PERIOD} seconds.")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return ""

def search_geo(disease_name: str) -> List[Tuple[str, str]]:
    """
    Search GEO datasets using NCBI's Entrez API and extract GSE IDs along with their corresponding types.

    Parameters:
    - disease_name: A string containing the name of the disease.

    Returns:
    - A list of tuples, each containing the GSE ID and its Type.
    """
    Entrez.email = EMAIL  # Provide your email here
    Entrez.api_key = NCBI_API_KEY

    try:
        disease_synonyms_file = "/app/res-immunology-automation/res_immunology_automation/src/disease_data/diseases_synonyms.json"
        with open(disease_synonyms_file, 'r') as f:
            disease_data: Dict = json.load(f).get("diseases", {})

        # Get the synonyms of the disease
        synonyms: List[str] = disease_data.get(disease_name.lower(), {}).get("synonyms", [])

        disease_mesh_term = get_mesh_term_for_disease(disease_name)
        synonyms.append(disease_mesh_term)

        print("MeshTerm in searchGeo",disease_mesh_term)
        disease_syn_query = " OR ".join([f'"{syn}" [Title] OR "{syn}" [Description]' for syn in synonyms])
        disease_only_query = f'"{disease_mesh_term}" [MeSH Terms] '
        query = (
            f'({disease_syn_query}) AND '
            f'"gse" [Filter] NOT "Hive" [All Fields] NOT "Hives" [All Fields] AND '
            f'"Expression profiling by high throughput sequencing" [Filter]'
        )
        print("Geo Query: ", query)
        handle = Entrez.esearch(db="gds", term=query, retmax=MAX_RESULTS)
        record = Entrez.read(handle)
        handle.close()

        # Check if results were returned
        if 'IdList' in record and record['IdList']:
            # Fetch results in text format
            fetch_handle = Entrez.efetch(db="gds", id=record['IdList'])
            data = fetch_handle.read()
            fetch_handle.close()

            # Extract GSE IDs and Types from the response
            gse_type_list: List[Tuple[str, str]] = []
            lines = data.splitlines()
            gse_id, dataset_type = None, None
            gse_id_set=set()

            for line in lines:
                if "Accession: GSE" in line:  # Extract GSE ID
                    gse_id = line.split()[2]
                elif "Type:" in line:  # Extract Type
                    dataset_type = line.split("Type:")[-1].strip()
                
                # If both GSE ID and Type are extracted, save them
                if gse_id and dataset_type and gse_id not in gse_id_set:
                    gse_type_list.append((gse_id, dataset_type,fetch_gse_summary(gse_id)))
                    gse_id, dataset_type = None, None  # Reset for next entry
                gse_id_set.add(gse_id)
                time.sleep(0.2)

            # Return the list of GSE IDs and their types
            return gse_type_list
        
    except HTTPError as e:
        if e.code == 429:
            raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Try again after {RATE_LIMIT_RETRY_PERIOD} seconds.")

    except HTTPException as e:
        raise e
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return []



def get_common_name(taxonomy_id: str) -> Optional[str]:
    """
    Fetches the commonName from the UniProt taxonomy API.

    Args:
    - taxonomy_id (int): The taxonomy ID to fetch data for.

    Returns:
    - str or None: The commonName of the organism, or None if the taxonomy ID is invalid or not found.
    """
    url = f"https://rest.uniprot.org/taxonomy/{taxonomy_id}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        return data.get("commonName", None)  # Return None if 'commonName' doesn't exist
    else:
        return None  # Return None if taxonomy ID is invalid or not found


def get_geo_metadata(gse_id: str,experiment_type: str,gse_summary: str) -> Dict[str, Any]:
    """
    Fetches GEO metadata for the given GEO Series ID.

    Args:
        gse_id (str): The GEO Series ID to retrieve metadata for.
        experiment_type (str): Experiment type.

    Returns:
        Dict[str, Any]: A dictionary containing the GSE metadata and GSM details.
    """
    socket.setdefaulttimeout(120) 
    try:
        # Load GEO dataset by GEO Series ID
        gse = GEOparse.get_GEO(geo=gse_id)

        # Access metadata and sample details
        gse_metadata: Dict[str, List[str]] = gse.metadata
        platform_names: Dict[str, str] = {}

        # Retrieve platform names
        for gpl_name, gpl in gse.gpls.items():
            platform_title = gpl.metadata.get("title", [""])[0]  # Use an empty string as the default value
            platform_names[gpl_name] = platform_title if platform_title else None  # Set to None if empty

        pubmed_ids: list[str] = gse_metadata.get("pubmed_id", [])

        pubmed_urls: list[str] = [
            f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/" for pubmed_id in pubmed_ids if pubmed_id
        ]

        result: Dict[str, Any] = {
            "GseID": gse_id,
            "Summary":gse_summary,
            "Title": gse_metadata.get("title", []),
            "OrganismID": gse_metadata.get("sample_taxid", []),
            "Platform": platform_names,
            "Design": gse_metadata.get("overall_design", []),
            "PubMedIDs": pubmed_ids,
            "PubMedURLs": pubmed_urls,
            "ExperimentType":experiment_type,
            "Samples": []
        }
        if result["OrganismID"]:
            result["Organism"] = [get_common_name(organism_id) for organism_id in result["OrganismID"]]
        else:
            result["Organism"] = None

        # Collect GSM details
        for gsm_name, gsm in gse.gsms.items():
            # Extracting the first tissue type
            tissue_types: List[str] = gsm.metadata.get("source_name_ch1", [])
            first_tissue_type: str = tissue_types[0].split(",")[0].strip() if tissue_types else ""  # Default to an
            # empty string if empty

            sample_info: Dict[str, Any] = {
                "SampleID": gsm_name,
                "TissueType": first_tissue_type,
                "Characteristics": gsm.metadata.get("characteristics_ch1", [])
            }
            result["Samples"].append(sample_info)

        # Clean up the downloaded file
        os.remove(f"{gse_id}_family.soft.gz")

        return result

    except (URLError, socket.timeout, Exception) as e:
        logging.error(f"Failed to download {gse_id}_family.soft.gz due to {e}")
    except Exception as e:
        print(f"An unexpected error occurred for {gse_id}: {e}")
        return None  # Return None to indicate failure


def get_geo_data_for_diseases(diseases: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetches GSE metadata for a list of diseases.

    Args:
        diseases (List[str]): A list of diseases to search for.

    Returns:
        Dict[str, List[Dict[str, Any]]]: A dictionary mapping each disease to its corresponding GSE metadata.
    """
    try:
        results: Dict[str, List[Dict[str, Any]]] = {}

        for disease in diseases:
            exceptional_diseases = {"prurigo nodularis": "prurigo", "chronic idiopathic urticaria": "urticaria"}
            input_disease_name = None
            # if disease=="prurigo nodularis":
            #     disease="prurigo"
            # elif disease=="chronic idiopathic urticaria":
            #     disease="urticaria"
            if disease in exceptional_diseases:
                input_disease_name = disease
                disease = exceptional_diseases[disease]
            print(f"Searching GSE IDs for disease: {disease}")
            gse_type_list = search_geo(disease)

            if gse_type_list is None:
                print(f"No results found for disease: {disease}")
                gse_type_list = [] 

            # Fetch metadata for each GSE ID
            disease_results = []
            for gse_id,experiment_type,gse_summary in gse_type_list:
                print(f"Fetching metadata for GSE ID: {gse_id}")
                metadata = get_geo_metadata(gse_id,experiment_type,gse_summary)
                if metadata is not None:
                    if metadata["Organism"] is not None and any(s and "honeybee" in s.lower() for s in metadata["Organism"]):
                        continue
                    else:
                        disease_results.append(metadata)
            # if disease=="prurigo":
            #     disease="prurigo nodularis"
            # elif disease=="urticaria":
            #     disease="chronic idiopathic urticaria"
            if input_disease_name:
                disease = input_disease_name
            results[disease] = disease_results  # Store results for the current disease
    
    except HTTPException as e:
        raise e
    except Exception as e:
        return results
    
    return results

# Function to search PubMed
def search_pubmed(disease_name: str) -> List[str]:
    """
    Searches PubMed for literature on a disease and retrieves PMIDs from the last 5 years.

    Args:
        disease_name (str): Name of the disease to search for.

    Returns:
        List[str]: A list of PubMed IDs (PMIDs) from the search.
    """
    # Get the current year and calculate the starting year
    current_year = datetime.now().year
    start_year = current_year - 5

    # params = {
    #     "db": "pubmed",
    #     "term": f"{disease_name}[MAJR]",  # Added filter for review articles
    #     "retmode": "json",
    #     "retmax": MAX_RESULTS,  # Maximum number of records to retrieve
    #     "sort": "relevance",  # Sort by relevance
    #     "mindate": f"{start_year}/01/01",  # Start date for filtering
    #     "maxdate": f"{current_year}/12/31",  # End date for filtering
    #     "datetype": "pdat",  # Search by publication date
    #     "api_key": NCBI_API_KEY
    # }
    article_types = [
    "Case Reports",
    "Clinical Study",
    "Clinical Trial",
    "Dataset",
    "Journal Article",
    "Preprint",
    "Research Support, American Recovery and Reinvestment Act",
    "Research Support, N.I.H., Extramural",
    "Research Support, N.I.H., Intramural", 
    "Research Support, Non-U.S. Gov't",
    "Research Support, U.S. Gov't, Non-P.H.S.",
    "Research Support, U.S. Gov't, P.H.S.",
    "Research Support, U.S. Gov't",
    "Review",
    "Systematic Review",
    "Technical Report"
    ]

    # Build the article types filter part
    article_types_query = " OR ".join([f'"{atype}"[Publication Type]' for atype in article_types])

    # Final term combining disease name and article type filters
    term = f'({disease_name}[MeSH Terms]) AND ({article_types_query})'

    params = {
        "db": "pubmed",
        "term": term,
        "retmode": "json",
        "retmax": MAX_RESULTS,
        "sort": "relevance",
        "mindate": f"{start_year}/01/01",
        "maxdate": f"{current_year}/12/31",
        "datetype": "pdat",
        "api_key": NCBI_API_KEY
    }

    try:

        url = BASE_URL + "esearch.fcgi"
        response = get_data_from_pubmed(url, params)
        data = response.json()

    except HTTPException as e:
        raise e
    return data.get("esearchresult", {}).get("idlist", [])

def search_pubmed_target(target_name: str, disease_name: str,target_terms_file: str,mesh_major_term:str) -> List[str]:
    """
    Searches PubMed for literature on a specific target and disease, 
    retrieving PMIDs from the last 5 years.

    Args:
        target_name (str): Name of the target to search for (e.g., "IL-17F").
        disease_name (str): Name of the disease to search for (e.g., "hidradenitis suppurativa").
        target_terms_file (str): Path of file containing the other terms for target
        mesh_major_term (str): Mesh major term for the disease

    Returns:
        List[str]: A list of PubMed IDs (PMIDs) from the search.
    """
    base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    with open(target_terms_file, 'r') as f:
        target_data: Dict[str, List[str]] = json.load(f)

    terms: List[str] = target_data.get(target_name.lower(), [])
    
    print("terms for target",terms)

    article_types = [
    "Case Reports",
    "Clinical Study",
    "Clinical Trial",
    "Dataset",
    "Journal Article",
    "Preprint",
    "Research Support, American Recovery and Reinvestment Act",
    "Research Support, N.I.H., Extramural",
    "Research Support, N.I.H., Intramural", 
    "Research Support, Non-U.S. Gov't",
    "Research Support, U.S. Gov't, Non-P.H.S.",
    "Research Support, U.S. Gov't, P.H.S.",
    "Research Support, U.S. Gov't",
    "Review",
    "Systematic Review",
    "Technical Report"
    ]

    # Build the article types filter part
    article_types_query = " OR ".join([f'"{atype}"[Publication Type]' for atype in article_types])

    # Build the target query
    if terms:
        target_query = " OR ".join([f'"{term}"[Title/Abstract]' for term in terms])
        print("target query before adding target name",target_query)
        target_query = f'("{target_name}"[Title/Abstract] OR {target_query})'
    else:
        target_query = f'"{target_name}"[Title/Abstract]'

    if disease_name != 'no-disease':

        # Build the disease query
        disease_query = f'"{disease_name}"[Title/Abstract]'

        # Build the MeSH term query
        mesh_query = f'"{mesh_major_term}"[MeSH Major Topic]'

        # Combine everything into the final query
        query = f'(({target_query}) AND ({mesh_query}) AND ({article_types_query}))'

    else:
        query = f'{target_query} AND ({article_types_query})'

    print("Target Query for Target:", target_name, query)

    current_year = datetime.now().year
    start_year = current_year - 10
    # Set up query parameters
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": MAX_RESULTS,  # Maximum number of records to retrieve
        "mindate": f"{start_year}/01/01",  # Start date for filtering
        "maxdate": f"{current_year}/12/31",  # End date for filtering
        "sort": "relevance",  # Sort by relevance
        "datetype": "pdat",  # Search by publication date
        "api_key": NCBI_API_KEY
    }
    try:
        url = base_url + "esearch.fcgi"
        response = get_data_from_pubmed(url, params)
        data = response.json()

    except HTTPException as e:
        raise e
    # Extract and return the list of PMIDs
    return data.get("esearchresult", {}).get("idlist", [])

def extract_article_title(article: ET.Element) -> str:
    """
    Extracts and combines the text from an ArticleTitle element, preserving nested tags like <sub>.

    Args:
        article (ET.Element): The XML element containing the ArticleTitle tag.

    Returns:
        str: The combined title with proper spaces and preserved <sub> tags.
    """
    # Initialize an empty list to store each element's text
    text_elements = []

    # Iterate over all elements in the ArticleTitle tag
    for element in article.iter():
        if element.tag == "sub" or element.tag=="sup":
            # Append  tag with its content as is
            text_elements.append(f"<{element.tag}>{element.text}</{element.tag}>")
        elif element.text:
            # Append plain text content
            text_elements.append(element.text.strip())
        if element.tail:
            # Append tail text (text after a nested tag)
            text_elements.append(element.tail.strip())

    # Combine the elements in the list with spaces
    full_title = " ".join(text_elements).strip()
    return full_title


def extract_qualifiers_for_disease(mesh_heading_list: Element, disease_name: str) -> List[str]:
    """
    Extracts qualifiers for a specific disease from a MeSHHeadingList.

    Args:
    - mesh_heading_list (Element): The XML element containing MeSHHeadingList.
    - disease_name (str): The name of the disease to filter.

    Returns:
    - List[str]: A list of qualifiers for the given disease.
    """
    qualifiers = []
    # print("finding qualifier")
        # Ensure mesh_heading_list is not None
    if mesh_heading_list is None or not mesh_heading_list:
        return qualifiers  # Return an empty list if mesh_heading_list is None


    # Iterate through all MeshHeading elements
    for mesh_heading in mesh_heading_list.findall(".//MeshHeading"):
        # Get the DescriptorName
        descriptor_name = mesh_heading.find("DescriptorName")
        if descriptor_name is not None and descriptor_name.text and descriptor_name.attrib.get("MajorTopicYN") == "Y":
            # Check if the descriptor name matches the disease name
            if descriptor_name.text.strip().lower() == disease_name.strip().lower():
                # Extract all QualifierName elements
                qualifier_names = mesh_heading.findall("QualifierName")
                qualifiers.extend([qualifier.text for qualifier in qualifier_names if qualifier.text])

    # print(f"found qualifers: {qualifiers}")
    return qualifiers


def get_cited_by_count(pmid: str) -> int:
    """
    Gets the cite count of a pubmed Article from OpenCitations API
    """
    API_CALL = f"https://opencitations.net/index/api/v2/citation-count/pmid:{pmid}"
    HTTP_HEADERS = {"authorization": OPEN_CITATIONS_API}

    try:
        response = requests.get(API_CALL, headers=HTTP_HEADERS, timeout=100)
        if response.status_code == 200:
            time.sleep(0.1)
            return response.json()[0]['count']
        
    except Exception as e:
        logging.error(f"Error fetching citation count from Open Citations for PMID {pmid}: {e}")
        return 0


def get_journal_rank(journal_issn: str) -> Optional[int]:
    """
    Get the rank of a journal from SciMago Journal Ranking data using ISSN.
    """
    with open(JOURNAL_DATA_PATH) as f:
        headers = ['Rank', 'Title', 'Issn']
        rows = csv.DictReader(f, fieldnames=headers, delimiter=',')
        next(rows)  # Skip header row

        for row in rows:
            row['Issn'] = row['Issn'].split(",")
            issn_list = ["00" + issn if len(issn) == 6 else issn for issn in row['Issn']]
            if journal_issn in issn_list:
                return int(row['Rank']) if row['Rank'].isdigit() else 50000

    return 50000

def min_max_rank(df: pd.DataFrame, column: str, invert: bool = False):
    """
    Normalize the given column using Min-Max scaling.
    If invert=True, higher values are mapped to lower scores (useful for ranking).
    """
    df[column] = pd.to_numeric(df[column], errors="coerce")

    min_val = df[column].min()
    max_val = df[column].max()

    if max_val == min_val:  # Avoid division by zero
        df[f"{column}_score"] = 1 if invert else 0
    else:
        if invert:
            df[f"{column}_score"] = round((max_val - df[column]) / (max_val - min_val), 2)
        else:
            df[f"{column}_score"] = round((df[column] - min_val) / (max_val - min_val), 2)

    return df[f"{column}_score"]

def generate_articles_rank(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]: 
    """
    Generate rank for each article using Journal Rank, Citation Count, and Recency.
    """
    df = pd.DataFrame(articles)
    df['Year'] = pd.to_numeric(df['Year'], errors='coerce').fillna(0).astype(int)
    
    # Compute recency score (more recent years get higher scores)
    min_year = df['Year'].min()
    max_year = df['Year'].max()
    
    print("min_year: ", min_year, max_year)
    if min_year != max_year:
        df['recency_score'] = round((df['Year'] - min_year) / (max_year - min_year), 2)
    else:
        df['recency_score'] = 0

    # Normalize cited by count
    df['citedby_score'] = min_max_rank(df, 'citedby')

    # Normalize journal rank (lower rank is better, so invert it)
    df['journal_rank_score'] = min_max_rank(df, 'journal_rank', invert=True)

    # average of all three scores
    df['overall_score'] = round((df['recency_score'] + df['citedby_score'] + df['journal_rank_score']) / 3, 2)

    df.sort_values(by='overall_score', ascending=False, inplace=True)

    # df.drop(columns=['citation_count_score'], axis=1, inplace=True)
    
    return df.to_dict('records')

def get_h_index_semantic_scholar(author_name):
    base_url = "https://api.semanticscholar.org/graph/v1/author/search"
    params = {"query": author_name, "fields": "authorId,name,hIndex"}
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)
        data = response.json()
        time.sleep(1)  # Avoid hitting API rate limits

        if data.get("data"):
            author = data["data"][0]  # Take the first match
            return author.get("hIndex", 0), author.get("authorId", 0)
        
    except requests.RequestException:
        pass

    return 0, 0 

def generate_articles_hindex(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]: 
    """
    Order the top 25 articles by overall score with H-index of the Last Author
    """
    df = pd.DataFrame(articles)
    df['hindex'] = 0
    df['hindex_score'] = 0.0
    top_df = df.head(25).copy()
    top_df['hindex'] = top_df['last_author'].apply(lambda x: get_h_index_semantic_scholar(x)[0] if pd.notna(x) else 0)
    top_df['hindex_score'] = min_max_rank(top_df, 'hindex')
    top_df.sort_values(by=['overall_score','hindex_score'], ascending=False, inplace=True)
    df.iloc[:25] = top_df.values
    return df.where(pd.notna(df), 0).to_dict('records')

def get_mesh_terms_in_article(article_content):
    mesh_details = {}

    for mesh_heading in article_content.findall(".//MeshHeading"):
        descriptor = mesh_heading.find("DescriptorName")
        qualifiers = mesh_heading.findall("QualifierName")

        descriptor_major = descriptor is not None and descriptor.attrib.get("MajorTopicYN") == "Y"
        qualifier_major = any(q.attrib.get("MajorTopicYN") == "Y" for q in qualifiers)

        # Include if either descriptor or any qualifier is a major topic
        if descriptor_major or qualifier_major:
            if descriptor is not None:
                mesh_details[descriptor.text] = descriptor.attrib.get("UI")

            # # Include qualifiers that are major topics (optional: comment out if not needed)
            # for q in qualifiers:
            #     if q.attrib.get("MajorTopicYN") == "Y":
            #         mesh_terms.append(f"{descriptor.text}")
            #         mesh_ids.append(q.attrib.get("UI"))

    return mesh_details

def fetch_literature_details_with_abstracts(disease_name: str,pmids: List[str]) -> List[Dict]:
    """
    Fetches detailed information including abstracts and publication type for a list of PMIDs.

    Args:
        pmids (List[str]): List of PubMed IDs.

    Returns:
        List[Dict]: A list of detailed information for the given PMIDs.
    """
    try:
        
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",  # Use XML to retrieve detailed information
            "api_key": NCBI_API_KEY
        }

        url = BASE_URL + "efetch.fcgi"
        response = get_data_from_pubmed(url, params)
        # print("pubmed response: ", response.text)
        # Parse XML response
        from xml.etree import ElementTree as ET
        root = ET.fromstring(response.text)
        
        articles = []
        for article in root.findall(".//PubmedArticle"):
            # Safe extraction of data with default values if tags are missing
            if article is None:
                continue  # Skip if no article data is found
            pmid = article.find(".//PMID")
            # print("pmid: ", pmid.text)
            article_title = article.find(".//ArticleTitle")
            vernacular_title=article.find(".//VernacularTitle")
            abstract = article.find(".//Abstract/AbstractText")
            pub_year = article.find(".//PubDate/Year")
            mesh_heading=article.find(".//MeshHeadingList")
            
            publication_types = article.findall(".//PublicationType") if article is not None else []

            # Safe extraction and handling of PublicationType elements
            publication_type_texts = [pub_type.text for pub_type in publication_types if pub_type is not None and pub_type.text]


            # Use default values (blank string for text, empty list for publication types) if tags are missing
            pmid_text = pmid.text if pmid is not None else ""
            article_title_text = extract_article_title(article_title) if article_title is not None else ""
            vernacular_title_text = extract_article_title(vernacular_title) if vernacular_title is not None else ""
            abstract_text = abstract.text if abstract is not None else ""
            year_text = pub_year.text if pub_year is not None else ""
            
            citedby_count = get_cited_by_count(pmid_text)
            journal_elem = article.find(".//Journal")
            title_elem = journal_elem.find('.//Title') if journal_elem is not None else None
            journal_name = title_elem.text if title_elem is not None else None

            issn_elem = journal_elem.find('.//ISSN') if journal_elem is not None else None
            journal_issn = issn_elem.text if issn_elem is not None else None

            # journal_name = article.find(".//Journal").find('.//Title').text if article.find(".//Journal") else None
            # journal_issn = article.find(".//Journal").find('.//ISSN').text if article.find(".//Journal") else None
            if journal_issn:
                journal_issn = journal_issn.replace('-','')
                journal_rank = get_journal_rank(journal_issn)

            authors_list = []
            last_author = None
            corresponding_author = None
            authors_ent = article.findall(".//AuthorList/Author")

            for index, auth in enumerate(authors_ent):
                fore_name = auth.find('ForeName')
                last_name = auth.find('LastName')

                if fore_name is not None and fore_name.text and last_name is not None and last_name.text:
                    auth_name = f"{fore_name.text.strip()} {last_name.text.strip()}"
                elif last_name is not None and last_name.text:
                    auth_name = last_name.text.strip()
                else:
                    auth_name = None

                if auth_name:
                    authors_list.append(auth_name)
                    if index == len(authors_ent) - 1:
                        last_author = auth_name

            # Create PubMed link using the PMID
            pubmed_link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid_text}/" if pmid_text else ""
            
            # If no publication types, default to empty list
            publication_type_texts = publication_type_texts if publication_type_texts else []

            mesh_details = get_mesh_terms_in_article(article)
            # Append article details with default values
            articles.append({
                "PMID": pmid_text,
                "Title": article_title_text if article_title_text!="[Not Available]." else vernacular_title_text,
                "Abstract": abstract_text,
                "Year": year_text,
                "PublicationType": publication_type_texts,
                "PubMedLink": pubmed_link,
                "Qualifers":extract_qualifiers_for_disease(mesh_heading,disease_name),
                "mesh_details": mesh_details,
                "citedby": citedby_count,
                "last_author": last_author,
                "authors": authors_list,
                "journal_name": journal_name if journal_name else "",
                "journal_issn": journal_issn if journal_issn else "",
                "journal_rank": journal_rank
            })
    
    except HTTPException as e:
        raise e
    
    except Exception as e:
        raise e
    
    # Rank the Articles based on Recency(Published Year), CitedBy Count(Open Citations API) and Journal Rank (SciMago Journal Ranking data)

    return articles


def fetch_literature_details_in_batches(disease_name:str,pmids: List[str], batch_size: int = 200) -> List[Dict]:
    """
    Fetches detailed information for a large list of PMIDs in batches.

    Args:
        disease_name: Name of the disease.
        pmids (List[str]): List of PubMed IDs.
        batch_size (int): The size of each batch. Default is 1000.

    Returns:
        List[Dict]: A combined list of detailed information for all PMIDs.
    """
    all_articles = []

    try:
        disease_name=get_mesh_term_for_disease(disease_name.replace("_"," "))
        # Process pmids in chunks of `batch_size`
        for i in range(0, len(pmids), batch_size):
            batch_pmids = pmids[i:i + batch_size]  # Get the current batch of PMIDs
            if not batch_pmids:  # Check if batch is empty (to prevent IndexError)
                continue
            
            print(f"Processing batch {i // batch_size + 1} of {len(pmids) // batch_size + 1}...\n")

            # Fetch the details for this batch
            batch_details = fetch_literature_details_with_abstracts(disease_name,batch_pmids)
            
            # print("batch details: ", batch_details)
            # Append the batch details to the overall list
            all_articles.extend(batch_details)
            time.sleep(1)
            print("all_articles ")

        if len(all_articles) > 0:   
            print("Ranking Articles according to Journal Rank, Recency and CitedBy count")
            ordered_articles = generate_articles_rank(all_articles)
            print("Fetching h-index of top 25 articles")
            hindex_ordered = generate_articles_hindex(ordered_articles)

            return hindex_ordered
        else:
            return all_articles
        
    except HTTPException as e:
        raise e
    
    except Exception as e:
        raise e

def generate_mapped_diseases_for_disease_area(disease_area, articles_data):
    """
    Annotate each article with the diseases falling under given disease area
    """
    def filter_mapped_diseases(disease_area_mesh_tree_numbers, article_tree_numbers):
        for da_tn in disease_area_mesh_tree_numbers:
            for tn in article_tree_numbers:
                if da_tn in tn:
                    print(f"Found matching tree number: Disease Area TN: {da_tn}, Article TN: {tn}")
                    return True
        return False

    disease_area_mesh_tree_numbers = get_mesh_tree_numbers_of_disease(disease_area)
    tree_numbers_dict = {}
    print("disease_area_mesh_tree_numbers: ", disease_area_mesh_tree_numbers)
    for article in articles_data:
        mapped_diseases = []
        mesh_details = article.get("mesh_details", {})
        if not mesh_details:
            llmclient = LLMClient()
            disease_efo_term = llmclient.identify_disease_efo_term(article.get("Title",""), article.get("Abstract","")).get('efo_term', "")
            if disease_efo_term:
                if disease_efo_term in tree_numbers_dict:
                    tree_numbers = tree_numbers_dict[disease_efo_term]
                else:
                    tree_numbers = get_mesh_tree_numbers_of_disease(disease_efo_term)
                    tree_numbers_dict[disease_efo_term] = tree_numbers
                
                is_child = filter_mapped_diseases(disease_area_mesh_tree_numbers, tree_numbers)
                if is_child:
                    print(f"Adding Mesh Term {disease_efo_term} for disease area {disease_area}")
                    mapped_diseases.append(disease_efo_term)

        else:
            for mesh_term, mesh_id in mesh_details.items():
                # print("mesh_term, mesh_id: ", mesh_term, mesh_id)
                if mesh_term in tree_numbers_dict:
                    tree_numbers = tree_numbers_dict[mesh_term]
                else:
                    time.sleep(0.1)
                    tree_numbers = get_mesh_tree_numbers_of_disease(mesh_term, mesh_id)
                    print("tree_numbers: ", tree_numbers)
                    tree_numbers_dict[mesh_term] = tree_numbers
            
                is_child = filter_mapped_diseases(disease_area_mesh_tree_numbers, tree_numbers)
                if is_child:
                    print(f"Adding Mesh Term {mesh_term} for disease area {disease_area}")
                    mapped_diseases.append(mesh_term)  

        article["mapped_diseases"] = list(set(mapped_diseases))

    return articles_data

def add_mapped_diseases(rna_seq_response: Dict[str, Any], pmid_key: str) -> Dict[str, Any]:
    """
    Add mapped diseases to the RNA-seq response.
    """
    def filter_mapped_diseases(disease_area_mesh_tree_numbers, article_tree_numbers):
        for da_tn in disease_area_mesh_tree_numbers:
            for tn in article_tree_numbers:
                if da_tn in tn:
                    print(f"Found matching tree number: Disease Area TN: {da_tn}, Article TN: {tn}")
                    return True
        return False
    
    tree_numbers_dict = {}

    for disease_area, articles_data in rna_seq_response.items():
        disease_area_mesh_tree_numbers = get_mesh_tree_numbers_of_disease(disease_area)
        for article in articles_data:
            print("+"*80)
            print(f"Processing article with {pmid_key}: {article.get(pmid_key, [])}")
            pmids = article.get(pmid_key, [])
            if pmids:
                if isinstance(pmids, int):
                    pmids = [str(pmids)]
                elif isinstance(pmids, str):
                    pmids = [pmids]
                for pmid in pmids:
                    
                    mesh_details = pmid_to_meshid_mapper(pmid)
                    time.sleep(0.1)
                    if mesh_details:
                        article["mesh_details"] = mesh_details
                        article["mapped_diseases"] = []
                        for mesh_term, mesh_id in mesh_details.items():
                            if mesh_id not in tree_numbers_dict:
                                tree_numbers_dict[mesh_id] = get_mesh_tree_numbers_of_disease(mesh_term, mesh_id)
                            # if any('.' not in tn for tn in tree_numbers):
                            #     continue

                            # if mesh_id in tree_numbers_dict and tree_numbers_dict[mesh_id]:
                            tn_list = tree_numbers_dict[mesh_id]
                            is_child = filter_mapped_diseases(disease_area_mesh_tree_numbers, tn_list)
                            if is_child:
                                article["mapped_diseases"].append(mesh_term)
                            time.sleep(0.1)
            # elif pmids == [] or 'mesh_details' not in article:
            #     llmclient = LLMClient()
            #     disease_efo_term = llmclient.identify_disease_efo_term(article.get("Title",""), article.get("Abstract","")).get('efo_term', "")
            #     if disease_efo_term and disease_efo_term not in ['null', 'N/A', 'none', 'None', '']:
            #         logger.info(f"Fetching tree numbers for efo term: {disease_efo_term} for {article.get('PMID','')}")
            #         if disease_efo_term in tree_numbers_dict:
            #             tree_numbers = tree_numbers_dict[disease_efo_term]
            #         else:
            #             tree_numbers = get_mesh_tree_numbers_of_disease(disease_efo_term)

            #         if tree_numbers:
            #             tree_numbers_dict[disease_efo_term] = tree_numbers

            #             is_child = filter_mapped_diseases(disease_area_mesh_tree_numbers, tree_numbers)
            #             if is_child:
            #                 article["mapped_diseases"] = [disease_efo_term]
            #             else:
            #                 article["mapped_diseases"] = []
            #     else:
            #         article["mesh_details"] = {}
            #         article["mapped_diseases"] = []

            article["mapped_diseases"] = list(set(article.get("mapped_diseases", [])))
        return rna_seq_response


def fetch_mouse_models(query: str) -> Dict[str, Any]:
    """
    Fetch mouse models for a specific disease query using MouseMine API.

    Args:
        query (str): The disease query string (e.g., "alzheimer*").

    Returns:
        Dict[str, Any]: A dictionary containing the count of filtered rows 
                        and the filtered data with URLs for each row.
    """
    # URL with the specified disease query
    url = (
        "https://www.mousemine.org/mousemine/service/template/results?"
        "name=HDisease_MModel&constraint1=OntologyAnnotation.ontologyTerm.parents"
        f"&op1=LOOKUP&value1={query}&extra1=&format=tab"
    )

    try:
        # Send a GET request to fetch the data
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception if the request failed
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from MouseMine API: {e}")
        return {"count": 0, "data": []}

    # Process the TSV data
    lines = response.text.splitlines()
    if not lines:
        print("Error: Received empty response from the API.")
        return {"count": 0, "data": []}

    # Define column names explicitly
    columns = [
        "ontologyTerm.identifier",  # Column 1
        "ontologyTerm.name",        # Column 2
        "qualifier",                # Column 3
        "subject.symbol",           # Column 4
        "subject.background.name",  # Column 5
        "subject.zygosity"          # Column 6
    ]

    try:
        # Verify the number of columns in the header
        header_columns = len(lines[0].split("\t"))
        if header_columns != len(columns):
            print(f"Warning: Expected {len(columns)} columns but found {header_columns}. Data may not match.")
    except IndexError:
        print("Error: Response data is malformed.")
        return {"count": 0, "data": []}

    # Create a DictReader with the correct column headers
    reader = csv.DictReader(lines, delimiter="\t", fieldnames=columns)
    results = [row for row in reader]

    # Filter out rows where qualifier is "NOT"
    filtered_results = []
    for row in results:
        if row.get("qualifier") != "NOT":
            # Add a URL field to each row
            ontology_id = row.get("ontologyTerm.identifier")
            if ontology_id:
                row["url"] = f"https://www.informatics.jax.org/disease/{ontology_id}?openTab=models"
            else:
                row["url"] = ""  # Handle missing ontologyTerm.identifier gracefully
            filtered_results.append(row)

    return {
        "count": len(filtered_results),
        "data": filtered_results
    }


def convert_pmc_to_pmid(pmc_id: str) -> Optional[str]:
    """
    Convert a PubMed Central (PMC) ID to a PubMed ID (PMID) using NCBI E-utilities.

    Args:
        pmc_id (str): The PMC ID to convert.

    Returns:
        Optional[str]: The corresponding PMID, or an empty string if no match is found or if pmc_id is empty.
    """
    # Return empty string if pmc_id is empty
    if not pmc_id.strip():
        return ""

    Entrez.email = EMAIL  # Replace with your email
    Entrez.api_key = NCBI_API_KEY
    try:
        # Use the Entrez elink utility to link PMC to PMID
        handle = Entrez.elink(dbfrom="pmc", db="pubmed", id=pmc_id)
        record = Entrez.read(handle)
        handle.close()

        # Extract the PMID from the record
        linkset = record[0]
        if "LinkSetDb" in linkset and len(linkset["LinkSetDb"]) > 0:
            pmid = linkset["LinkSetDb"][0]["Link"][0]["Id"]
            return pmid
        else:
            return ""
    except Exception as e:
        print(f"Error converting PMC ID {pmc_id} to PMID: {e}")
        return ""

def fetch_mesh_major_terms(pmid: str) -> list:
    """
    Fetches all MeSH terms (including major and non-major topics) for a given PubMed ID (PMID) using efetch.
    """
    if not pmid:
        return []

    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    
    # Request parameters
    params = {
        'db': 'pubmed', 
        'id': pmid,  
        'retmode': 'xml',
        "api_key": NCBI_API_KEY   
    }
    
    try:
        # response = requests.get(url, params=params)
        # if response.status_code == 429:
        #     # raise Exception("Too Many Requests: You are being rate-limited. Please try again later.")
        #     rate_limited_until = time.time() + RATE_LIMIT_RETRY_PERIOD
        #     raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Try again after {RATE_LIMIT_RETRY_PERIOD} seconds.")

        # response.raise_for_status()  
        response = get_data_from_pubmed(url, params)

        # Parse the XML response
        tree = ElementTree.fromstring(response.content)
        
        # Extract all MeSH terms
        mesh_terms = [
            mesh.find("DescriptorName").text
            for mesh in tree.findall(".//MeshHeading")
            if mesh.find("DescriptorName") is not None
        ]

        return mesh_terms
    except HTTPException as e:
        raise e
    
    except Exception as e:
        print(f"An error occurred while fetching MeSH terms for PMID '{pmid}': {e}")
        return []
    

def is_disease_in_mesh_terms(pmid: str, disease_name: str) -> bool:
    """
    Checks if a given disease name is present in the list of MeSH Major Terms for a given PubMed ID (PMID).
    
    Args:
    - pmid (str): PubMed ID (PMID) of the article.
    - disease_name (str): The disease name to search for in the MeSH Major Terms list.
    
    Returns:
    - bool: True if the disease name is present in the MeSH Major Terms list, otherwise False.
    """
    try:
        # Fetch MeSH Major Terms for the given PMID
        mesh_terms = fetch_mesh_major_terms(pmid)
        
        # Ensure mesh_terms is a list, even if it's empty
        if not isinstance(mesh_terms, list):
            raise ValueError(f"Expected a list of MeSH terms, but got {type(mesh_terms)}")
        
        # Print the MeSH Major Terms for debugging
        # print(f"Mesh Majors for PMID {pmid}: {mesh_terms}")
        
        if disease_name.lower()=="atopic dermatitis":
            disease_name="dermatitis, atopic"
        
        time.sleep(1)

        # Check if the disease name is present in the MeSH Major Terms list (case-insensitive)
        return disease_name.lower() in [term.lower() for term in mesh_terms]

    except HTTPException as e:
        raise e
    except Exception as e:
        # Handle unexpected errors (e.g., network issues, invalid data)
        print(f"Error while processing PMID {pmid}: {e}")
        return False  # Return False in case of an error


def enrich_with_pmid(data: List[Dict]) -> List[Dict]:
    """
    Enriches a list of dictionaries containing PMC IDs with corresponding PM IDs.

    Args:
        data (List[Dict]): A list of dictionaries where each contains a `pmcid`.

    Returns:
        List[Dict]: The input list with an added `pmid` key for each dictionary.
    """
    def chunk_list(lst: List[Dict], chunk_size: int) -> List[List[Dict]]| Any:
        """
        Splits a list into smaller chunks of a given size.

        Args:
            lst (List[Dict]): The list to be split.
            chunk_size (int): The size of each chunk.

        Returns:
            List[List[Dict]]: A list of smaller chunks.
        """
        for i in range(0, len(lst), chunk_size):
            yield lst[i:i + chunk_size]

    # Define your tool name and email for API usage
    tool_name = "my_tool"
    email = EMAIL

    # URL for the NCBI ID Converter API
    base_url = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
    max_ids_per_request = 200  # Maximum number of IDs allowed per request

    # Enrich data by processing in chunks
    for chunk in chunk_list(data, max_ids_per_request):
        # Extract PMC IDs from the current chunk
        pmc_ids = [entry["pmcid"] for entry in chunk]

        # Make the API request
        params = {
            "tool": tool_name,
            "email": email,
            "ids": ",".join(pmc_ids),
            "format": "json",
            "api_key": NCBI_API_KEY
        }

        try:
            # response = requests.get(base_url, params=params)
            # if response.status_code == 429:
            # # raise Exception("Too Many Requests: You are being rate-limited. Please try again later.")
            #     rate_limited_until = time.time() + RATE_LIMIT_RETRY_PERIOD
            #     raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Try again after {RATE_LIMIT_RETRY_PERIOD} seconds.")

            # response.raise_for_status()  # Raise exception for HTTP errors
            response = get_data_from_pubmed(base_url, params)
            api_data = response.json()
            time.sleep(3)

            # Create a mapping of PMC to PM IDs
            pmc_to_pmids = {
                record.get("pmcid"): record.get("pmid")
                for record in api_data.get("records", [])
            }

            # Update the original data with PM IDs
            for entry in chunk:
                entry["pmid"] = pmc_to_pmids.get(entry["pmcid"], "")


        
        except HTTPException as e:
            raise e
        
        except Exception as e:
            print(f"An error occurred while processing PMC IDs {pmc_ids}: {e}")
            raise e
        # Add a delay to avoid overloading the server
        time.sleep(1)

    return data


def fetch_gene_symbols_from_figid(figure_id: str) -> List[str]:
    """
    Fetches the ncbigene_symbol values from the TSV file for a given figure ID,
    filtering records where organism_name is 'Homo sapiens'.
    
    Args:
        figure_id (str): The figure ID to construct the URL.
        
    Returns:
        List[str]: A list of gene symbols found in the TSV file.
    """
    url: str = f"https://raw.githubusercontent.com/wikipathways/pfocr-database/main/_data/{figure_id}-genes.tsv"
    gene_symbols: List[str] = []
    
    try:
        # Fetch the TSV data from the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTP errors if any
        
        # Process the TSV content
        lines = response.text.strip().split("\n")
        headers = lines[0].split("\t")
        
        # Check if required headers are present
        if "ncbigene_symbol" not in headers or "organism_name" not in headers:
            # print(f"Required fields ('ncbigene_symbol' or 'organism_name') not found in TSV headers for figure ID {figure_id}.")
            return []

        # Find the indices of the relevant columns
        symbol_index = headers.index("ncbigene_symbol")
        organism_index = headers.index("organism_name")
        
        # Extract gene symbols from rows where organism_name is 'Homo sapiens'
        max_index = max(symbol_index, organism_index)
        for line in lines[1:]:
            fields = line.split("\t")
            if len(fields) >  max_index and fields[organism_index] == "Homo sapiens":
                gene_symbols.append(fields[symbol_index])
                
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
    except Exception as e:  # Handle any unexpected exceptions
        print(f"An error occurred: {e}")
    
    return gene_symbols


def get_network_biology_strapi(disease_name: str) -> List[Dict[str, Any]]:
    """
    Fetches and filters key influencers data from Strapi for the given disease name.

    Args:
        disease_name (str): The name of the disease to filter key influencers.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing filtered data fields.
    """
    # Define the API endpoint, dynamically include the disease name
    STRAPI_BASE_URL = os.getenv("STRAPI_BASE_URL")
    url = (
        f"{STRAPI_BASE_URL}/api/disease-pathway-figures"
        f"?filters[disease][$eqi]={disease_name}&fields[0]=disease&fields[1]=pmid"
        f"&fields[2]=figtitle&fields[3]=image_url&fields[4]=gene_symbols&fields[5]=pmcid&pagination[page]=1&pagination[pageSize]=500"
    )

    # Retrieve the API token
    api_token: str = os.getenv('STRAPI_API_TOKEN') 

    if not api_token:
        print("API token not found in environment variables. Set 'STRAPI_API_TOKEN'.")
        return []

    # Define the headers with the authorization token
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    try:
        # Send a GET request to retrieve data
        response = requests.get(url, headers=headers)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()
            filtered_data = []

            # Extract only the relevant fields
            for item in data.get("data", []):
                filtered_data.append({
                    "disease": item.get("disease","").lower(),
                    "pmid": item.get("pmid",""),
                    "pmcid":item.get("pmcid",""),
                    "figtitle": item.get("figtitle",""),
                    "image_url": item.get("image_url",""),
                    "gene_symbols": item.get("gene_symbols",[])
                })

            return filtered_data
        else:
            # If there's an error, print the status code and error message
            print(f"Failed to fetch data. Status code: {response.status_code}")
            # print(response.text)
            return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def fetch_and_filter_figures_by_disease_and_pmids(disease: str) -> List[Dict[str, str]]:
    """
    Fetch data from the API and filter figures based on:
      1. Presence of a disease in the figtitle.
      2. Inclusion of the pmid in a provided list.
    Assigns blank strings to missing fields.
    
    Args:
        api_url (str): The API URL to fetch data from.
        disease (str): Disease name to filter by.
        pmid_list (List[str]): List of PMIDs to filter against.
    
    Returns:
        List[Dict[str, str]]: Filtered list containing the required fields.
    """
    try:
        api_url: str="https://pfocr.wikipathways.org/json/getFigureInfo.json"
        # Fetch data from the API
        response = requests.get(api_url)
        
        # Check if the request was successful
        if response.status_code != 200:
            raise Exception(f"Failed to fetch data from the API. Status code: {response.status_code}")
        
        data = response.json()
        
        filtered_figures = []
        disease_lower = disease.lower()
        # print('Disease lower sending to get the mesh term', disease_lower)
        disease_mesh_term=get_mesh_term_for_disease(disease_lower)
        mesh_entry_terms_for_disease = fetch_mesh_entry_terms(disease_mesh_term)
        # Filter the figures based on the disease name in the figtitle
        for figure in data.get("figureInfo", []):
            figtitle = figure.get("figtitle", "").lower().replace("’", "'").replace("&#39;", "'")
            if (disease_mesh_term and disease_mesh_term in figtitle) or any(keyword.lower() in figtitle for keyword in mesh_entry_terms_for_disease):
                figid = figure.get("figid", "")
                # print(figtitle)
                figid_parts = figid.split("__") if figid else []
                
                if len(figid_parts) == 2:
                    first_part, second_part = figid_parts
                    image_url = f"https://europepmc.org/articles/{first_part}/bin/{second_part}.jpg"
                else:
                    image_url = ""
                
                filtered_figures.append({
                    "url": figure.get("url", ""),
                    "pmcid": figure.get("pmcid", ""),
                    "figtitle": figure.get("figtitle", ""),
                    "figid": figid,
                    "image_url": image_url
                })
        
        # Print the length of the array before filtering by PMIDs
        print(f"Number of records before filtering by PMIDs: {len(filtered_figures)}")
        filtered_figures=enrich_with_pmid(filtered_figures)
        # print(filtered_figures)
        # Filter by PMIDs
        filtered_figures = [figure for figure in filtered_figures if is_disease_in_mesh_terms(figure.get("pmid", ""),disease_mesh_term)]

        # Print the length of the array after filtering by PMIDs
        print(f"Number of records after filtering by PMIDs: {len(filtered_figures)}")
        
        # getting list of genes for each figure
        for figure in filtered_figures:
            figid: str = figure.get("figid", "")
            # Fetch gene symbols for the current figure
            gene_symbols: List[str] = fetch_gene_symbols_from_figid(figid)
            # Add gene symbols to the figure dictionary
            figure["gene_symbols"] = gene_symbols
        # strapi_result=get_network_biology_strapi(disease_name=disease)
        # filtered_figures.extend(strapi_result)
    except HTTPException as e:
        raise e
    return filtered_figures

def get_doid(disease_name: str) -> str:
    """
    Fetch the Disease Ontology ID (DOID) for a given disease name using the OLS API.

    :param disease_name: Name of the disease to search for.
    :return: DOID of the disease, or a message if not found.
    """
    url = "https://www.ebi.ac.uk/ols/api/search"
    params = {"q": disease_name, "ontology": "doid"}

    response = requests.get(url, params=params)
    if response.status_code == 200:
        results = response.json().get("response", {}).get("docs", [])
        if results:
            return results[0]["obo_id"]  # Return the first match's DOID
        else:
            print("No DOID found for the disease.")
            return ""
    else:
        print(f"Error: {response.status_code}")
        return ""


def add_source_urls_to_records(records: List[Dict[str, str]], doid: str) -> List[Dict[str, str]]:
    """
    Fetches the TSV file for the given DOID from the Alliance Genome API,
    extracts the 'Source URL' column, and adds each Source URL to the records.

    Args:
        records (List[Dict[str, str]]): List of dictionaries representing records.
        doid (str): The Disease Ontology ID (DOID) to fetch the TSV file for.

    Returns:
        List[Dict[str, str]]: The updated list of records with a new 'SourceURL' field added.
    """
    # Construct the URL with the given DOID
    url = f"https://www.alliancegenome.org/api/disease/{doid}/models/download"

    try:
        # Fetch the TSV data
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for non-200 responses

        # Read the TSV data into a pandas DataFrame
        tsv_data = pd.read_csv(io.StringIO(response.text), sep="\t")

        # Check if 'Source URL' column exists
        if 'Source URL' not in tsv_data.columns:
            print("The 'Source URL' column is missing in the TSV data.")
            return records

        # Extract the 'Source URL' column as a list
        source_urls = tsv_data['Source URL'].tolist()

        # Add each Source URL to the records
        for i, source_url in enumerate(source_urls):
            # If there are more source URLs than records, create new empty records
            records[i]['SourceURL'] = source_url if pd.notna(source_url) else ""

        return records
    except Exception as e:
        print(f"An error occurred: {e}")
        return records

def get_disease_details(efo_id: str) -> Dict[str, Any]:
    """
    Fetch disease details from Open Targets using the EFO ID.
    """
    print(f"[STEP 2] 🔍 Fetching disease details for EFO ID: {efo_id}")
    
    base_url: str = "https://api.platform.opentargets.org/api/v4/graphql"
    variables = {"efoId": efo_id}
    try:
        disease_details_query = """
            query disease($efoId: String!) {
            disease(efoId: $efoId) {
                id
                name
                dbXRefs
            }
            }
            """
        response = requests.post(
            base_url,
            json={'query': disease_details_query, 'variables': variables}
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"[STEP 2] ✅ Disease details retrieved successfully")
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"[STEP 2] ❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error while connecting to the API: {str(e)}")


def get_doid_from_disease_details(details: Dict[str, Any]) -> Optional[str]:
    """
    Extract DOID from the dbXRefs in the disease details.
    """
    print(f"[STEP 3] 🔍 Extracting DOID from dbXRefs...")
    
    dbxrefs = details.get("data", {}).get("disease", {}).get("dbXRefs", [])
    
    print(f"[STEP 3] 📋 Available dbXRefs: {dbxrefs}")
    
    for ref in dbxrefs:
        if ref.startswith("DOID:"):
            print(f"[STEP 3] ✅ DOID found: {ref}")
            return ref
    
    print(f"[STEP 3] ❌ No DOID found in dbXRefs")
    return None

def fetch_mouse_model_data_alliancegenome(disease_name: str, efo_id:str) -> List[Dict[str, Any]]:
    """
    Fetch and process disease data for the given disease name from alliance genome and return the result as JSON.
    Handles errors such as invalid disease names, API issues, and missing data.
    Prints the error and returns an empty list in case of an error.

    Args:
        disease_name (str): The name of the disease.

    Returns:
        List[Dict[str, Any]]: The processed data in JSON format, or an empty list on error.
    """
    # API base URL
    api_url = "https://www.alliancegenome.org"
    
    try:
        # Extract DOID from the first result
        # disease_id = get_doid(disease_name)

        disease_id = get_doid_from_disease_details(get_disease_details(efo_id))
        # Fetch the disease-related models data using the DOID
        # Alliance genome imposes a limit of 20, therefore overriding with a large number
        response = requests.get(f"{api_url}/api/disease/{disease_id}/models?limit=1000")
        response.raise_for_status()  # Raise an error for bad HTTP responses

        # Check if results are available
        raw_data = response.json().get("results", [])
        if not raw_data:
            print(f"Error: No model data found for disease '{disease_name}'.")
            return []

        # Step 3: Process the data and extract relevant information
        extracted_data = []

        for association in raw_data:
            row = {
                "Model": association.get("subject", {}).get("agmFullName", {}).get("displayText", ""),  # Model name
                "Species": association.get("subject", {}).get("taxon", {}).get("name", ""),  # Species
                "ExperimentalCondition": association.get("experimentalConditionList", []),  # Experimental conditions
                "Association": association.get("generatedRelationString", ""),  # Association type
                "DiseaseQualifiers": association.get("diseaseQualifiers"),  # Disease qualifiers
                "Disease": association.get("object", {}).get("name", ""),  # Disease name
                "ConditionModifier": association.get("conditionModifierList", []),  # Condition modifiers
                "GeneticModifier": association.get("geneticModifierList"),  # Genetic modifiers
                "Evidence": [evidence.get("abbreviation", "") for evidence in association.get("evidenceCodes", [])],  # Evidence codes
                "References": [ref.split(":")[1] for ref in association.get("pubmedPubModIDs", []) if ":" in ref],  # Extract only the ID part of PMID
                "Gene": (
                association.get("primaryAnnotations", [{}])[0]
                .get("inferredGene", {})
                .get("geneFullName", {})
                .get("displayText", "")
                or association.get("primaryAnnotations", [{}])[0]
                .get("inferredGene", {})
                .get("geneFullName", {})
                .get("formatText", "")
                if association.get("primaryAnnotations", [{}])[0].get("inferredGene") is not None
                else ""
                    )
            }
        
            extracted_data.append(row)
        extracted_data=add_source_urls_to_records(extracted_data,disease_id)
        # Return the processed data as JSON
        return extracted_data

    except requests.exceptions.RequestException as e:
        # Catch network or HTTP errors
        print(f"Network or HTTP error: {str(e)}")
        return []
    except Exception as e:
        # Catch any other unforeseen errors
        print(f"An unexpected error occurred: {str(e)}")
        return []
    

def get_top_10_literature_helper(disease_name: str) -> list[Any] | Any:
    """
    Fetches key top 10 literature data from Strapi based on the provided disease name.

    Args:
        disease_name (str): The name of the disease to filter key influencers.

    Returns:
        dict or None: The JSON response from the API if successful, None otherwise.
    """
    # Define the API endpoint, dynamically include the disease name
    STRAPI_BASE_URL = os.getenv("STRAPI_BASE_URL")
    url = f"{STRAPI_BASE_URL}/api/top-10-literatures?filters[disease][$eqi]={disease_name}&fields[0]=disease&fields[1]=year&fields[2]=title_text&fields[3]=title_url"

    # Retrieve the API token from the environment variable
    api_token = os.getenv('STRAPI_API_TOKEN')

    if not api_token:
        print("API token not found in environment variables. Set 'STRAPI_API_TOKEN'.")
        return []

    # Define the headers with authorization token
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    try:
        # Send a GET request to retrieve data
        response = requests.get(url, headers=headers)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse and return the JSON response
            data = response.json()
            return data["data"]
        else:
            # If there's an error, print the status code and error message
            print(f"Failed to fetch data. Status code: {response.status_code}")
            # print(response.text)
            return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []
    

def add_platform_name(data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Adds a new field 'PlatformName' to each record in the input data, 
    extracted from the 'Platform' field.

    Parameters:
        data (Dict[str, List[Dict[str, Any]]]): Input data where each disease has a list of records.

    Returns:
        Dict[str, List[Dict[str, Any]]]: The modified data with 'PlatformName' added to each record.
    """
    for disease, records in data.items():
        for record in records:
            # Check if 'Platform' exists and is valid
            if "Platform" in record and isinstance(record["Platform"], dict):
                # Extract the values from the Platform dictionary
                platform_values: List[str] = list(record["Platform"].values())

                # Extract the text before the first '(' if it exists
                record["PlatformNames"] = [
                    value.split(" (")[0] if " (" in value else value for value in platform_values
                ]
            else:
                # Default to an empty list if 'Platform' is missing or invalid
                record["PlatformName"] = []
    
    return data

def add_study_type(data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Adds a new field 'StudyType' to each record in the input data.
    The 'StudyType' is determined by searching specific keywords in the 'Design' field.

    Parameters:
        data (Dict[str, List[Dict[str, Any]]]): Input data where each disease has a list of records.

    Returns:
        Dict[str, List[Dict[str, Any]]]: The modified data with 'DesignType' added to each record.
    """
    # Keywords to identify sc-RNA designs (case-insensitive)
    # Keywords to identify sc-RNA designs (case-insensitive)
    sc_keywords: List[str] = ["single cell", "scrna-seq", "single-cell", "single","sc-rna","scrnaseq","scrna"]
    # bc_keywords: List[str]=["rna-sequencing","rna sequencing","bulk rna","bulk-rna","rna-seq","rna seq"]
    micro_array_keywords: List[str]=["array"]

    for disease, records in data.items():
        for record in records:
            # Combine elements of 'Design' (if it exists and is a list) and 'Title' (if it exists and is a list) into a single string
            design_string: str = " ".join(record.get("Design", [])).lower() if isinstance(record.get("Design"), list) else ""
            title_string: str = " ".join(record.get("Title", [])).lower() if isinstance(record.get("Title"), list) else ""
            combined_string: str = f"{design_string} {title_string}"
            experiment_type: str=record.get("ExperimentType","").lower()

            # Check if any sc-RNA keyword exists in the combined string
            if any(keyword in combined_string for keyword in sc_keywords):
                record["StudyType"] = "scRNA"
            elif any(keyword in experiment_type for keyword in micro_array_keywords):
                record["StudyType"] = "Microarray"
            else:
                record["StudyType"] = "bulkRNA"
    
    return data


def add_sample_type(data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Adds a new field 'SampleType' to each record with additional debug logging.
    Modified to only use 'Diseased' and 'Both' categories based on specific criteria.
    """
    logging.info("Starting add_sample_type function")
    
    try:
        # Keywords to identify control samples (case-insensitive)
        control_keywords: List[str] = [
            "control", "healthy", "normal", "baseline", "wild type", 
            "sham", "disease free", "unaffected", "ctrl"
        ]
        
        # Keywords to identify diseased samples (case-insensitive)
        disease_keywords: List[str] = [
            "disease", "affected", "pathological", "case", "patient", 
            "tumor", "cancer", "infected", "lesion", "fibrosis", 
            "inflammation", "dysplastic", "mutant", "knockout", 
            "treated", "experimental", "induced", "injury", "drug"
        ]

        for disease, records in data.items():
            logging.info(f"Processing disease: {disease} with {len(records)} records")
            
            for i, record in enumerate(records):
                try:
                    logging.info(f"Processing record {i} for disease {disease}")
                    
                    # Safe string extraction with type checking
                    title_string = ""
                    if "Title" in record:
                        if isinstance(record["Title"], list):
                            title_items = []
                            for item in record["Title"]:
                                title_items.append(str(item))
                            title_string = " ".join(title_items).lower()
                        elif isinstance(record["Title"], str):
                            title_string = record["Title"].lower()
                        else:
                            logging.warning(f"Unexpected Title type: {type(record['Title'])}")
                    
                    design_string = ""
                    if "Design" in record:
                        if isinstance(record["Design"], list):
                            design_items = []
                            for item in record["Design"]:
                                design_items.append(str(item))
                            design_string = " ".join(design_items).lower()
                        elif isinstance(record["Design"], str):
                            design_string = record["Design"].lower()
                        else:
                            logging.warning(f"Unexpected Design type: {type(record['Design'])}")
                    
                    summary_string = ""
                    if "Summary" in record and record["Summary"] is not None:
                        summary_string = str(record["Summary"]).lower()
                    
                    sample_string = ""
                    if "Samples" in record:
                        if isinstance(record["Samples"], list):
                            sample_items = []
                            for item in record["Samples"]:
                                sample_items.append(str(item))
                            sample_string = " ".join(sample_items).lower()
                        elif isinstance(record["Samples"], str):
                            sample_string = record["Samples"].lower()
                        else:
                            logging.warning(f"Unexpected Samples type: {type(record['Samples'])}")
                    
                    # Combine all strings for comprehensive searching
                    combined_string = f"{title_string} {design_string} {summary_string} {sample_string}"
                    
                    # Check for presence of control and disease keywords
                    has_control = any(keyword in combined_string for keyword in control_keywords)
                    has_disease = any(keyword in combined_string for keyword in disease_keywords)
                    
                    # Modified logic: Only use 'Diseased' and 'Both' categories
                    if has_control and has_disease:
                        record["SampleType"] = "Both"
                    elif has_disease and not has_control:
                        record["SampleType"] = "Diseased"
                    else:
                        # Default case - not having disease keywords or having only control keywords
                        record["SampleType"] = "Unknown"
                        
                    logging.info(f"Record {i} processed successfully, SampleType: {record['SampleType']}")
                    
                except Exception as e:
                    logging.error(f"Error processing record {i}: {str(e)}")
                    record["SampleType"] = "Error"  # Set a default value
                    
        logging.info("Completed add_sample_type function")
        return data
        
    except Exception as e:
        logging.error(f"Fatal error in add_sample_type: {str(e)}")
        # Return original data if function fails
        return data




# Function to fetch MeSH descriptor data for a disease name
def fetch_mesh_descriptor(disease_name):
    print("Fetching descriptor data for the disease name...")
    search_url = "https://id.nlm.nih.gov/mesh/lookup/descriptor"
    params = {"label": disease_name}  # Search term
    response = requests.get(search_url, params=params)
    response.raise_for_status()
    results = response.json()

    if not results:
        raise ValueError(f"No descriptor found for '{disease_name}'.")

    time.sleep(0.5)

    # Fetch descriptor data using the resource URL
    descriptor_url = results[0]["resource"]
    descriptor_response = requests.get(descriptor_url + ".json")
    descriptor_response.raise_for_status()
    return descriptor_response.json()


def fetch_mesh_terms(disease_name):
    try:
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            "db": "mesh",       # Search in MeSH database
            "term": disease_name, # Query term (disease name)
            "retmode": "json" ,   # Return results in JSON format
            "api_key": NCBI_API_KEY
        }
        # response = requests.get(base_url, params=params)
        # if response.status_code == 429:
        #     # raise Exception("Too Many Requests: You are being rate-limited. Please try again later.")
        #     rate_limited_until = time.time() + RATE_LIMIT_RETRY_PERIOD
        #     raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Try again after {RATE_LIMIT_RETRY_PERIOD} seconds.")

        # response.raise_for_status()  # Raise an error for HTTP issues
        response = get_data_from_pubmed(base_url, params)
        time.sleep(0.5)
        data = response.json()
        #print (data)

    except HTTPException as e:
        raise e
    except Exception as e:
        data.get("esearchresult", {}).get("idlist", [])
    return data.get("esearchresult", {}).get("idlist", [])  # List of MeSH term IDs

def fetch_mesh_details(mesh_id):
    try:
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        params = {
            "db": "mesh",
            "id": mesh_id,
            "retmode": "json",
            "api_key": NCBI_API_KEY
        }
        # response = requests.get(base_url, params=params)
        # if response.status_code == 429:
        #     # raise Exception("Too Many Requests: You are being rate-limited. Please try again later.")
        #     rate_limited_until = time.time() + RATE_LIMIT_RETRY_PERIOD
        #     raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Try again after {RATE_LIMIT_RETRY_PERIOD} seconds.")

        # response.raise_for_status()
        response = get_data_from_pubmed(base_url, params)
        time.sleep(0.5)
        mesh_details = response.json()

    except Exception as e:
        raise e
    return mesh_details
    # fetch the ds_meshterms from mesh_details

def extract_mesh_terms(data, unique_id):
    mesh_terms = []
    # Use a stack (list) to manage the traversal
    stack = [data]
    
    while stack:
        current_item = stack.pop()
        
        # If the current item is a dictionary, check for 'ds_meshterms' and 'ds_meshui'
        if isinstance(current_item, dict):
            if 'ds_meshterms' in current_item and 'ds_meshui' in current_item:
                if current_item['ds_meshui'] == unique_id:
                    mesh_terms.extend(current_item['ds_meshterms'])
                    return mesh_terms
         
            # Add the dictionary's values to the stack for further checking
            stack.extend(value for value in current_item.values() if isinstance(value, (dict, list)))
        
        # If the current item is a list, process each item in the list
        elif isinstance(current_item, list):
            # Add each item in the list to the stack
            stack.extend(item for item in current_item if isinstance(item, (dict, list)))
    
    return mesh_terms



def fetch_mesh_entry_terms(disease_name):
    """ Returns mesh entry terms for a given disease """

    mesh_entry_terms = []
    try:
       # Step 1: Get the descriptor data for a given disease
        descriptor_data = fetch_mesh_descriptor(disease_name)

        # Step 2: Get Mesh IDs for a given disease
        mesh_ids = fetch_mesh_terms (disease_name)

        # Step 3: Extract the unique ID from the descriptor data
        descriptor_url = descriptor_data["@id"]
        unique_id = descriptor_url.split("/")[-1]
        # print(f"Unique ID for {disease_name}: {unique_id}")

        # print(f"Mesh IDs: {mesh_ids}")

        details = []
        # Step 4: Iterate over the Mesh IDs for the disease and collate all the mesh details for all Mesh IDs
        for mesh_id in mesh_ids:
            details.append(fetch_mesh_details(mesh_id))

        # Step 5: Within all of the Mesh details for all of the Mesh IDs, search for the unique ID
        # The unique ID will be found with an element called ds_meshui
        # For this ds_meshui, fetch ds_meshterms
        mesh_entry_terms = extract_mesh_terms (details, unique_id)

        # print (f"\nMesh Entry Terms: {mesh_entry_terms}")
    except Exception as e:
        print(f"An error occurred: {e}")
    return mesh_entry_terms


if __name__ == "__main__":
    # rna_seq_data_path = "/app/res-immunology-automation/res_immunology_automation/src/scripts/cached_data_json/disease/obesity.json"
    # with open(rna_seq_data_path, 'r') as file:
    #     data = json.load(file)
    #     rna_seq_data = data["/evidence/rna-sequence/"] 
    
    # rna_seq_updated = add_mapped_diseases(rna_seq_data)
    # with open("rna_seq_updated.json", 'w') as outfile:
    #     json.dump(rna_seq_updated, outfile, indent=4)
    target_name = "gucy1a1"
    disease_name = "cardiovascular diseases"
    target_terms_file = "/app/res-immunology-automation/res_immunology_automation/src/scripts/target_data/target_terms.json"
    mesh_major_term="cardiovascular diseases"  # cardiovascular diseases
    search_pubmed_target(target_name, disease_name, target_terms_file, mesh_major_term)
    