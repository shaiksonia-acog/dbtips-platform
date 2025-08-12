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


def save_response_to_file(file_path: str, data: Dict[str, Any]) -> None:
    """
    Save data to JSON file
    
    Args:
        file_path: Path to save JSON file
        data: Data to save
    """
    try:
        # Ensure directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        log.debug(f"Data saved to {file_path}")
    except Exception as e:
        log.error(f"Failed to save data to {file_path}: {e}")
        raise


def save_big_response_to_file(file_path: str, response: Dict):
    """ Save response to a file in JSON format """
    with open(file_path, 'w') as file:
        json.dump(response, file, cls=CustomJSONEncoder)
        file.flush()


def load_response_from_file(file_path: str) -> Dict[str, Any]:
    """
    Load JSON response from file
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Dictionary containing loaded data
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        log.warning(f"Cache file not found: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        log.error(f"Failed to decode JSON from {file_path}: {e}")
        return {}


def add_years(date_str: str, years: int) -> str:
    """
    Add or subtract years from a given date in the format 'yyyy-mm-dd'.

    Args:
    date_str (str): The input date as a string in the format 'yyyy-mm-dd'.
    years (int): The number of years to add (positive) or subtract (negative).

    Returns:
    str: The modified date as a string in the format 'yyyy-mm-dd'.
    """
    if not date_str:
        return ""

    # Parse the input date string to a datetime object
    date: datetime = datetime.strptime(date_str, "%Y-%m-%d")

    # Modify the date by adding/subtracting the given number of years
    new_date: datetime = date + relativedelta(years=years)

    # Return the new date formatted back into 'dd-mm-yyyy' string
    return new_date.strftime("%Y-%m-%d")


def calculate_expiry_date(filing_date: str, invention_type: str, publication_date: str) -> str:
    """
    Calculate the expiry date of the patent based on its type (UTILITY, DESIGN, PLANT).

    Args:
    filing_date (str): Filing date of the patent in 'dd-mm-yyyy' format.
    invention_type (str): Type of patent - UTILITY, DESIGN, or PLANT.
    publication_date (str): Publication date (for design patents) in 'dd-mm-yyyy' format, if applicable.

    Returns:
    str: The calculated expiry date in 'dd-mm-yyyy' format.
    """
    # Convert the invention type to lowercase for case-insensitive comparison
    invention_type = invention_type.lower()

    if invention_type == "utility" or invention_type == "plant":
        # Utility and Plant patents expire 20 years from the filing date
        return add_years(filing_date, 20)
    elif invention_type == "design":
        # Parse the filing date to check if it is before or after May 13, 2015
        date_filed: datetime = datetime.strptime(filing_date, "%m-%d-%Y")
        cutoff_date: datetime = datetime(2015, 5, 13)

        # Design patents filed after May 13, 2015 expire 15 years from publication date
        # Design patents filed on or before May 13, 2015 expire 14 years from publication date
        years_to_add: int = 15 if date_filed > cutoff_date else 14

        # If the publication date is not provided, use the filing date instead
        return add_years(publication_date, years_to_add)
    else:
        # For unknown invention types, return 20 years from the filing date
        return add_years(filing_date, 20)
    

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
            response = requests.get(url)
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
            # Make a GET request to the API
            response = requests.get(url)
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

