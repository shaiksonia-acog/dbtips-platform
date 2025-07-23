import os
import sys
from typing import List, Dict, Any, Tuple,Optional,Union
import requests
import json
from xml.etree import ElementTree as ET
from llmfactory.llm_provider import get_llm
from xml.etree import ElementTree
import time
from fastapi import HTTPException
from requests.auth import HTTPBasicAuth
from openai import OpenAI
from openai._exceptions import OpenAIError, RateLimitError
from .pubmed_utils import get_data_from_pubmed
PATIENT_STORIES_URL = os.getenv('PATIENT_STORIES_URL')
username = os.getenv('username')
password = os.getenv('password')

super_parent_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if super_parent_path not in sys.path:
    sys.path.insert(0, super_parent_path)
from gql_variables import DrugWarningQueryVariables, SearchDrugQueryVariables
from gql_queries import DrugWarningQuery, SearchDrugQuery


MAX_RESULTS = 10000
NCBI_API_KEY = os.getenv('NCBI_API_KEY')
RATE_LIMIT_RETRY_PERIOD = 300
EMAIL = os.getenv('NCBI_EMAIL')
NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
openai_batch_size = 4
LLM = os.getenv('LLM_MODEL', 'gpt-4o-mini')
openai_batch_size = 4
RATE_LIMIT_OPENAI_FLAG = False

def get_patient_advocacy_group_by_disease(disease_name: str) -> list[Any] | Any:
    """
    Fetches key influencers data from Strapi based on the provided disease name.

    Args:
        disease_name (str): The name of the disease to filter key influencers.

    Returns:
        dict or None: The JSON response from the API if successful, None otherwise.
    """
    # Define the API endpoint, dynamically include the disease name
    STRAPI_BASE_URL = os.getenv("STRAPI_BASE_URL")
    url = f"{STRAPI_BASE_URL}/api/patient-advocacy-groups?filters[disease][$eqi]={disease_name}"

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

def extract_nct_ids(data: Dict[str, Dict[str, Any]]) -> Dict[str, List[Tuple[str, str]]]:
    """
    Extracts all NCT IDs from the 'Source URLs' for each disease.

    Args:
    - data: A dictionary where the keys are pipeline categories and values contain disease data.

    Returns:
    - A dictionary where the keys are diseases and the values are lists of NCT IDs for each disease.
    """
    nct_ids_by_disease: Dict[str, List[Tuple[str, str]]] = {}

    # Iterate through the 'indication_pipeline' data
    for disease, drug_entries in data.get("indication_pipeline", {}).items():
        # Initialize a list to hold all the NCT IDs for the current disease
        nct_ids: List[Tuple[str, str]] = []

        # Iterate through the drug entries for the current disease
        for entry in drug_entries:
            # Check if 'Source URLs' key exists
            if "Source URLs" in entry:
                # Extract the NCT ID from each URL
                for url in entry["Source URLs"]:
                    # Extract the part after the last '/' which is the NCT ID
                    nct_id = url.split('/')[-1]
                    nct_ids.append((nct_id, entry.get("Type", "")))

        # Store the collected NCT IDs for the current disease
        nct_ids_by_disease[disease] = list(set(nct_ids))

    return nct_ids_by_disease

def extract_location_info(location: Dict[str, Union[str, List[Dict[str, str]]]]) -> Optional[Dict[str, Optional[str]]]:
    """
    Extracts the facility (affiliation), location (city, state, country, zip), contact info (phone), and name
    from a location entry in the contactsLocationsModule.

    Args:
        location (Dict[str, Union[str, List[Dict[str, str]]]]): The location dictionary containing facility info,
        status, city, state, country, zip, and contacts.

    Returns:
        Optional[Dict[str, Optional[str]]]: Extracted information with keys 'name', 'affiliation', 'location', and 'phone'.
                                            Returns None if the name is not present.
    """
    facility: Optional[str] = location.get('facility', '')
    city: Optional[str] = location.get('city', '')
    state: Optional[str] = location.get('state', '')
    country: Optional[str] = location.get('country', '')
    zip_code: Optional[str] = location.get('zip', '')

    # Combine the city, state, country, and zip into a location string, filtering out empty values
    location_parts: List[str] = [part for part in [city, state, country, zip_code] if part]
    location_str: str = ', '.join(location_parts)

    # Extracting contact info (phone and name)
    contacts: List[Dict[str, str]] = location.get('contacts', [])
    phone: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    other_contact_phone: Optional[str] = None
    other_contact_email: Optional[str] = None
    other_contact_name: Optional[str] = None

    for contact in contacts:
        if 'role' in contact and contact['role'] == "PRINCIPAL_INVESTIGATOR":
            name = contact['name']

    for contact in contacts:
        if 'role' in contact and contact['role'] == "CONTACT" and 'name' in contact and contact['name'] == name:
            if 'email' in contact:
                email = contact['email']
            if 'phone' in contact:
                phone = contact['phone']
        elif 'role' in contact and contact['role'] == "CONTACT" and 'name' in contact and contact['name'] != name:
            if 'name' in contact:
                other_contact_name = contact['name']
            if 'email' in contact:
                other_contact_email = contact['email']
            if 'phone' in contact:
                other_contact_phone = contact['phone']

    # if email is None and phone is None:
    #     for contact in contacts:
    #         if 'role' in contact and contact['role'] == "CONTACT" and ('name' in contact and contact['name'] != other_contact_name):
    #             if 'email' in contact:
    #                 email = contact['email']
    #             if 'phone' in contact:
    #                 phone = contact['phone']

    # Return only if the name is not None
    if name is not None:
        return {
            'name': name,
            'affiliation': facility,
            'location': location_str,
            'phone': phone,
            'email': email,
            'contact': {
                'name': other_contact_name,
                'phone': other_contact_phone,
                'email': other_contact_email
            }
        }

    return None  # Return None if name is not present

def fetch_clinical_study_data(nct_id: str) -> List[Dict[str, Optional[str]]]:
    """
    Fetches clinical study data using the NCT ID and extracts location information from the response.

    Args:
        nct_id (str): The clinical trial ID (NCT ID).

    Returns:
        List[Dict[str, Optional[str]]]: List of dictionaries containing extracted location info for each facility.
    """
    url: str = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}"
    response = requests.get(url)
    response.raise_for_status()  # Raises HTTPError for bad responses

    data: Dict = response.json()

    # Accessing protocolSection and contactsLocationsModule
    locations_module: List[Dict] = data.get('protocolSection', {}).get('contactsLocationsModule', {}).get('locations',
                                                                                                          [])

    # Extracting location information
    extracted_info: List[Dict[str, Optional[str]]] = []
    for location in locations_module:
        location_info = extract_location_info(location)
        if location_info is not None:
            extracted_info.append(location_info)
    return extracted_info

