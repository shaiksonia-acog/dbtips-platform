import json
from typing import Dict, Any
from typing import Optional
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException
from typing import Dict, List, Set
from typing import Optional,Union
import json
from gql_queries import GetTargetUniProt
from gql_queries import DiseaseAssociatedTargetQuery,MousePhenotypesQuery,PublicationQuery
from gql_variables import DiseaseAssociationTargetVariables
from typing import List, Dict, Any
import requests
import json
import html
import os
from component_services.evidence_services import get_network_biology_strapi
from component_services.market_intelligence_service import get_pmids_for_nct_ids,add_outcome_status,get_indication_pipeline_strapi
import logging
from component_services.drug_extraction import chembl_sessions_request


# Set up logger
logger = logging.getLogger(__name__)

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, frozenset):
            return list(obj)  # Convert frozenset to list
        return super().default(obj)


def format_for_cytoscape(query_result, node_types, edge_types):
    nodes = {}
    edges = {}

    for record in query_result:
        # Add nodes
        for node in node_types:
            node_data = record[node]
            if node_data.id not in nodes:
                nodes[node_data.id] = {
                    "data": {
                        "id": str(node_data.id),
                        "label": node_data.get("name") or node_data.get("id"),
                        "type": get_type_from_labels(node_data.labels),
                        "labels": node_data.labels,
                        "properties": dict(node_data)
                    }
                }

        # Add edges
        for rel in edge_types:
            rel_data = record[rel]
            if rel_data.id not in edges:
                prop_dict = dict(rel_data)
                prop_dict["source"] = str(rel_data.start_node.get("name") or rel_data.start_node.get("id"))
                prop_dict["target"] = str(rel_data.end_node.get("name") or rel_data.end_node.get("id"))

                edges[rel_data.id] = {
                    "data": {
                        "source": str(rel_data.start_node.id),
                        "target": str(rel_data.end_node.id),
                        "label": rel_data.type,
                        "properties": prop_dict
                    }
                }

    elements = list(nodes.values()) + list(edges.values())

    return elements


def get_type_from_labels(labels) -> str:
    node_types = {
        "biolink:Gene": "Gene",
        "biolink:Disease": "Disease",
        "biolink:Pathway": "Pathway"
    }

    for type in node_types:
        if type in labels:
            return node_types[type]


# def get_efo_id(disease_name: str) -> str:
#     """
#     Find the EFO ID for a given disease name, semantically. Considers the topmost result by default.
#     """
#     response = requests.get("https://www.ebi.ac.uk/ols/api/search",
#                             params={"q": disease_name, "ontology": "efo"})
#     if response.status_code == 200:
#         results = response.json().get('response', {}).get('docs', [])
#         if results:
#             first_result = results[0]
#             efo_id = first_result.get('obo_id')
#             print(f"Found EFO ID for {disease_name}: {efo_id}")
#             return efo_id
#         else:
#             print(f"No results found for {disease_name}")
#             return None
#     else:
#         print(f"Error {response.status_code} during search")
#         return None

def request_open_targets_api(disease_name: str) -> Optional[str]:
    """
    Fetch the EFO ID for a given disease using the OpenTargets GraphQL API.

    Args:
        disease_name (str): Name of the disease to search.

    Returns:
        Optional[str]: The EFO ID if found, else None.
    """
    url: str= "https://api.platform.opentargets.org/api/v4/graphql"
    headers = {"Content-Type": "application/json"}
    
    # GraphQL query
    query = """
    query searchDisease($queryString: String!) {
      search(queryString: $queryString, entityNames: ["disease"], page: {index: 0, size: 100}) {
        total
        hits {
          id
          name
          entity
          description
        }
      }
    }
    """
    
    # Variables for the query
    variables = {"queryString": disease_name}
    
    try:
        # Send the POST request
        response = requests.post(url, json={"query": query, "variables": variables}, headers=headers)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        
        # Parse the response
        if response.status_code == 200:
            data = response.json()
        else:
            data = None
        # hits = data.get("data", {}).get("search", {}).get("hits", [])
        
        # if hits:
        #     efo_id = hits[0].get("id", None)
        #     return efo_id
        # else:
        #     print(f"No EFO ID found for '{disease_name}'")
        #     return None

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None
    
    return data
  