def fetch_data_for_diseases(disease_dict: Dict[str, List[Tuple[str, str]]]) -> Dict[
    str, Dict[str, List[Dict[str, Optional[str]]]]]:
    """
    Fetches clinical study data for multiple diseases based on a dictionary of diseases and their NCT IDs.

    Args:
        disease_dict (Dict[str, List[str]]): A dictionary where keys are disease names and values are lists of NCT IDs.

    Returns:
        Dict[str, Dict[str, List[Dict[str, Optional[str]]]]]: A nested dictionary containing extracted location info for each disease and NCT ID.
    """
    results: Dict[str, Dict[str, List[Dict[str, Optional[str]]]]] = {}

    for disease, nct_ids_type in disease_dict.items():
        results[disease] = {}  # Initialize a new dictionary for the disease
        for nct_id, type_disease in nct_ids_type:
            try:
                study_data = fetch_clinical_study_data(nct_id)
                if len(study_data) != 0:
                    for entry in study_data:
                        entry["type"] = type_disease
                    results[disease][nct_id] = study_data  # Store results by NCT ID
            except requests.HTTPError as e:
                print(f"Failed to fetch data for NCT ID {nct_id}: {e}")
                results[disease][nct_id] = []  # Assign an empty list if the request fails

    return results

def get_key_influencers_by_disease(disease_name: str) -> list[Any] | Any:
    """
    Fetches key influencers data from Strapi based on the provided disease name.

    Args:
        disease_name (str): The name of the disease to filter key influencers.

    Returns:
        dict or None: The JSON response from the API if successful, None otherwise.
    """
    # Define the API endpoint, dynamically include the disease name
    STRAPI_BASE_URL = os.getenv("STRAPI_BASE_URL")
    url = f"{STRAPI_BASE_URL}/api/key-influencers?filters[disease][$eqi]={disease_name}&fields[0]=name&fields[1]=affiliation&fields[2]=expertise&fields[3]=notable_talks&fields[4]=publications"

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

def filter_indication_records_by_synonyms(
    disease_records: Dict[str, List[Dict]],
    disease_synonyms: Dict[str, List[str]]
) -> Dict[str, List[Dict]]:
    """
    Filters records for each disease based on exact synonyms (case-insensitive).

    Args:
        disease_records (Dict[str, List[Dict]]): A dictionary where keys are disease names, and values are lists of records.
        disease_synonyms (Dict[str, List[str]]): A dictionary where keys are disease names, and values are lists of exact synonyms.

    Returns:
        Dict[str, List[Dict]]: A filtered dictionary with records where the `Disease` field matches the exact synonyms.
    """
    filtered_records: Dict[str, List[Dict]] = {}

    for disease, records in disease_records.items():
        # Get the list of exact synonyms for the disease and normalize to lowercase
        synonyms: List[str] = [syn.lower() for syn in disease_synonyms.get(disease, [])]
        
        filtered_records[disease] = []
        for record in records:
            if not isinstance(record, dict):  # Handle non-dictionary entries
                print(f"Skipping invalid record: {record}")
                continue
            if "Disease" not in record:
                print(f"Skipping record with missing 'Disease' key: {record}")
                continue
            if record["Disease"].lower() in synonyms:
                filtered_records[disease].append(record)

    return filtered_records

def get_pmids_indication_pipeline(disease_name: str) -> List[str]:
    """
    Searches PubMed for randomized controlled trials and clinical trials related to a disease.

    Args:
        disease_name (str): Name of the disease to search for.

    Returns:
        List[str]: A list of PubMed IDs (PMIDs) from the search.
    """
    try:
        query = (
            f'(("randomized controlled trial"[Publication Type]) OR '
            f'("clinical trial"[Publication Type])) AND ({disease_name}[MeSH Terms])'
        )
        
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": MAX_RESULTS,
            "api_key": NCBI_API_KEY  # Maximum number of records to retrieve
        }
        
        # response = requests.get(NCBI_BASE_URL + "esearch.fcgi", params=params)
        # if response.status_code == 429:
        #     # raise Exception("Too Many Requests: You are being rate-limited. Please try again later.")
        #     rate_limited_until = time.time() + RATE_LIMIT_RETRY_PERIOD
        #     raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Try again after {RATE_LIMIT_RETRY_PERIOD} seconds.")

        # time.sleep(0.4)  # Add a delay of 0.4 seconds between requests
        # response.raise_for_status()
        url = NCBI_BASE_URL + "esearch.fcgi"
        response = get_data_from_pubmed(url, params)
        data = response.json()

    except HTTPException as e:
        raise e

    except requests.RequestException as e:
        print(f"An error occurred while fetching the Pubmed Articles for Randomized Controlled Trials: {e}")
        raise e
    return data.get("esearchresult", {}).get("idlist", [])

# def get_nctids_from_pmid_efetch(pmid_list: List[str]) -> Dict[str, List[str]]:
#     """
#     Fetch all associated NCT IDs for a list of PMIDs using the Entrez API (efetch) with POST method.
#     Returns a dictionary with PMID as the key and a list of associated NCT IDs as the value.

#     Args:
#         pmid_list (List[str]): List of PubMed IDs.

#     Returns:
#         Dict[str, List[str]]: A dictionary where each key is a PMID and the value is a list of associated NCT IDs.
#     """
#     base_url = f"{NCBI_BASE_URL}/efetch.fcgi"
    
#     try:
#         # Join the list of PMIDs into a comma-separated string
#         pmid_str = ",".join(pmid_list)
        
#         params = {
#             "db": "pubmed",
#             "id": pmid_str,
#             "retmode": "xml",
#             "api_key": NCBI_API_KEY
#         }
        
#         # Make a POST request to avoid URL length limitations
#         # response = requests.post(base_url, data=params)
#         # if response.status_code == 429:
#         #     # raise Exception("Too Many Requests: You are being rate-limited. Please try again later.")
#         #     rate_limited_until = time.time() + RATE_LIMIT_RETRY_PERIOD
#         #     raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Try again after {RATE_LIMIT_RETRY_PERIOD} seconds.")
        
#         response = get_data_from_pubmed(base_url, params)
#         time.sleep(0.2)
        
#         pmid_nct_dict: Dict[str, List[str]] = {}
        
#         if response.status_code == 200:
#             root = ET.fromstring(response.content)
            
#             # Iterate over each PubmedArticle in the response
#             for pubmed_article in root.findall(".//PubmedArticle"):
#                 # Extract the PMID for this article
#                 pmid = pubmed_article.find(".//PMID").text
                
#                 # Initialize a list to store NCT IDs for this PMID
#                 nct_ids: List[str] = []
                
#                 # Find DataBank entries that may contain NCT IDs
#                 for databank in pubmed_article.findall(".//DataBank"):
#                     databank_name = databank.find("DataBankName")
#                     if databank_name is not None and databank_name.text == "ClinicalTrials.gov":
#                         accession_numbers = databank.findall(".//AccessionNumber")
#                         for accession_number in accession_numbers:
#                             if accession_number is not None and accession_number.text:
#                                 nct_ids.append(accession_number.text)
                