def get_efo_id(disease_name: str)-> Optional[str]:
    open_t_data = request_open_targets_api(disease_name)
    if open_t_data:
        exact_matches = [hit for hit in open_t_data["data"]["search"]["hits"] if hit["name"].lower() == disease_name.lower()]
        if exact_matches:
            return exact_matches[0]['id']
        else:
            print(f"EFO ID not found for {disease_name} in OpenTargets")
            return None
    else:
        print(f"No records in OpenTargets for {disease_name}")

def find_disease_id_by_name(jsonl_file: str, disease_name: str) -> Optional[str]:
    """
    Find the corresponding ID for a given disease name in a JSONL file,
    prioritizing EFO IDs first, then MONDO, and then other IDs.

    Parameters:
    - jsonl_file (str): Path to the JSONL file containing disease data.
    - disease_name (str): The disease name to search for.

    Returns:
    - Optional[str]: The prioritized ID of the disease if found, otherwise None.
    """
    efo_id: Optional[str] = None
    mondo_id: Optional[str] = None
    other_id: Optional[str] = None

    # Open and iterate through the JSONL file line by line
    with open(jsonl_file, 'r') as file:
        for line in file:
            # Parse each line as a JSON object
            data = json.loads(line)

            # Check if the 'name' matches the disease name (case-insensitive)
            if data['name'].lower() == disease_name.lower():
                disease_id = data.get('id')

                # Prioritize the IDs: EFO > MONDO > others
                if "EFO" in disease_id and not efo_id:
                    efo_id = disease_id
                elif "MONDO" in disease_id and not mondo_id:
                    mondo_id = disease_id
                elif not other_id:
                    other_id = disease_id

    # Return the prioritized ID if found
    if efo_id:
        return efo_id
    elif mondo_id:
        return mondo_id
    else:
        return other_id