#                 # If there are associated NCT IDs, add them to the dictionary
#                 if nct_ids:
#                     pmid_nct_dict[pmid] = nct_ids
    
#     except HTTPException as e:
#         raise e
    
#     except Exception as e:
#         print(f"An error occurred while fetching NCT IDS for given PMID '{pmid_str}': {e}")
#         raise e
#     return pmid_nct_dict

def get_nctids_from_pmid_efetch(pmid_list: List[str]) -> Dict[str, List[str]]:
    """
    Fetch all associated NCT IDs for a list of PMIDs using the Entrez API (efetch) with POST method.
    Returns a dictionary with PMID as the key and a list of associated NCT IDs as the value.

    Args:
        pmid_list (List[str]): List of PubMed IDs.

    Returns:
        Dict[str, List[str]]: A dictionary where each key is a PMID and the value is a list of associated NCT IDs.
    """
    base_url = f"{NCBI_BASE_URL}/efetch.fcgi"
    
    # If the list is very large, process in chunks to avoid memory issues
    max_chunk_size = 200  # Adjust based on your needs
    pmid_nct_dict: Dict[str, List[str]] = {}
    
    try:
        # Process PMIDs in chunks if the list is large
        for i in range(0, len(pmid_list), max_chunk_size):
            chunk = pmid_list[i:i + max_chunk_size]
            pmid_str = ",".join(chunk)
            
            # Prepare data for POST request body
            post_data = {
                "db": "pubmed",
                "id": pmid_str,
                "retmode": "xml"
            }
            
            # Add API key if available
            if NCBI_API_KEY:
                post_data["api_key"] = NCBI_API_KEY
            
            # Make POST request with data in the request body
            response = requests.post(
                base_url, 
                data=post_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                rate_limited_until = time.time() + RATE_LIMIT_RETRY_PERIOD
                raise HTTPException(
                    status_code=429, 
                    detail=f"Rate limit exceeded. Try again after {RATE_LIMIT_RETRY_PERIOD} seconds."
                )
            
            # Alternative: use your existing rate-limited function
            # response = get_data_from_pubmed(base_url, post_data, method='POST')
            
            time.sleep(0.2)  # Rate limiting
            
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                
                # Iterate over each PubmedArticle in the response
                for pubmed_article in root.findall(".//PubmedArticle"):
                    # Extract the PMID for this article
                    pmid_element = pubmed_article.find(".//PMID")
                    if pmid_element is not None:
                        pmid = pmid_element.text
                        
                        # Initialize a list to store NCT IDs for this PMID
                        nct_ids: List[str] = []
                        
                        # Find DataBank entries that may contain NCT IDs
                        for databank in pubmed_article.findall(".//DataBank"):
                            databank_name = databank.find("DataBankName")
                            if databank_name is not None and databank_name.text == "ClinicalTrials.gov":
                                accession_numbers = databank.findall(".//AccessionNumber")
                                for accession_number in accession_numbers:
                                    if accession_number is not None and accession_number.text:
                                        nct_ids.append(accession_number.text)
                        
                        # Add to dictionary (even if empty list, to track processed PMIDs)
                        pmid_nct_dict[pmid] = nct_ids
            else:
                print(f"Error fetching chunk {i//max_chunk_size + 1}: HTTP {response.status_code}")
                print(f"Response: {response.text}")
    
    except HTTPException as e:
        raise e
    
    except Exception as e:
        pmid_str = ",".join(pmid_list[:5]) + "..." if len(pmid_list) > 5 else ",".join(pmid_list)
        print(f"An error occurred while fetching NCT IDs for PMIDs '{pmid_str}': {e}")
        raise e
    
    return pmid_nct_dict

def fetch_pubmed_article_data(pmids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetches the Article content of given pmid list
    """
    try:
        params = {
                  "db": "pubmed",
                  "id": ",".join(pmids),
                  "retmode": "xml",  # Use XML to retrieve detailed information
                  "api_key": NCBI_API_KEY
              }
        
        # response = requests.get(NCBI_BASE_URL + "efetch.fcgi", params=params)
        # if response.status_code == 429:
        #     # raise Exception("Too Many Requests: You are being rate-limited. Please try again later.")
        #     rate_limited_until = time.time() + RATE_LIMIT_RETRY_PERIOD
        #     raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Try again after {RATE_LIMIT_RETRY_PERIOD} seconds.")

        # response.raise_for_status()
        url = NCBI_BASE_URL + "esearch.fcgi"
        response = get_data_from_pubmed(url, params)

    except HTTPException as e:
        raise e

    except Exception as e:
        raise e

    return response.text

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
        # Send the request to the API
        # response = requests.get(NCBI_BASE_URL + "esearch.fcgi", params=params)
        # time.sleep(1)
        # if response.status_code == 429:
        #     # raise Exception("Too Many Requests: You are being rate-limited. Please try again later.")
        #     rate_limited_until = time.time() + RATE_LIMIT_RETRY_PERIOD
        #     raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Try again after {RATE_LIMIT_RETRY_PERIOD} seconds.")

        # response.raise_for_status()
        url = NCBI_BASE_URL + "esearch.fcgi"
        response = get_data_from_pubmed(url, params)
        
        # Parse the XML response
        root = ET.fromstring(response.content)

        # Find the <TermSet> with <Field> == 'MeSH Terms'
        for term_set in root.findall(".//TermSet"):
            field = term_set.find("Field")
            term = term_set.find("Term")
            if field is not None and term is not None and field.text == "MeSH Terms":
                # Clean the MeSH term (remove quotes and brackets)
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

def filter_pubmed_articles(pubmed_response: str, disease_mesh_term: str):
    """
    Filters Pubmed Articles if DiseaseName is MeSH Major Topic
    OR
    if DiseaseName is not a MeSH Major Topic then corresponding Qualifier should be MeSH Major Topic
    And then extract the NCTIDs of those articles
    """
    root = ET.fromstring(pubmed_response)
    articles = root.findall(".//PubmedArticle")
    filtered_articles = []
    qualifier_count = 0
    descriptor_count = 0
    for article in articles:
        article_info = {}
        if article is None:
            continue  # Skip if no article data is found
        article_info['pmid'] = article.find(".//PMID").text if article.find(".//PMID") is not None else None

        mesh_details = []
        mesh_heading_list = article.find(".//MeshHeadingList")
        # if mesh_heading_list is None or not mesh_heading_list:
        #     return qualifiers  # Return an empty list if mesh_heading_list is None

        if mesh_heading_list:
            # Iterate through all MeshHeading elements
            for mesh_heading in mesh_heading_list.findall(".//MeshHeading"):
                mesh_info = {}

                # Get the DescriptorName
                descriptor_name = mesh_heading.find("DescriptorName")
                if descriptor_name is not None and descriptor_name.text.strip().lower() == disease_mesh_term.strip().lower():
                    if descriptor_name.attrib.get("MajorTopicYN") == "Y":
                      mesh_info["DescriptorName"] = descriptor_name.text.strip()
                      descriptor_count += 1
                    # Check if the descriptor name matches the disease name
                    else:
                        qualifier_names = mesh_heading.findall("QualifierName")
                        if qualifier_names:
                            qualifiers = []
                            for qualifier_name in qualifier_names:
                                if qualifier_name.attrib.get("MajorTopicYN") == "Y":
                                    qualifiers.append(qualifier_name.text.strip())

                            if qualifiers:
                                mesh_info["DescriptorName"] = descriptor_name.text.strip()
                                mesh_info["Qualifiers"] = qualifiers
                                qualifier_count += 1
                    if mesh_info:
                        mesh_details.append(mesh_info)
        if len(mesh_details):
            article_info['mesh_details'] = mesh_details
            nct_ids = []
            for databank in article.findall(".//DataBank"):
                databank_name = databank.find("DataBankName")
                if databank_name is not None and databank_name.text == "ClinicalTrials.gov":
                    accession_numbers = databank.findall(".//AccessionNumber")
                    for accession_number in accession_numbers:
                        if accession_number is not None and accession_number.text:
                            nct_ids.append(accession_number.text)

            # If there are associated NCT IDs, add them to the dictionary
            if nct_ids:
                article_info['nctids'] = nct_ids

            filtered_articles.append(article_info)
    return filtered_articles, descriptor_count, qualifier_count

def filter_pmids_in_batches(pmids, disease) -> List[Dict[str, Any]]:
    """
    Fetch the pubmed articles in batches from NCBI and then fetch the NCTIDs 
    of filtered articles which  if DiseaseName is MeSH Major Topic
    OR
    if DiseaseName is not a MeSH Major Topic then corresponding Qualifier should be MeSH Major Topic
    """
    filtered_pmids = []
    total_descriptor_count = 0
    total_qualifier_count = 0
    for i in range(0, len(pmids), 200):
        batch = pmids[i:i + 200]
        pubmed_article_data = fetch_pubmed_article_data(batch)
        time.sleep(0.1)
        filtered_articles, descriptor_count, qualifier_count = filter_pubmed_articles(pubmed_article_data, disease)
        filtered_pmids.extend(filtered_articles)
        total_descriptor_count += descriptor_count
        total_qualifier_count += qualifier_count
    return filtered_pmids

def get_pmids_for_nct_ids(disease_data: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
    """
    Extracts disease names from each record, retrieves PMIDs using `get_pmids_indication_pipeline` function,
    and then calls `get_nctids_from_pmid_efetch` to retrieve and filter unique PMIDs associated with NCT IDs.
    Adds the list of matching PMIDs to each record only if the record has a "Status" of "Completed".
    If "Status" is missing, or if any other keys are missing, default values are used.

    Args:
        disease_data (Dict[str, List[Dict]]): A dictionary with disease names as keys and
                                               a list of records as values. Each record contains NCT IDs.
    Returns:
        Dict[str, List[Dict]]: A dictionary where each disease name maps to a list of records, each of which
                                includes the original information along with a list of matching unique PMIDs (or an empty list).
    """
    disease_nctid_pmids = {}

    # Iterate through each disease and its associated records
    for disease, records in disease_data.items():
        try:
            # Initialize a list to store records with updated PMIDs for each disease
            updated_records = []
            # Get the list of PMIDs related to the disease using get_pmids_indication_pipeline
            pmids = get_pmids_indication_pipeline(disease)

            # filter the pubmed articles which has descriptor as mesh term of the disease
            disease_mesh_term = get_mesh_term_for_disease(disease)
            filtered_records = filter_pmids_in_batches(pmids, disease_mesh_term)

            # get pmids from filtered_records
            filtered_pmids = [record["pmid"] for record in filtered_records]

            # print(f"Filtered PMIDs for {disease}: {len(filtered_pmids)}")
            # pmid_nct_dict = get_nctids_from_pmid_efetch(filtered_pmids)

            #get nctids from filtered_records
            pmid_nct_dict = {record["pmid"]:record["nctids"] for record in filtered_records if "nctids" in record}
            print(f"NCT IDs for {disease}:  {len(pmid_nct_dict)}")

            # For each record, extract the disease name and call get_pmids_indication_pipeline with the disease name
            for record in records:
                disease_name = record.get("Disease", "")  # Default to empty string if "Disease" is missing

                # Check if the status is "Completed", if not, add an empty list for Matching PMIDs
                # if record.get("Status", "") == "Completed":  # Default to empty string if "Status" is missing

                # Extract the NCT IDs from the record's 'Source URLs' (default to empty list if key is missing)
                nct_ids = [url.split("/")[-1] for url in record.get("Source URLs", [])]

                # Initialize a set to collect unique PMIDs associated with the NCT IDs
                matching_pmids = set()

                # For each NCT ID, collect the corresponding PMIDs that have it
                for nct_id in nct_ids:
                    for pmid, associated_nct_ids in pmid_nct_dict.items():
                        if nct_id in associated_nct_ids:
                            # Add the PMID to the set if it matches
                            matching_pmids.add(pmid)

                # Add the matching PMIDs as a new key in the record
                record["PMIDs"] = list(matching_pmids)
                # else:
                #     # If the status is not "Completed" or missing, add an empty list for PMIDs
                #     record["PMIDs"] = []

                # Add the updated record to the list of updated records for the disease
                updated_records.append(record)

            # Store the updated records for the current disease
            disease_nctid_pmids[disease] = updated_records

        except HTTPException as e:
            raise e
        
        except Exception as e:
            raise e

    return disease_nctid_pmids

def get_pmids_for_nct_ids_target_pipeline(
    disease_data: List[Dict[str, Any]],
    disease_pmid_nct_mapping: Dict[str, Dict[str, List[str]]]
) -> List[Dict[str, Any]]:
    """
    Processes a list of records, retrieves PMIDs for each disease using a precomputed mapping,
    and adds matching PMIDs for completed studies to each record.

    Args:
        disease_data (List[Dict[str, Any]]): A list of records, each containing information about drugs,
                                              diseases, and associated clinical trials.
        disease_pmid_nct_mapping (Dict[str, Dict[str, List[str]]]): A dictionary mapping diseases to a 
                                                                     dictionary of PMIDs and their associated NCT IDs.

    Returns:
        List[Dict[str, Any]]: The updated list of records with added PMIDs for completed studies.
    """
    # Iterate over each record and update it with matching PMIDs
    for record in disease_data:
        # Extract disease name and ensure it's in the mapping
        disease_name = record.get("Disease", "").lower()
        pmid_nct_dict = disease_pmid_nct_mapping.get(disease_name, {})
        

        # Check if the record has a "Completed" status
        # if record.get("Status", "") == "Completed":
        # Extract NCT IDs from the record's "Source URLs"
        nct_ids = [url.split("/")[-1] for url in record.get("Source URLs", [])]

        # Collect unique PMIDs associated with these NCT IDs
                        # Initialize a set to collect unique PMIDs associated with the NCT IDs
        matching_pmids = set()

        # For each NCT ID, collect the corresponding PMIDs that have it
        for nct_id in nct_ids:
            for pmid, associated_nct_ids in pmid_nct_dict.items():
                if nct_id in associated_nct_ids:
                    # Add the PMID to the set if it matches
                    matching_pmids.add(pmid)

        # Add the matching PMIDs as a new key in the record
        record["PMIDs"] = list(matching_pmids)
        # else:
        #     # For non-completed statuses, add an empty list for PMIDs
        #     record["PMIDs"] = []

    return disease_data

def get_conclusion(pubmed_id: str) -> Optional[str]:
    """
    Fetches the conclusion or abstract text from the PubMed abstract for a given PubMed ID.

    Args:
    - pubmed_id (str): The PubMed ID of the article.

    Returns:
    - Optional[str]: The conclusion or abstract text of the article, or None if not found.
    """
    # Define the URL for PubMed E-utilities
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pubmed_id}&retmode=xml&api_key={NCBI_API_KEY}"
    
    try:
        # Send the GET request to fetch the XML data
        response = requests.get(url)
        
        # Check if the response status code is OK (200)
        if response.status_code == 200:
            # Parse the XML content
            tree = ElementTree.fromstring(response.content)
            
            # Search for the 'CONCLUSIONS' AbstractText
            for abstract_text in tree.findall(".//AbstractText"):
                if abstract_text.attrib.get("Label") == "CONCLUSIONS" or abstract_text.attrib.get("Label") == "CONCLUSION":
                    return abstract_text.text.strip()
                elif abstract_text.attrib.get("Label") == "INTERPRETATION":
                    return abstract_text.text.strip()
            
            # If no 'CONCLUSIONS', return the full abstract text
            abstract_texts = tree.findall(".//AbstractText")
            if abstract_texts: 
                text = " ".join("".join(abstract_text.itertext()) for abstract_text in abstract_texts)
                return text
            
        if response.status_code == 429:
            # raise Exception("Too Many Requests: You are being rate-limited. Please try again later.")
            rate_limited_until = time.time() + RATE_LIMIT_RETRY_PERIOD
            raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Try again after {RATE_LIMIT_RETRY_PERIOD} seconds.")

    except HTTPException as e:
        raise e
    
    except Exception as e:
        print(f"An error occurred while fetching MeSH terms for PMID '{pubmed_id}': {e}")
        raise e
    # Return None if no abstract or conclusion is found
    return ""

def get_combined_conclusions(pubmed_ids: List[str]) -> str:
    """
    Fetches conclusions or abstract texts for a list of PubMed IDs and combines them into a single string.

    Args:
    - pubmed_ids (List[str]): A list of PubMed IDs.

    Returns:
    - str: A single string containing the content of each conclusion/abstract, separated by paragraphs.
    """
    combined_content = []
    for pubmed_id in pubmed_ids:
        try:
            content = get_conclusion(pubmed_id)
            if content:
                combined_content.append(content)
            else:
                print(f"PubMed ID {pubmed_id}:\nNo conclusion or abstract found.")
        
        except HTTPException as e:
            raise e
    
        except Exception as e:
            print(f"PubMed ID {pubmed_id}:\nError fetching content: {e}")

    # Join all results with a paragraph break
    return "\n\n".join(combined_content)

def openai_health_check():
    "Checks the access for OPENAI"
    global RATE_LIMIT_OPENAI_FLAG
    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1
        )

        print("OpenAI API is healthy")
        if RATE_LIMIT_OPENAI_FLAG == True:
            RATE_LIMIT_OPENAI_FLAG = False
        return True
    
    except Exception as e:
        print("OpenAI API health check failed:", e)
        RATE_LIMIT_OPENAI_FLAG = True
        return False

def get_outcome_status_openai_batches(pubmed_ids: List[str], disease_name: str) -> str:
    outcome_status = []
    for i in range(0, len(pubmed_ids), openai_batch_size):
        batch = pubmed_ids[i:i + openai_batch_size]
        outcome_status.append(get_outcome_status_openai(batch, disease_name))

    outcome_status = list(set(outcome_status))
    if len(outcome_status) > 1:
        return "Indeterminate"
    return outcome_status[0]

def get_outcome_status_openai(pubmed_ids: List[str], disease_name: str) -> str:
    """
    Return the outcome status for a disease name and pubmed ids.

    Args:
    - pubmed_ids (List[str]): A list of PubMed IDs.
    - disease_name (str): Name of the disease.

    Returns:
    - str: A single string containing the outcome status (Success/Failed/Indeterminate).
    """
    global RATE_LIMIT_OPENAI_FLAG
    try:
        if not pubmed_ids or not disease_name:
            return "Not Known"


        # Placeholder for fetching conclusions
        conclusion: str = get_combined_conclusions(pubmed_ids=pubmed_ids)
        pmids_string: str = ",".join(pubmed_ids)
    
    except HTTPException as e:
        raise e
    
    except Exception as e:
        raise e
    
    if conclusion:
        # Prepare a prompt for classification
        prompt = f"""
        The conclusion of the PubMed articles with Pubmed ID {pmids_string} is as follows:
        {conclusion}

        The article is associated with the disease: {disease_name}.

        Based on this conclusion, classify it into one of the following categories:

        1. **Success**: The study indicates clear positive outcomes or advancements related to the disease's treatment, management, or understanding.
        2. **Failed**: The study reports negative results, lack of significant outcomes, or setbacks in addressing the disease.
        3. **Indeterminate**: The study provides ambiguous or inconclusive results, or the conclusion lacks sufficient evidence to determine success or failure.

        Provide the classification in the following JSON format:
        {{ "classification": "<Success/Failed/Indeterminate>" }}
        """

        try:

            retries = 3
            delay = 2  # starting delay in seconds
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            for attempt in range(retries):
                
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
                
                classification = json.loads(response_content).get("classification", "Indeterminate")

                if "Success" in classification:
                    return "Success"
                elif "Failed" in classification:
                    return "Failed"
                elif "Indeterminate" in classification:
                    return "Indeterminate"
                else:
                    return "Not Known"

        except RateLimitError as e:
            if hasattr(e, "status_code") and e.status_code == 429:
                try:
                    # Try to parse the structured error message
                    error_data = e.response.json()
                    error_info = error_data.get("error", {}).get("code", "")
                    print(f"Error data: {error_info}")
                    error_code = error_data.get("error", {}).get("code")
                
                except Exception as parse_error:
                    print(f"Error while parsing rate OpenAI limit response: {parse_error}")
                    return "Not Known"

            if error_code == "insufficient_quota":
                print("🚫 You have exceeded your OpenAI quota. Please check your plan and billing.")
                RATE_LIMIT_OPENAI_FLAG = True
                return "Not Known"
            
            print(f"⚠️ Rate limit hit. Retrying in {delay} seconds... ({attempt+1}/{retries})")
            time.sleep(delay)
            delay *= RATE_LIMIT_RETRY_PERIOD  # exponential backoff

        except OpenAIError as e:
            print(f"OpenAI API error: {e}")
            return "Not Known"
        except Exception as e:
            print(f"Unexpected error: {e}")
            return "Not Known"

        print("Exceeded maximum retries due to rate limits.")
        return "Not Known"

    else:
        print(f"Error: No conclusion found for the provided PubMed IDS: {pmids_string}")
        return "Not Known"
    
    
def get_outcome_status(pubmed_ids: List[str],disease_name: str) -> str:
    """
    Return the outcome status for a disease name and pubmed ids.

    Args:
    - pubmed_ids (List[str]): A list of PubMed IDs.
    - disease_name (str): Name of the disease.

    Returns:
    - str: A single string containing the outocome status (Success/Failed/Indeterminate).
    """
    try:
        if not pubmed_ids or not disease_name:
            return "Not Known"
        
        conclusion: str = get_combined_conclusions(pubmed_ids=pubmed_ids)
        config = {
            "provider": os.getenv("provider"),
            "model": os.getenv("model"),
            "endpoint": os.getenv("endpoint"),
            "username": os.getenv("username"),
            "password": os.getenv("password"),
            "additional_args": {}  
        }

        with open("config.json", "w") as file:
            json.dump(config, file)

        chat_llm = get_llm(config_path="config.json", interface_type="chat")
        # print("Llama chat initialized")
        pmids_string: str=",".join(pubmed_ids)
        if conclusion:
            # Prepare a prompt for classification
            prompt = f"""
            The conclusion of the PubMed articles with Pubmed ID {pmids_string} is as follows:
            {conclusion}
            
            The article is associated with the disease: {disease_name}.
            
            Based on this conclusion, classify it into one of the following categories:
            
            1. **Success**: The study indicates clear positive outcomes or advancements related to the disease's treatment, management, or understanding.
            2. **Failed**: The study reports negative results, lack of significant outcomes, or setbacks in addressing the disease.
            3. **Indeterminate**: The study provides ambiguous or inconclusive results, or the conclusion lacks sufficient evidence to determine success or failure.
            
            Provide the classification in the following JSON format:
            {{ "classification": "<Success/Failed/Indeterminate>" }}
            """
            
            try:
                # Get classification response from the LLM
                response = chat_llm.invoke(prompt)
            except Exception as e:
                    print(f"An error occurred while invoking the llama with prompt: {prompt}")
                    print(f"An error occurred: {e}")
                    return "Not Known"
            
            if response:
                try:
                    # Parse the JSON from the response content
                    classification = json.loads(response.content).get("classification", "Indeterminate")
                    # print(f"Classification: {classification}")
                        # Check for substrings and return the corresponding status
                    if "Success" in classification:
                        return "Success"
                    elif "Failed" in classification:
                        return "Failed"
                    elif "Indeterminate" in classification:
                        return "Indeterminate"
                    else:
                        return "Not Known"
                except Exception as e:
                    print(f"An error occurred: {e}")
                    return "Not Known"
            else:
                print("Error: No content found in response.")
                return "Not Known"
        else:
            print(f"Error: No conclusion found for the provided PubMed IDS: {pmids_string}")
            return "Not Known"
    
    except HTTPException as e:
        raise e
    
    except Exception as e:
        raise e
    

def add_outcome_status(records: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Adds an OutcomeStatus field to each record in the dataset.
    
    - If Status is not 'Completed', OutcomeStatus is set to an empty string.
    - If Status is 'Completed', OutcomeStatus is determined using the get_outcome_status function.

    :param records: Dictionary containing a list of records for each disease.
    :return: Updated records with the OutcomeStatus field added.
    """
    try:
        # Check the OPENAI access
        openai_health_check()
        # Iterate over all diseases and their respective records
        for disease, entries in records.items():
            for entry in entries:
                if entry["Status"] == "Terminated" or entry["Status"] == "Withdrawn" or entry["Status"]=="Suspended":
                    entry["OutcomeStatus"] = "Failed"
                else:
                    # Call the get_outcome_status function to populate OutcomeStatus
                    # entry["OutcomeStatus"] = get_outcome_status_openai(entry.get("PMIDs", []), disease)
                    # Check OpenAI access
                    if RATE_LIMIT_OPENAI_FLAG == True:
                        entry["OutcomeStatus"] = "Not Known"
                    else:
                        pubmed_ids = entry.get("PMIDs", [])
                        if len(pubmed_ids) > 4:
                            entry["OutcomeStatus"] = get_outcome_status_openai_batches(pubmed_ids, entry.get("Disease", "").lower())
                        else:
                            entry["OutcomeStatus"] = get_outcome_status_openai(pubmed_ids, entry.get("Disease", "").lower())
                        time.sleep(1)

    except HTTPException as e:
        raise e
    
    except Exception as e:
        raise e
    
    # records['Validity'] = "invalid" if RATE_LIMIT_OPENAI_FLAG == True else "valid"
    openai_validity = "invalid" if RATE_LIMIT_OPENAI_FLAG == True else "valid"

    return records, openai_validity

def add_outcome_status_target_pipeline(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Adds an OutcomeStatus field to each record in the dataset.
    
    - If Status is not 'Completed', OutcomeStatus is set to an empty string.
    - If Status is 'Completed', OutcomeStatus is determined using the get_outcome_status function.

    :param records: List of records, where each record is a dictionary.
    :return: Updated records with the OutcomeStatus field added.
    """
    try:
        # Check the OPENAI access
        openai_health_check()
        # Iterate over all records
        for entry in records:
            if entry["Status"] == "Terminated" or entry["Status"] == "Withdrawn" or entry["Status"]=="Suspended":
                entry["OutcomeStatus"] = "Failed"
            else:
                if RATE_LIMIT_OPENAI_FLAG == True:
                    entry["OutcomeStatus"] = "Not Known"
                else:
                    # Call the get_outcome_status function to populate OutcomeStatus
                    pubmed_ids = entry.get("PMIDs", [])
                    if len(pubmed_ids) > 4:
                        entry["OutcomeStatus"] = get_outcome_status_openai_batches(pubmed_ids, entry.get("Disease", "").lower())
                    else:
                        entry["OutcomeStatus"] = get_outcome_status_openai(pubmed_ids, entry.get("Disease", "").lower())
                    time.sleep(1)

    except HTTPException as e:
        print("exception raised here")
        raise e
    
    except Exception as e:
        raise e
    
    return records

def get_why_stopped(nct_id: str) -> str:
    api_url = f"https://clinicaltrials.gov/api/int/studies/{nct_id}?history=true"

    try:
        # Send a GET request to the API
        response = requests.get(api_url)
        
        # Raise an error if the response code is not 200
        response.raise_for_status()
        
        # Parse the JSON response
        study_data = response.json()
        
        # Extract and return the `whyStopped` field
        return study_data.get("study", {}).get("protocolSection", {}).get("statusModule", {}).get("whyStopped", "")
    
    except requests.RequestException as e:
        print(f"Error fetching data for NCT ID {nct_id}: {e}")
        return ""

def get_indication_pipeline_strapi(disease_name: str) -> List[Dict[str, Any]]:
    """
    Fetches and filters key influencers data from Strapi for the given disease name.

    Args:
        disease_name (str): The name of the disease to filter key influencers.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing filtered data fields.
    """
    # Define the API endpoint, dynamically include the disease name as a filter
    STRAPI_BASE_URL = os.getenv("STRAPI_BASE_URL")
    base_url = f"{STRAPI_BASE_URL}/api/pipeline-by-indications"
    url = f"{base_url}?filters[disease][$eqi]={disease_name}&pagination[page]=1&pagination[pageSize]=500"

    # Retrieve the API token
    api_token = os.getenv('STRAPI_API_TOKEN') 

    # Ensure the token exists
    if not api_token:
        print("API token not found. Set the 'STRAPI_API_TOKEN'.")
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
                phase = item.get("trialRecord", {}).get("phase")
                trial_status = item.get("trialRecord", {}).get("trialStatus")
                source_url = item.get("trialRecord", {}).get("url")
                trial_id= item.get("trialRecord", {}).get("trialID")
                
                                # Ensure source_url is always a list
                if isinstance(source_url, str):
                    source_url = [source_url]
                elif not isinstance(source_url, list):
                    source_url = []

                # Ensure trial_id is always a list
                if isinstance(trial_id, str):
                    trial_id = [trial_id]
                elif not isinstance(trial_id, list):
                    trial_id = []
                
                approval_status = item.get("trialRecord", {}).get("approvalStatus")
                filtered_data.append({
                    "Disease": item.get("disease", "").lower(),
                    "Drug": item.get("drug", ""),
                    "Type": item.get("type", ""),
                    "Mechanism of Action": item.get("MoA", ""),
                    "Phase": f"Phase {phase}" if phase else "N/A",
                    "Status": trial_status,
                    "Target": item.get("target", ""),
                    "Source URLs": source_url,
                    "Sponsor": item.get("sponsor", ""),
                    "ApprovalStatus": approval_status,
                    "WhyStopped":get_why_stopped(nct_id=trial_id[0]) if trial_id else ""
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


# def get_target_pipeline_strapi(diseases: List[str], target: str) -> List[Dict[str, Any]]:
#     """
#     Fetches and filters key influencers data from Strapi for the given list of disease and target combinations.

#     Args:
#         diseases (List[str]): A list of disease names to filter key influencers.
#         targets (str) : A target names to filter key influencers.

#     Returns:
#         List[Dict[str, Any]]: A list of dictionaries containing filtered data fields.
#     """
#     # Define the API endpoint
#     STRAPI_BASE_URL = os.getenv("STRAPI_BASE_URL")
#     base_url = f"{STRAPI_BASE_URL}/api/pipeline-by-indications"

#     # Retrieve the API token
#     api_token = os.getenv('STRAPI_API_TOKEN')
#     # Ensure the token exists
#     if not api_token:
#         print("API token not found. Set the 'STRAPI_API_TOKEN'.")
#         return []

#     # Define the headers with the authorization token
#     headers = {
#         "Authorization": f"Bearer {api_token}",
#         "Content-Type": "application/json"
#     }

#     filtered_data = []

#     try:
#         # Iterate over all disease and target combinations
#         for disease in diseases:
#               # Define the API query parameters
#               url = f"{base_url}?filters[disease][$eqi]={disease}&filters[target][$eqi]={target}&pagination[page]=1&pagination[pageSize]=500"

#               # Send a GET request to retrieve data
#               response = requests.get(url, headers=headers)

#               # Check if the request was successful
#               if response.status_code == 200:
#                   # Parse the JSON response
#                   data = response.json()

#                   # Extract only the relevant fields
#                   for item in data.get("data", []):
#                       phase = item.get("trialRecord", {}).get("phase")
#                       trial_status = item.get("trialRecord", {}).get("trialStatus")
#                       source_url = item.get("trialRecord", {}).get("url")
#                       trial_id = item.get("trialRecord", {}).get("trialID")

#                       # Ensure source_url is always a list
#                       if isinstance(source_url, str):
#                           source_url = [source_url]
#                       elif not isinstance(source_url, list):
#                           source_url = []

#                       # Ensure trial_id is always a list
#                       if isinstance(trial_id, str):
#                           trial_id = [trial_id]
#                       elif not isinstance(trial_id, list):
#                           trial_id = []

#                       approval_status = item.get("trialRecord", {}).get("approvalStatus")
#                       filtered_data.append({
#                           "Disease": item.get("disease", "").lower(),
#                           "Drug": item.get("drug", ""),
#                           "Type": item.get("type", ""),
#                           "Mechanism of Action": item.get("MoA", ""),
#                           "Phase": f"Phase {phase}" if phase else "N/A",
#                           "Status": trial_status,
#                           "Target": item.get("target", ""),
#                           "Source URLs": source_url,
#                           "Sponsor": item.get("sponsor", ""),
#                           "ApprovalStatus": approval_status,
#                           "WhyStopped": get_why_stopped(nct_id=trial_id[0]) if trial_id else ""
#                       })
#               else:
#                   # If there's an error, log it and continue with other combinations
#                   print(f"Failed to fetch data for Disease: {disease}, Target: {target}. Status code: {response.status_code}")
#                 #   print(response.text)

#         return filtered_data
#     except Exception as e:
#         print(f"An error occurred: {e}")
#         return []


def get_disease_pmid_nct_mapping(diseases: List[str]) -> Dict[str, Dict[int, List[str]]]:
    """
    Generate a dictionary mapping diseases to their PMIDs and associated NCT IDs.

    Args:
        diseases (List[str]): A list of diseases to process.

    Returns:
        Dict[str, Dict[int, List[str]]]: A dictionary where the key is the disease name,
                                         and the value is another dictionary that maps PMIDs to lists of NCT IDs.
    """
    # Initialize the result dictionary
    disease_pmid_nct_mapping: Dict[str, Dict[int, List[str]]] = {}

    try:
        for disease in diseases:
            # Get the list of PMIDs related to the disease using the pipeline function
            pmids: List[int] = get_pmids_indication_pipeline(disease)

            # Call the function to retrieve the mapping of PMIDs to NCT IDs
            pmid_nct_dict: Dict[str, List[str]] = get_nctids_from_pmid_efetch(pmids)

            # Add the disease and its PMIDs-NCT mapping to the result dictionary
            disease_pmid_nct_mapping[disease] = pmid_nct_dict
    
    except HTTPException as e:
        raise e
    
    return disease_pmid_nct_mapping



def remove_duplicates(pipeline):
    """
    Removes duplicate entries in the pipeline based on specific unique fields.
    The comparison is case-insensitive for strings and lists of strings.
    Keeps the latest entry if duplicates are found.

    Parameters:
        pipeline (list): List of dictionaries representing the pipeline.

    Returns:
        list: List of dictionaries with duplicates removed.
    """
    # Define the fields used to identify unique entries
    unique_fields = ["Drug", "Disease", "Source URLs"]

    seen = {}
    if len(pipeline)>0:
        for entry in pipeline:
            # Create a case-insensitive unique key for each entry
            unique_key = tuple(
                (entry.get(field, "").lower() if isinstance(entry.get(field, ""), str) else
                tuple(sorted([url.lower() for url in entry.get(field, [])])) if isinstance(entry.get(field, []), list) else "")
                for field in unique_fields
            )

            # Keep only the latest occurrence
            seen[unique_key] = entry
    # Return the filtered list
    return list(seen.values())


def remove_duplicates_from_indication_pipeline(indication_pipeline):
    """
    Removes duplicates from the indication pipeline where each disease has an array of entries.
    Calls the `remove_duplicates` function for each disease's array.

    Parameters:
        indication_pipeline (dict): Dictionary with diseases as keys and lists of entries as values.

    Returns:
        dict: Dictionary with duplicates removed from each disease's array.
    """
    
    return {
        disease: remove_duplicates(entries) if disease != "Validity" else entries
        for disease, entries in indication_pipeline.items()
    }
    

API_URL = "https://api.platform.opentargets.org/api/v4/graphql"

def parse_drug_warning_response(response: Dict) -> Dict:
    """
    Parses the GraphQL API response to extract warning-related information.
    """
    try:
        drug_data = response.get("data", {}).get("drug", {})
        if not drug_data:
            raise ValueError("No drug data found in response.")
        return {
            "blackBoxWarning": drug_data.get("blackBoxWarning"),
            "drugWarnings": drug_data.get("drugWarnings", [])
        }
    except Exception as e:
        return {}


def fetch_drug_warning_data(chembl_id: str) -> Dict:
    """
    Fetches drug warning data from Open Targets API.
    """
    variables = DrugWarningQueryVariables.copy()
    variables["chemblId"] = chembl_id
    
    try:
        response = requests.post(API_URL, json={"query": DrugWarningQuery, "variables": variables}, timeout=20)
        response.raise_for_status()
        raw_data = response.json()
        warning_data = parse_drug_warning_response(raw_data)
        return warning_data
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch warning data: {str(e)}")

def resolve_chembl_id_from_name(drug_name: str) -> Optional[str]:
    """
    Resolves a drug name to its ChEMBL ID using Open Targets search API.
    """
    variables = SearchDrugQueryVariables.copy()
    variables["term"] = drug_name
    payload = {"query": SearchDrugQuery, "variables": variables}
    
    try:
        response = requests.post(API_URL, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        hits = data.get("data", {}).get("search", {}).get("hits", [])
        
        if not hits:
            return None
        
        for hit in hits:
            hit_name = hit["name"]
            if hit_name.lower() == drug_name.lower():
                chembl_id = hit["id"]
                return chembl_id
        
        return None
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve ChEMBL ID: {str(e)}")

def get_target_pipeline_strapi_all(diseases: List[str], target: str) -> List[Dict[str, Any]]:
    """
    Fetches and filters pipeline data from Strapi for the given list of diseases and target.
    If `diseases` is empty, returns all pipeline entries for the target.
    """
    STRAPI_BASE_URL = os.getenv("STRAPI_BASE_URL")
    api_token = os.getenv("STRAPI_API_TOKEN")
    if not api_token:
        print("API token not found. Set the 'STRAPI_API_TOKEN'.")
        return []

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    base_url = f"{STRAPI_BASE_URL}/api/pipeline-by-indications"
    filtered_data: List[Dict[str, Any]] = []

    def fetch_for_params(params: Dict[str, Any]):
        """Helper to fetch a single page of results with given params."""
        try:
            response = requests.get(base_url, headers=headers, params=params)
            if response.status_code != 200:
                print(f"Strapi error {response.status_code} for params {params}")
                return []
            return response.json().get("data", [])
        except Exception as e:
            print(f"Error fetching Strapi data for params {params}: {e}")
            return []

    # If no diseases provided, fetch all entries for the target
    if not diseases:
        params = {
            "filters[target][$eqi]": target,
            "pagination[page]": 1,
            "pagination[pageSize]": 500
        }
        items = fetch_for_params(params)
        diseases_to_iterate = [None]  # signal “all”
    else:
        # Otherwise, fetch per-disease
        diseases_to_iterate = diseases

    # Iterate and collect
    for disease in diseases_to_iterate:
        params = {
            "filters[target][$eqi]": target,
            "pagination[page]": 1,
            "pagination[pageSize]": 500
        }
        if disease:
            params["filters[disease][$eqi]"] = disease

        items = fetch_for_params(params)
        for item in items:
            phase = item.get("trialRecord", {}).get("phase")
            trial_status = item.get("trialRecord", {}).get("trialStatus")
            source_url = item.get("trialRecord", {}).get("url")
            trial_id = item.get("trialRecord", {}).get("trialID")

            # normalize to lists
            if isinstance(source_url, str):
                source_url = [source_url]
            elif not isinstance(source_url, list):
                source_url = []
            if isinstance(trial_id, str):
                trial_id = [trial_id]
            elif not isinstance(trial_id, list):
                trial_id = []

            filtered_data.append({
                "Disease": (item.get("disease") or "").lower(),
                "Drug": item.get("drug", ""),
                "Type": item.get("type", ""),
                "Mechanism of Action": item.get("MoA", ""),
                "Phase": f"Phase {phase}" if phase else "N/A",
                "Status": trial_status,
                "Target": item.get("target", ""),
                "Source URLs": source_url,
                "Sponsor": item.get("sponsor", ""),
                "ApprovalStatus": item.get("trialRecord", {}).get("approvalStatus"),
                "WhyStopped": get_why_stopped(nct_id=trial_id[0]) if trial_id else ""
            })

    return filtered_data
def fetch_patient_stories_from_source(disease: str):
    """
    Fetch Patient Stories from internally hosted service
    """
    headers = {"Content-Type": "application/json"}
    
    params = {"search_name": disease}
    url = f"{PATIENT_STORIES_URL}/fetch_patient_stories"
    response = requests.post(url, params=params, headers=headers, auth=HTTPBasicAuth(username, password))
    
    if response.status_code == 200:
        return response.json()
    else:
        return []

#kol-videos endpoint helper function
def fetch_kol_videos_from_source(disease: str):
    """
    Fetch KOL Videos from internally hosted service
    """
    headers = {"Content-Type": "application/json"}
    
    params = {"search_name": disease}
    url = f"{PATIENT_STORIES_URL}/fetch_kol_interviews"  
    response = requests.post(url, params=params, headers=headers, auth=HTTPBasicAuth(username, password))
    
    if response.status_code == 200:
        return response.json()
    else:
        return []