def send_graphql_request(query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    base_url: str = "https://api.platform.opentargets.org/api/v4/graphql"
    try:
        response = requests.post(
            base_url,
            json={'query': query, 'variables': variables}
        )
        response.raise_for_status()  # Raise an error for bad responses (4xx and 5xx)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error while connecting to the API: {str(e)}")

    return response.json()


def save_response_to_file(file_path: str, response: Dict):
    """ Save response to a file in JSON format """
    with open(file_path, 'w') as file:
        json.dump(response, file)


def save_big_response_to_file(file_path: str, response: Dict):
    """ Save response to a file in JSON format """
    with open(file_path, 'w') as file:
        json.dump(response, file, cls=CustomJSONEncoder)
        file.flush()


def load_response_from_file(file_path: str) -> Dict:
    """ Load response from a file in JSON format """
    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            file.write("{}")
    with open(file_path, 'r') as file:
        return json.load(file)


def get_associated_targets(disease_name: str,sort_by: str) -> List[str]:
    """
    Queries the OpenTargets API for disease-associated targets using a disease name.

    Args:
        disease_name (str): The name of the disease.

    Returns:
        list: A list of target IDs associated with the disease.
        or
        dict: In case of an error, a dictionary with error message.
    """
    # OpenTargets GraphQL API endpoint
    opentargets_url = "https://api.platform.opentargets.org/api/v4/graphql"

    try:
        # Get the EFO ID for the disease
        efo_id = get_efo_id(disease_name)
        if not efo_id:
            print(f"No EFO ID found for the disease: {disease_name}")
            return []

        efo_id = efo_id.replace(":", "_")
        print(f"EFO ID for {disease_name}: {efo_id}")

        # Prepare the variables for the query
        variables = DiseaseAssociationTargetVariables.replace('{efo_id}', efo_id)
        variables=variables.replace('{sort_by}',sort_by)
        print(f"Variables: {variables}")

        # Construct the GraphQL payload
        payload = {
            "query": DiseaseAssociatedTargetQuery,
            "variables": variables,
        }

        # Send the request to the OpenTargets API
        response = requests.post(opentargets_url, json=payload)

        # Check if the response is successful
        if response.status_code != 200:
            print(
                f"Failed to query OpenTargets API. Status Code: {response.status_code}, Response: {response.text}"
            )
            return []

        # Extract the list of target IDs from the response
        data = response.json()
        target_ids = [
            target['target']['id'] 
            for target in data.get('data', {}).get('disease', {}).get('associatedTargets', {}).get('rows', [])
        ]

        return target_ids

    except Exception as e:
        print("error:", str(e))
        return []

def get_mouse_phenotypes(ensembl_id: str):
        """
        Get Mouse Phenotypes for a given ensembl_id
        """
        print(f"Using Ensembl ID: {ensembl_id}")
        variables = {"ensemblId": ensembl_id}
        otp_base_url = "https://api.platform.opentargets.org/api/v4/graphql"
        r = requests.post(otp_base_url, json={"query": MousePhenotypesQuery, "variables": variables})
        api_response = json.loads(r.text)

        if 'errors' in api_response:
            print("Error in API response:", api_response['errors'])

        return api_response


# Function to fetch all rows
def fetch_all_publications(efo_id: str, ensembl_ids: List[str], size: int = 100) -> List[Dict[str, Union[str, Dict]]]:
    """
    Fetch all rows of evidence data for the given EFO ID and Ensembl IDs.

    Args:
        efo_id (str): The EFO ID for the disease.
        ensembl_ids (List[str]): List of Ensembl IDs for the targets.
        size (int): Number of results per page (default: 50).

    Returns:
        List[Dict]: List of all rows fetched from the API.
    """
    # Define the API endpoint
    api_url = "https://api.platform.opentargets.org/api/v4/graphql"
    
    # Initialize variables
    all_rows = []
    cursor = None

    try:
        while True:
            # Prepare query variables
            variables = {
                "efoId": efo_id,
                "ensemblIds": ensembl_ids,
                "size": size,
                "cursor": cursor
            }

            # Make the API request
            response = requests.post(api_url, json={"query": PublicationQuery, "variables": variables})
            data = response.json()

            # Handle API errors
            if "errors" in data:
                raise ValueError(f"API Error: {data['errors']}")

            # Extract rows and cursor
            europe_pmc_data = data["data"]["disease"]["europePmc"]
            rows = europe_pmc_data["rows"]
            cursor = europe_pmc_data["cursor"]

            # Add rows to the list
            all_rows.extend(rows)

            # Break the loop if there are no more pages
            if cursor is None:
                break

    except Exception as e:
        print(f"An error occurred: {e}")
    
    return all_rows

# print(get_efo_id("atopic eczema"))

def get_exact_synonyms(disease_name: str) -> List[str]:
    """
    Fetch the exact synonyms (`hasExactSynonym`) for a given disease from the OpenTargets API.

    Args:
        disease_name (str): The name of the disease for which to retrieve synonyms.

    Returns:
        List[str]: A list of terms corresponding to `hasExactSynonym` for the disease.
                   Returns an empty list if the response format is invalid or if any error occurs.
    """
    try:
        # Get the EFO ID for the disease
        efo_id: str = get_efo_id(disease_name)

        # GraphQL query to fetch disease information
        query: str = """
        query diseaseAnnotation {
          disease(efoId: "%s") {
            id
            name
            synonyms {
              relation
              terms
            }
          }
        }
        """ % efo_id

        # OpenTargets API URL
        api_url: str = "https://api.platform.opentargets.org/api/v4/graphql"

        # Make the POST request to the API
        response = requests.post(api_url, json={"query": query})

        # Raise an exception if the API call failed
        response.raise_for_status()

        # Parse the JSON response
        data: Dict = response.json()

        # Extract synonyms with `hasExactSynonym` relation
        synonyms = []
        if data["data"] and data["data"]["disease"] and data["data"]["disease"]["synonyms"]:
            for synonym_entry in data["data"]["disease"]["synonyms"]:
                if synonym_entry["relation"] == "hasExactSynonym":
                    synonyms.extend(synonym_entry["terms"])

        return synonyms+[disease_name]

    except Exception as e:
        # Print the error message and return an empty list
        print(f"An error occurred: {e}")
        return [disease_name]
    

def get_conver_later_strapi() -> str:
    """
    Fetches and returns the landing page data for from Strapi.

    Returns:
        str: The landing page data as a string if successful, or an empty string if an error occurs.
    """
    # Define the API endpoint, dynamically include the disease name
    STRAPI_BASE_URL = os.getenv("STRAPI_BASE_URL")
    url = (
        f"{STRAPI_BASE_URL}/api/cover-pages"
    )

    # Retrieve the API token
    api_token = os.getenv('STRAPI_API_TOKEN')

    if not api_token:
        print("API token not found in environment variables. Set 'STRAPI_API_TOKEN'.")
        return ""

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
            json_content = response.json()
            return json_content["data"][0].get("landing_page", "")
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            return ""
    except Exception as e:
        print(f"An error occurred: {e}")
        return ""
    


def get_target_indication_pairs_strapi(disease_name: str) -> List[Dict[str, Any]]:
    """
    Fetches and filters target-indication pairs data from Strapi for the given disease name.

    Args:
        disease_name (str): The name of the disease to filter target-indication pairs.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing filtered data fields.
    """
    # Define the base API endpoint
    STRAPI_BASE_URL = os.getenv("STRAPI_BASE_URL")
    base_url = f"{STRAPI_BASE_URL}/api/target-indication-pairs"
    # Include the disease name as a query filter
    url = f"{base_url}?filters[disease][$eqi]={disease_name}&pagination[page]=1&pagination[pageSize]=500"

    # API token for authorization
    api_token = os.getenv('STRAPI_API_TOKEN') 

    # Check if the token is provided
    if not api_token:
        print("API token not found. Please set the 'STRAPI_API_TOKEN'.")
        return []

    # Set up the headers for the request
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    try:
        # Send a GET request to the API
        response = requests.get(url, headers=headers)

        # Check if the response is successful
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()
            filtered_data = []

            # Extract only the relevant fields
            for item in data.get("data", []):
                filtered_data.append({
                    "Disease": item.get("disease", ""),
                    "Target": item.get("target", ""),
                    "EvidenceType": item.get("evidenceType", ""),
                    "Modality": item.get("modality", ""),
                })

            return filtered_data
        else:
            # Print error information
            print(f"Failed to fetch data. Status code: {response.status_code}")
            print(response.text)
            return []

    except Exception as e:
        # Handle exceptions
        print(f"An error occurred: {e}")
        return []
    

def enrich_disease_pathway_results(disease_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enriches disease results by fetching additional data from Strapi and appending
    the fetched data to the 'results' key of each disease.

    Args:
        disease_results (Dict[str, Any]): A dictionary containing disease data.

    Returns:
        Dict[str, Any]: The enriched disease results.
    """
    for disease, data in disease_results.items():
        print(f"Fetching additional data for disease: {disease}...")
        strapi_result = get_network_biology_strapi(disease_name=disease)  # Fetch data
        if "results" in disease_results[disease] and isinstance(disease_results[disease]["results"], List):
            disease_results[disease]["results"].extend(strapi_result)  # Append the result

    return disease_results


def add_pipeline_indication_records(diseases_and_efo, existing_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes diseases and combines the output with an existing response, and returns the updated response.
    """
    ans: Dict[str, Any] = {}

    # Step 1: Process each disease name with get_indication_pipeline_strapi
    for disease_name in diseases_and_efo:
        ans[disease_name] = get_indication_pipeline_strapi(disease_name)

    # Step 2: Process the indication pipeline with get_pmids_for_nct_ids
    indication_pipeline = get_pmids_for_nct_ids(ans)
    print("get_pmids_for_nct_ids\n")

    # Step 3: Add outcome status to the indication pipeline
    indication_pipeline = add_outcome_status(indication_pipeline)
    print("add_outcome_status\n")

    # Step 4: Combine with the existing response
    if "indication_pipeline" not in existing_response:
        existing_response["indication_pipeline"] = {}
    
    # Merge the new indication pipeline into the existing one
    for key, value in indication_pipeline.items():
        if key not in existing_response["indication_pipeline"]:
            existing_response["indication_pipeline"][key] = value
        else:
            # Append new records to the existing array if the key already exists
            existing_response["indication_pipeline"][key].extend(value)

    return existing_response

def fetch_nct_data(nct_ids: List[str]) -> List[Dict[str, str]]:
    """
    Fetches the official titles for a list of NCT IDs from the clinicaltrials.gov API.

    Args:
        nct_ids (List[str]): A list of NCT IDs.

    Returns:
        Dict[str, str]: A dictionary mapping NCT IDs to their official titles.
    """
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    nct_data = []    

    for nct_id in nct_ids:
        nct_details: Dict[str, str] = {"nctid": nct_id}
        try:
            # Construct the API URL for the specific NCT ID
            url = f"{base_url}/{nct_id}"
            # Make a GET request to the API
            response = chembl_sessions_request(url)
            # Raise an exception if the response status code is not 200
            response.raise_for_status()
            # Parse the JSON response
            data = response.json()
            
            # Extract the official title if it exists
            nct_details["title"] = data.get("protocolSection", {}).get("identificationModule", {}).get("officialTitle", "")

            nct_details["sponsor"] = data.get("protocolSection", {}).get("identificationModule", {}).get("organization", {}).get("fullName","")
            
            status = data.get("protocolSection", {}).get("statusModule", {}).get("overallStatus", "")

            if "unknown" in status.lower():
                status = data.get("protocolSection", {}).get("statusModule", {}).get("lastKnownStatus", "")

            nct_details["Status"] = status
            phase = data.get("protocolSection", {}).get("designModule", {}).get("phases", "")
            if phase :
                nct_details["phase"] = phase[0]

            interventions = data.get("protocolSection", {}).get("armsInterventionsModule", {}).get("interventions", None)
            drugs = []
            if interventions:
                for intervention in interventions:
                    if "drug" in intervention["type"].lower():
                        drugs.append(intervention["name"])

            nct_details["drug"] = drugs

            nct_details["whyStopped"] = data.get("protocolSection", {}).get("statusModule", ).get("whyStopped", "")

            nct_details["Source URLs"] = [f"https://clinicaltrials.gov/ct2/show/{nct_id}"]

            references = data.get("protocolSection", {}).get("referencesModule", {}).get("references", [])
            nct_details["PMIDs"] = []
            if references:
                for ref in references:
                    if "pmid" in ref:
                        nct_details["PMIDs"].append(ref.get("pmid"))
            print(f"PMIDs for {nct_id}: {nct_details['PMIDs']}")

        except Exception as e:
            # Handle errors (e.g., network issues, invalid NCT ID)
            print(f"Error fetching title for {nct_id}: {str(e)}")
            nct_details[nct_id] = ""
        
        nct_data.append(nct_details)
    return nct_data



def fetch_nct_titles(nct_ids: List[str]) -> Dict[str, str]:
    """
    Fetches the official titles for a list of NCT IDs from the clinicaltrials.gov API.

    Args:
        nct_ids (List[str]): A list of NCT IDs.

    Returns:
        Dict[str, str]: A dictionary mapping NCT IDs to their official titles.
    """
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    nct_to_title: Dict[str, str] = {}

    for nct_id in nct_ids:
        try:
            # Construct the API URL for the specific NCT ID
            url = f"{base_url}/{nct_id}"
            logger.info(f"Generating Trials for: {url}")
            # Make a GET request to the API
            response = chembl_sessions_request(url)
            # Raise an exception if the response status code is not 200
            response.raise_for_status()
            # Parse the JSON response
            data = response.json()
            
            # Extract the official title if it exists
            official_title = data.get("protocolSection", {}).get("identificationModule", {}).get("officialTitle")
            if official_title:
                nct_to_title[nct_id] = official_title
            else:
                print(f"Title not available for {nct_id}")
                nct_to_title[nct_id] = ""
        except Exception as e:
            # Handle errors (e.g., network issues, invalid NCT ID)
            print(f"Error fetching title for {nct_id}: {str(e)}")
            nct_to_title[nct_id] = ""

    return nct_to_title

def get_chembl_id_exact(drug_name):
    """
    Attempts to find the best ChEMBL ID for a drug name.
    First tries exact matches (preferred name and synonyms).
    If no exact match is found, tries partial matches.
    Returns a list with the first matching ChEMBL ID, or an empty list if not found.
    """
    base = "https://www.ebi.ac.uk/chembl/api/data/molecule.json"
    # 1. Try exact matches
    params_list = [
        {"pref_name__iexact": drug_name},
        {"molecule_synonyms__synonym__iexact": drug_name},
        {"molecule_synonyms__molecule_synonym__iexact": drug_name},
    ]
    for params in params_list:
        params.update({"limit": 200, "offset": 0})
        resp = chembl_sessions_request(base, params=params)
        if resp.status_code == 200:
            molecules = resp.json().get("molecules", [])
            if molecules:
                chembl_id = molecules[0]["molecule_chembl_id"]
                return [chembl_id]
    # 2. If no exact match, try partial matches
    params_list_partial = [
        {"pref_name__icontains": drug_name},
        {"molecule_synonyms__synonym__icontains": drug_name},
        {"molecule_synonyms__molecule_synonym__icontains": drug_name},
    ]
    for params in params_list_partial:
        params.update({"limit": 200, "offset": 0})
        resp = chembl_sessions_request(base, params=params)
        if resp.status_code == 200:
            molecules = resp.json().get("molecules", [])
            if molecules:
                chembl_id = molecules[0]["molecule_chembl_id"]
                return [chembl_id]
    return []

def fetch_molecule_type(chembl_id):
    """
    Given a ChEMBL ID, fetches the molecule type (e.g., 'Small molecule', 'Protein').
    Returns 'NA' if not found or on error.
    """
    url = f"https://www.ebi.ac.uk/chembl/api/data/molecule/{chembl_id}.json"
    resp = chembl_sessions_request(url)
    if resp.status_code == 200:
        return resp.json().get("molecule_type", "NA")
    else:
        print(f"[WARN] Failed to fetch molecule type ({resp.status_code}) for {chembl_id}")
        return "NA"

def fetch_approval_status(chembl_id, disease_name):
    """
    Checks if a drug (by ChEMBL ID) is approved for a given disease/indication.
    Returns 'Approved' if max_phase_for_ind is 4 for the indication,
    'Not Approved' if found but not phase 4, or 'NA' if not found.
    """
    url = f"https://www.ebi.ac.uk/chembl/api/data/drug_indication.json?molecule_chembl_id={chembl_id}&limit=1000"
    resp = chembl_sessions_request(url)
    if resp.status_code == 200:
        for ind in resp.json().get("drug_indications", []):
            # Safely handle None values for efo_term and mesh_heading
            efo_term = (ind.get("efo_term") or "").strip().lower()
            mesh_heading = (ind.get("mesh_heading") or "").strip().lower()
            if disease_name and (
                disease_name.strip().lower() == efo_term or
                disease_name.strip().lower() == mesh_heading or
                disease_name.strip().lower() in efo_term or
                disease_name.strip().lower() in mesh_heading
            ):
                if float(ind.get("max_phase_for_ind", 0)) == 4:
                    return "Approved"
                else:
                    return "Not Approved"
    return "NA"

def fetch_moa_targets_for_ids(chembl_ids):
    """
    For a list of ChEMBL IDs, fetches mechanism of action (MoA) and target information.
    Returns a list of tuples: (chembl_id, mechanism_of_action, target_name).
    If no mechanism is found, tries to get the first target_chembl_id from the activity endpoint as a fallback.
    """
    mechanisms = []
    for chembl_id in chembl_ids:
        mech_url = (
            "https://www.ebi.ac.uk/chembl/api/data/mechanism.json"
            f"?molecule_chembl_id={chembl_id}&limit=1000&offset=0"
        )
        resp = chembl_sessions_request(mech_url)
        found_mechanism = False
        if resp.status_code == 200:
            for mech in resp.json().get("mechanisms", []):
                moa = mech.get("mechanism_of_action") or "NA"
                tgt_id = mech.get("target_chembl_id")
                tgt_name = fetch_target_name(tgt_id) if tgt_id else "NA"
                mechanisms.append((chembl_id, moa, tgt_name, tgt_id))
                found_mechanism = True
        else:
            print(f"[WARN] Mechanism fetch failed ({resp.status_code}) for {chembl_id}")

        # Fallback: If no mechanism found, try activity endpoint for target_chembl_id
        if not found_mechanism:
            act_url = f"https://www.ebi.ac.uk/chembl/api/data/activity.json?molecule_chembl_id={chembl_id}&limit=1"
            act_resp = chembl_sessions_request(act_url)
            if act_resp.status_code == 200:
                activities = act_resp.json().get("activities", [])
                if activities:
                    tgt_id = activities[0].get("target_chembl_id")
                    tgt_name = fetch_target_name(tgt_id) if tgt_id else "NA"
                    mechanisms.append((chembl_id, "NA", tgt_name, tgt_id))

    return mechanisms

def fetch_target_name(target_chembl_id):
    """
    Given a ChEMBL target ID, fetches the gene symbol (GENE_SYMBOL) for the target.
    Falls back to the preferred name if no gene symbol is found.
    Returns 'NA' if not found or on error.
    """
    url = f"https://www.ebi.ac.uk/chembl/api/data/target/{target_chembl_id}.json"
    resp = chembl_sessions_request(url)
    if resp.status_code == 200:
        target = resp.json()
        # Search for GENE_SYMBOL in target_components
        for comp in target.get("target_components", []):
            for syn in comp.get("target_component_synonyms", []):
                if syn.get("syn_type") == "GENE_SYMBOL":
                    return syn.get("component_synonym", "NA")
        # Fallback to pref_name
        return target.get("pref_name", "NA")
    else:
        print(f"[WARN] Failed to fetch target name ({resp.status_code}) for {target_chembl_id}")
        return "NA"

def extract_moa_keyword(moa):
    """
    Extracts a short keyword from the MoA string (e.g., 'inhibitor', 'agonist').
    If a known keyword is found, returns it; otherwise, returns the last word or 'NA'.
    """
    for kw in ["inhibitor", "agonist", "antagonist", "modulator", "blocker", "activator"]:
        if kw in moa.lower():
            return kw
    # fallback: last word
    return moa.split()[-1] if moa else "NA"

def get_moa_short(moa_targets):
    """
    For a list of (chembl_id, moa, target) tuples, returns a short MoA string.
    Format: 'GENE_SYMBOL: keyword' for each pair, comma-separated for multiple pairs.
    Returns 'NA' if no valid pairs are found.
    """
    short_blocks = []
    for chembl_id, moa, target,tgt_id in moa_targets:
        if target and target != "NA":
            moa_kw = extract_moa_keyword(moa)
            short_blocks.append(f"{target}: {moa_kw}")
    return ", ".join(short_blocks) if short_blocks else "NA"

def format_multi_drug_output(blocks):
    """
    Formats output for multiple drugs and multiple values per drug.
    - Multiple values for a single drug are comma-separated.
    - Multiple drugs in a row are pipe-separated.
    Example: [["A", "B"], ["C"]] -> "A, B | C"
    """
    return " | ".join([", ".join([v for v in vals if v and v != "NA"]) if vals else "NA" for vals in blocks])

def get_target_type(target_id):
    """
    Given a target ID, fetches the target type (e.g., 'SINGLE PROTEIN', 'MULTI-PROTEIN').
    Returns 'NA' if not found or on error.
    """
    url = f"https://www.ebi.ac.uk/chembl/api/data/target/{target_id}.json"
    print("url: ", url)
    resp = chembl_sessions_request(url)
    if resp.status_code == 200:

        return resp.json().get("target_type", "NA")
    else:
        print(f"[WARN] Failed to fetch target type ({resp.status_code}) for {target_id}")
        return "NA"



def generate_mapped_diseases_for_disease_area(disease_area, articles_data):
    """
    Annotate each article with the diseases falling under given disease area
    """
    disease_area_mesh_tree_numbers = get_mesh_tree_numbers(disease_area)
    parent_tns = [tn.split('.')[0] for tn in disease_area_mesh_tree_number]
    for article in articles_data:
        article["mapped_diseases"] = []
        for mesh_term in article['mesh_terms']:
            tree_number = get_mesh_tree_number(mesh_term)
            if any(tree_number.startswith(parent_tn) for parent_tn in parent_tns):
                article["mapped_diseases"].append(mesh_term)

    return articles_data
