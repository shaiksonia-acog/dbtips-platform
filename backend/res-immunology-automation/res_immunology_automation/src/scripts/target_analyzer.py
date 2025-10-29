"""
#from res_immunology_automation.src.scripts.gql_queries import DiseaseAssociationsQuery, DiseaseDescendantsQuery, TargetAssociationsQuery, GenePageL2GPipelineQuery, GeneOntologyQuery, TargetDescriptionQuery, MousePhenotypesQuery, TargetabilityQuery, TractabilityQuery, CompGenomicsQuery, DifferentialRNAQuery, GetTargetUniProt, KnownDrugsQuery, SafetyQuery
#from res_immunology_automation.src.scripts.gql_variables import DiseaseAssociationQueryVariables, TargetAssociationQueryVariables, GeneOntologyVariables, TargetabilityVariables
"""
from gql_queries import DiseaseAssociationsQuery, DiseaseDescendantsQuery, TargetAssociationsQuery, \
    GenePageL2GPipelineQuery, GeneOntologyQuery, TargetDescriptionQuery, MousePhenotypesQuery, TargetabilityQuery, \
    TractabilityQuery, CompGenomicsQuery, DifferentialRNAQuery, GetTargetUniProt, KnownDrugsQuery, SafetyQuery, \
    PublicationQuery, DiseaseKnownDrugs,GeneEssentialityMapTargetQuery
from gql_variables import DiseaseAssociationQueryVariables, TargetAssociationQueryVariables, GeneOntologyVariables, \
    TargetabilityVariables, PublicationVariables,GeneEssentialityMapTargetVariable
from typing import Dict, List
import requests
import json, time
from tqdm import tqdm
import pandas as pd
from utils import get_efo_id
from typing import *
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class TargetAnalyzer:
    """
    Given a target (gene name), the TargetAnalyzer class provides various functions for easy analysis.
    """

    def __init__(self, target: str):
        self.target = target
        self.ensembl_id = self.get_ensembl_id(self.target)
        self.hgnc_id = self.get_hgnc_id(self.target)
        self.otp_base_url = "https://api.platform.opentargets.org/api/v4/graphql"
        self.otg_base_url = "https://api.genetics.opentargets.org/graphql"
        self.uniprot_id = self.get_uniprotkb_id(self.target)
        self.uniprot_base_url = "https://rest.uniprot.org/uniprotkb/search?&query="

    def get_huGE_score(self, phenotype: str, target: str = None) -> float:
        """
        Get the huGE score for a given phenotype and target.
        """
        gene = self.target if not target else target
        huge_score_url = f"https://bioindex.hugeamp.org/api/bio/query/huge?q={gene}"
        response = requests.get(huge_score_url)

        if response.ok:
            for data in response.json().get('data'):
                if data.get('phenotype') == phenotype:
                    print(data.get('huge'))
        else:
            print("Error:", response.text)

    def get_efo_id(self, disease_name: str) -> str:
        """
        Find the EFO ID for a given disease name, semantically. Considers the topmost result by default.
        """
        response = requests.get("https://www.ebi.ac.uk/ols/api/search",
                                params={"q": disease_name, "ontology": "efo"})
        if response.status_code == 200:
            results = response.json().get('response', {}).get('docs', [])
            if results:
                first_result = results[0]
                efo_id = first_result.get('obo_id')
                print(f"Found EFO ID for {disease_name}: {efo_id}")
                return efo_id
            else:
                print(f"No results found for {disease_name}")
                return None
        else:
            print(f"Error {response.status_code} during search")
            return None

    def get_uniprotkb_id(self, target: str = None):
        """
        Get Uniprot id for the given target
        """
        if target is not None:
            ensembl_id = self.get_ensembl_id(target)
        else:
            ensembl_id = self.ensembl_id

        if not ensembl_id:
            print("Ensembl ID is None, check get_ensembl_id function.")
            return None

        print(f"Using Ensembl ID: {ensembl_id}")
        variables = {"id": ensembl_id}

        r = requests.post(self.otp_base_url, json={"query": GetTargetUniProt, "variables": variables})
        api_response = json.loads(r.text)
        if 'errors' in api_response:
            print("Error in API response:", api_response['errors'])
            return None

        protein_ids = api_response.get('data', {}).get('target', {}).get('proteinIds', [])
        for protein in protein_ids:
            if protein.get('source') == 'uniprot_swissprot':
                return protein.get('id')

        print("No uniprot_swissprot ID found.")
        return None

    def get_descendants(self, disease_name: str) -> List:
        """
        Get the EFO IDs of all the descendants of a given disease.
        """
        efo_id = self.get_efo_id(disease_name)
        efo_id = efo_id.replace(":", "_")
        variables = """
        {"id": "{efo_id}"}
        """
        variables = variables.replace("{efo_id}", efo_id)
        r = requests.post(self.otp_base_url, json={"query": DiseaseDescendantsQuery, "variables": variables})
        api_response = json.loads(r.text)
        return api_response['data']['disease']['descendants']

    def get_target_gene_map(self,target:str=None):
        """
        Get gene map for a given target
        """
        if target is not None:
            ensembl_id = self.get_ensembl_id(target)
        else:
            ensembl_id = self.ensembl_id
        variables = GeneEssentialityMapTargetVariable.replace('{ensembl_id}', ensembl_id)
        print(f"varaible {variables}")
        print(f"ensemblId",{ensembl_id})
        r = requests.post(self.otp_base_url, json={"query": GeneEssentialityMapTargetQuery, "variables": variables})
        api_response = json.loads(r.text)
        print(api_response)
        return api_response
    
    def get_associated_diseases(self, target: str = None, sort_by: str = "score") -> Dict:
        """
        Get diseases associated to a given target in JSON format.
        """
        if target is None:
            ensembl_id = self.ensembl_id
        else:
            ensembl_id = self.get_ensembl_id(target)
        variables = TargetAssociationQueryVariables.replace('{ensembl_id}', ensembl_id)
        variables = variables.replace("sort_by", sort_by)

        r = requests.post(self.otp_base_url, json={"query": TargetAssociationsQuery, "variables": variables})
        api_response = json.loads(r.text)

        return api_response

    def get_associated_targets(self, efo_id, sort_by: str = "score") -> Dict:
        """
        Get targets associated to a given disease in JSON format.
        """
        variables = DiseaseAssociationQueryVariables.replace('{efo_id}', efo_id)
        variables = variables.replace("sort_by", sort_by)

        r = requests.post(self.otp_base_url, json={"query": DiseaseAssociationsQuery, "variables": variables})
        api_response = json.loads(r.text)

        return api_response

    def rank_my_target(self, parent_disease: str, target: str = None, limit: int = 10):
        """
        For a given target and a parent_disease, find the rank of that target in each disease 
        from their associated targets.
        """
        rows_list = []
        detailed_info = []

        diseases_api_response = self.get_associated_diseases(target=target)
        diseases = diseases_api_response.get("data", {}).get("target", {}).get("associatedDiseases", {}).get("rows", [])
        descendants = self.get_descendants(disease_name=parent_disease)
        diseases = [disease for disease in diseases if disease.get("disease", {}).get("id") in descendants][:limit]

        for disease in tqdm(diseases, desc="Processing diseases"):
            disease_id = disease.get("disease", {}).get("id")
            disease_name = disease.get("disease", {}).get("name")

            targets_response = self.get_associated_targets(efo_id=disease_id)
            targets = targets_response.get("data", {}).get("disease", {}).get("associatedTargets", {}).get("rows", [])

            rank = None
            for index, target in enumerate(targets):
                if target.get("target", {}).get("id") == self.ensembl_id:
                    rank = index + 1
                    break

            if rank is not None and rank <= 500:
                rows_list.append({"Gene": self.target, "Disease": disease_name, "Rank": rank})
                detailed_info.append(f"Rank of {self.target} for disease {disease_name} ({disease_id}): {rank}")
            elif rank is None:
                detailed_info.append(f"Rank of {self.target} for disease {disease_name} ({disease_id}): Not Found")

        for info in detailed_info:
            print(info)
        print("--" * 57)
        print("--" * 57)

        if rows_list:
            df = pd.DataFrame(rows_list)
            df = df.sort_values(by='Rank')
            return df
        else:
            return "No diseases found where the target has a rank of 500 or less."

    # def get_ensembl_id(self, gene_name: str) -> str:
    #     """
    #     Get the ensembl ID of a gene.
    #     """
    #     url = f"https://rest.ensembl.org/lookup/symbol/homo_sapiens/{gene_name}?content-type=application/json"
    #     print(f"Getting ensembl id for {gene_name}...")
    #     response = requests.get(url)
    #     if response.ok:
    #         data = response.json()
    #         print(data.get('id'))
    #         return data.get('id')
    #     else:
    #         print("Error:", response.text)
    #         return None
    
    def get_ensembl_id(self,gene_name: str) -> Optional[str]:
        """
        Fetches the Ensembl ID with the latest version for a given target name.

        Args:
            gene_name (str): The target name (e.g., "PDE4C").

        Returns:
            Optional[str]: The Ensembl ID with the latest version, or None if not found.
        """
        # Base URLs for Ensembl REST APIs
        base_url_xrefs = f"https://rest.ensembl.org/xrefs/symbol/homo_sapiens/{gene_name}?content-type=application/json"
        base_url_lookup = "https://rest.ensembl.org/lookup/id/"

        try:
            # Fetch Ensembl IDs from the xrefs API
            response_xrefs = requests.get(base_url_xrefs)
            response_xrefs.raise_for_status()
            ensembl_ids = response_xrefs.json()

            # Ensure Ensembl IDs are present
            if not ensembl_ids or not isinstance(ensembl_ids, list):
                print("No Ensembl IDs found for the given target.")
                return None

            # Fetch details for each Ensembl ID using the lookup API
            latest_version_id = None
            latest_version = -1  # Initialize with a value lower than any possible version

            for record in ensembl_ids:
                if record.get("type") == "gene" and "id" in record:
                    ensembl_id = record["id"]
                    try:
                        response_lookup = requests.get(
                            f"{base_url_lookup}{ensembl_id}?content-type=application/json"
                        )
                        response_lookup.raise_for_status()
                        lookup_data = response_lookup.json()

                        # Extract version and compare to find the latest
                        version = lookup_data.get("version", -1)
                        if version > latest_version:
                            latest_version = version
                            latest_version_id = ensembl_id

                    except Exception as e:
                        print(f"Error fetching data for ID {ensembl_id}: {e}")
                        continue

            if latest_version_id:
                print(f"Ensembl ID with the latest version: {latest_version_id}")
                return latest_version_id
            else:
                print("No valid Ensembl ID with version found.")
                return None

        except Exception as e:
            print(f"Error fetching data from xrefs API: {e}")
            return None

    def get_hgnc_id(self, gene_name: str) -> str:
        """
        Get the HGNC_ID of a gene.
        """
        url = f"https://rest.ensembl.org/lookup/symbol/homo_sapiens/{gene_name}?content-type=application/json"
        print(f"Getting HGNC id for {gene_name}...")
        response = requests.get(url)
        if response.ok:
            data = response.json()
            description = data.get('description', '')
            if 'HGNC Symbol' in description:
                hgnc_symbol = description.split('HGNC Symbol;Acc:')[1].split(']')[0].strip()
                print(hgnc_symbol)
                return hgnc_symbol
            else:
                print("HGNC Symbol not found in the description.")
                return None
        else:
            print("Error:", response.text)
            return None

    def get_otg_traits(self, target: str = None) -> Dict:
        """
        Get traits reported by authors for a given target in JSON format.
        """
        if not target:
            ensembl_id = self.ensembl_id
        else:
            ensembl_id = self.get_ensembl_id(target)

        variables = """
        {"geneId": "{geneId}"}
        """
        variables = variables.replace("{geneId}", ensembl_id)

        r = requests.post(self.otg_base_url, json={"query": GenePageL2GPipelineQuery, "variables": variables})
        api_response = json.loads(r.text)

        return api_response

    def get_gwas_indications(self, parent_disease: str, target: str = None):
        """
        Get gwas reported traits for a given disease
        """
        if not target:
            target = self.target

        traits_api_response = self.get_otg_traits(target)
        l2g = traits_api_response.get("data", {}).get("studiesAndLeadVariantsForGeneByL2G", [])

        all_data = [{
            'study_id': item['study']['studyId'],
            'trait': item['study']['traitReported'],
            'efo_id': item['study']['traitEfos'],
            'l2g_score': item['yProbaModel'],
            'p_value': item['pval']
        } for item in l2g]

        descendants = self.get_descendants(disease_name=parent_disease)

        relevant_traits = []
        for data in all_data:
            efo_ids = data.get('efo_id', [])
            for efo_id in efo_ids:
                if efo_id in descendants:
                    relevant_traits.append({
                        'trait': data['trait'],
                        'l2g_score': data['l2g_score'],
                        'p_value': data['p_value'],
                        'study_id': data['study_id'],
                        'efo_id': efo_id
                    })
        df = pd.DataFrame(relevant_traits)
        if not df.empty:
            df = df.sort_values(by="l2g_score", ascending=False)
            df = df.reset_index(drop=True)
        else:
            return "Did not find any related traits"

        return df

    def get_target_ontology(self, target: str = None):
        """
        Get gene onotology for a given target
        """
        if target is not None:
            ensembl_id = self.get_ensembl_id(target)
        else:
            ensembl_id = self.ensembl_id
        variables = GeneOntologyVariables.replace('{ensembl_id}', ensembl_id)

        r = requests.post(self.otp_base_url, json={"query": GeneOntologyQuery, "variables": variables})
        api_response = json.loads(r.text)

        return api_response

    def get_target_description(self, target: str = None):
        """
        Get Description and Target Synonyms for a given target
        """
        if target is not None:
            ensembl_id = self.get_ensembl_id(target)
        else:
            ensembl_id = self.ensembl_id
        if not ensembl_id:
            print("Ensembl ID is None, check get_ensembl_id function.")
            return None
        variables = {"id": ensembl_id}

        r = requests.post(self.otp_base_url, json={"query": TargetDescriptionQuery, "variables": variables})
        api_response = json.loads(r.text)
        print(api_response)

        if 'errors' in api_response:
            print("Error in API response:", api_response['errors'])

        return api_response

    def get_mouse_phenotypes(self, target: str = None):
        """
        Get Mouse Phenotypes for a given target
        """
        if target is not None:
            ensembl_id = self.get_ensembl_id(target)
        else:
            ensembl_id = self.ensembl_id

        if not ensembl_id:
            print("Ensembl ID is None, check get_ensembl_id function.")
            return None

        print(f"Using Ensembl ID: {ensembl_id}")
        variables = {"ensemblId": ensembl_id}

        r = requests.post(self.otp_base_url, json={"query": MousePhenotypesQuery, "variables": variables})
        api_response = json.loads(r.text)

        if 'errors' in api_response:
            print("Error in API response:", api_response['errors'])

        return api_response

    def get_targetablitiy(self, disease_name: str = "monocyte count", target: str = None):
        """
        Get Target prioritaztion factor for a given target
        """
        associated_diseases = self.get_associated_diseases(target)
        # print(f"as dis: {associated_diseases}")
        if not associated_diseases['data']['target']['associatedDiseases']['rows']:
            print(f"No associated diseases found for target {target}.")
            return None

        most_associated_disease = associated_diseases['data']['target']['associatedDiseases']['rows'][0]
        disease_name = most_associated_disease['disease']['name']
        efo_id = most_associated_disease['disease']['id']

        print(f"Most associated disease: {disease_name} with EFO ID: {efo_id}")

        if disease_name:
            efo_id = self.get_efo_id(disease_name)
            if efo_id is None:
                print(f"No EFO ID found for {disease_name}.")
                return None
            efo_id = efo_id.replace(":", "_")
        else:
            efo_id = None

        if target:
            ensembl_id = self.get_ensembl_id(target)
        else:
            target = self.target
            ensembl_id = self.ensembl_id

        variables = TargetabilityVariables.replace('{efo_id}', efo_id).replace('{target}', target)

        r = requests.post(self.otp_base_url, json={"query": TargetabilityQuery, "variables": variables})
        api_response = json.loads(r.text)
        if 'errors' in api_response:
            print("Error in API response:", api_response['errors'])

        return api_response

    def get_tractability(self, target: str = None):
        """
        Get tractability for a given disease
        """
        if target is not None:
            ensembl_id = self.get_ensembl_id(target)
        else:
            ensembl_id = self.ensembl_id

        if not ensembl_id:
            print("Ensembl ID is None, check get_ensembl_id function.")
            return None

        print(f"Using Ensembl ID: {ensembl_id}")
        variables = {"id": ensembl_id}

        r = requests.post(self.otp_base_url, json={"query": TractabilityQuery, "variables": variables})
        api_response = json.loads(r.text)
        if 'errors' in api_response:
            print("Error in API response:", api_response['errors'])

        return api_response

    # def get_comparative_genomics(self, target:str = None):
    #     """
    #     Get Comparative genomics for a given target
    #     """
    #     if target is not None:
    #         ensembl_id = self.get_ensembl_id(target)
    #     else:
    #         ensembl_id = self.ensembl_id

    #     if not ensembl_id:
    #         print("Ensembl ID is None, check get_ensembl_id function.")
    #         return None

    #     print(f"Using Ensembl ID: {ensembl_id}")
    #     variables = {"ensemblId": ensembl_id}

    #     r = requests.post(self.otp_base_url, json={"query": CompGenomicsQuery, "variables": variables})
    #     api_response = json.loads(r.text)
    #     if 'errors' in api_response:
    #         print("Error in API response:", api_response['errors'])
    #     return api_response

    def get_paralogs(self, target: str = None):
        """
        Get Paralogs for the given target from flyrnai
        """
        gene_name = self.target if not target else target
        species_codes = {
            "human": "9606",
            "mouse": "10090",
            "worm": "6239",
            "zebrafish": "7955",
            "Chimpanzee": "9598",
            "Fruitfly": "7227",
            "Tropical clawed frog": "8364",
            "Domestic Pig": "9825",
            "Pig": "9823", 
            "Dog": "9615",
            "Guinea Pig": "10141",
            "Rabbit": "9986",
            "Rat": "10114",
            "Macaque": "9539",
            "Mosquito": "7165",
            "Yeast": "4932",
            "Fission Yeast": "4896",
            "Thale cress": "3702",
            "E. coli": "562"
        }
        session = requests.Session()

        # polite headers (some servers close connections for default "python-requests" UA)
        headers = {
            "User-Agent": "my-script/1.0 (your-email@domain.example)",
            "Referer": "https://www.flyrnai.org",
            # "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }

        # Retry strategy — allow retries for POST + GET and for common server errors / rate limits
        retry_strategy = Retry(
            total=5,
            backoff_factor=5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
            raise_on_status=False
        )
        def is_retryable_exception(e):
            return isinstance(e, (requests.exceptions.ConnectionError, ProtocolError))

        retry_strategy.retry_on_exception = is_retryable_exception
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        initial_url = "https://www.flyrnai.org/tools/paralogs/web/getTableJsonData"

        results = {}
        for species_name, species_code in species_codes.items():
            #print(f"Fetching data for {species_name} ({species_code}) with gene {gene_name}")
            # headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
            data = {
                "species": species_code,
                "id_type": "gene1",
                "genes": gene_name,
                "diopt": "1",
                "rpkm": "2"
            }
            # initial_response = requests.post(initial_url, headers=headers, data=data)
            try:
                initial_response = session.post(initial_url, headers=headers, data=data, timeout=30)
                initial_response.raise_for_status()

                # defensive: some servers return empty body and then close — treat that as an error
                if not initial_response.content:
                    raise requests.exceptions.ConnectionError("Empty response body from initial POST")

                initial_data = initial_response.json()
            except requests.exceptions.RequestException as e:
                # include useful debug info
                results[species_name] = {
                    "error": "Initial request failed",
                    "exception": str(e),
                    "status_code": getattr(e.response, "status_code", None)
                }
                # short sleep to avoid hammering
                time.sleep(1)
                continue
            except json.JSONDecodeError:
                results[species_name] = {
                    "error": "Failed to decode JSON from initial response",
                    "raw": resp.text[:1000]  # truncated for debugging
                }
                continue
            # if initial_response.status_code == 200:
            #     initial_data = initial_response.json()
            time.sleep(2)
            if 'run_id' in initial_data:
                run_id = initial_data['run_id']
                #print(f"Retrieved run_id {run_id}, fetching detailed data...")
                detailed_url = f"https://www.flyrnai.org/tools/paralogs/web/paralogDataSlice/{run_id}"
                # detailed_response = requests.get(detailed_url)
                detailed_response = session.get(detailed_url, headers=headers, timeout=30)
                if detailed_response.status_code == 200:
                    detailed_data = detailed_response.json()
                    results[species_name] = detailed_data
                else:
                    results[species_name] = {
                        'error': f"Failed to retrieve detailed data: Status Code {detailed_response.status_code}"}
            else:
                results[species_name] = {'error': 'No run_id found in initial data'}
            # else:
            #     results[species_name] = {
            #         'error': f"Failed to retrieve initial data: Status Code {initial_response.status_code}"}
            time.sleep(2)
        return results

    def get_differential_rna_and_protein_expression(self, target: str = None):
        if target is not None:
            ensembl_id = self.get_ensembl_id(target)
        else:
            ensembl_id = self.ensembl_id

        if not ensembl_id:
            print("Ensembl ID is None, check get_ensembl_id function.")
            return None

        print(f"Using Ensembl ID: {ensembl_id}")
        variables = {"id": ensembl_id}

        r = requests.post(self.otp_base_url, json={"query": DifferentialRNAQuery, "variables": variables})
        api_response = json.loads(r.text)
        if 'errors' in api_response:
            print("Error in API response:", api_response['errors'])
        return api_response

    def get_target_introduction(self, target: str = None):
        if target is not None:
            uniprot_id = self.get_uniprotkb_id(target)
        else:
            uniprot_id = self.uniprot_id

        if not uniprot_id:
            print("Uniprot ID not found.")
            return None

        fetch_url = f"{self.uniprot_base_url}{uniprot_id}"
        response = requests.get(fetch_url)

        if response.status_code != 200:
            print(f"Failed to retrieve data: HTTP {response.status_code}")
            return None

        try:
            api_response = response.json()
        except json.JSONDecodeError:
            print("Failed to decode the response")
            return None

        if 'errors' in api_response:
            print("Error in API response:", api_response['errors'])
            return None

        return api_response

    # def get_target_topology_features(self, target: str = None):
    #     if target is not None:
    #         uniprot_id = self.get_uniprotkb_id(target)
    #     else:
    #         uniprot_id = self.uniprot_id
    #     if not uniprot_id:
    #         print("Uniprot ID not found.")
    #         return None

    #     fetch_url = f"https://www.ebi.ac.uk/proteins/api/features?offset=0&size=100&accession={uniprot_id}"
    #     response = requests.get(fetch_url, headers={"Accept": "application/json"})
    #     if response.status_code != 200:
    #         print(f"Failed to retrieve data: HTTP {response.status_code}")
    #         return None

    #     try:
    #         api_response = response.json()
    #     except json.JSONDecodeError:
    #         print("Failed to decode the response")
    #         return None

    #     if 'errors' in api_response:
    #         print("Error in API response:", api_response['errors'])
    #         return None

    #     return api_response

  


    def get_target_topology_features(self, target: str = None):
        if target is not None:
            uniprot_id = self.get_uniprotkb_id(target)
        else:
            uniprot_id = self.uniprot_id
        if not uniprot_id:
            print("Uniprot ID not found.")
            return None

        fetch_url = f"https://www.ebi.ac.uk/proteins/api/features?offset=0&size=100&accession={uniprot_id}"

        headers = {
            "Accept": "application/json",
            "User-Agent": "my-script/1.0 (contact@example.com)"  # helps avoid silent drops
        }

        # Retry strategy (exponential backoff)
        retry_strategy = Retry(
            total=3,                # retry max 3 times
            backoff_factor=10,      # wait: 10s, 20s, 40s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        try:
            response = session.get(fetch_url, headers=headers, timeout=60)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

        try:
            api_response = response.json()
        except json.JSONDecodeError:
            print("Failed to decode the response")
            return None

        if isinstance(api_response, dict) and 'errors' in api_response:
            print("Error in API response:", api_response['errors'])
            return None

        return api_response

    def get_known_drugs(self, target: str = None):
        if target is not None:
            ensembl_id = self.get_ensembl_id(target)
        else:
            ensembl_id = self.ensembl_id

        if not ensembl_id:
            print("Ensembl ID is None, check get_ensembl_id function.")
            return None

        print(f"Using Ensembl ID: {ensembl_id}")
        variables = {"id": ensembl_id}

        r = requests.post(self.otp_base_url, json={"query": KnownDrugsQuery, "variables": variables})
        api_response = json.loads(r.text)
        if 'errors' in api_response:
            print("Error in API response:", api_response['errors'])
        return api_response

    def get_safety(self, target: str = None):
        if target is not None:
            ensembl_id = self.get_ensembl_id(target)
        else:
            ensembl_id = self.ensembl_id

        if not ensembl_id:
            print("Ensembl ID is None, check get_ensembl_id function.")
            return None

        print(f"Using Ensembl ID: {ensembl_id}")
        variables = {"ensemblId": ensembl_id}

        r = requests.post(self.otp_base_url, json={"query": SafetyQuery, "variables": variables})
        api_response = json.loads(r.text)
        if 'errors' in api_response:
            print("Error in API response:", api_response['errors'])
        return api_response

    def get_publications(self, target: str = None, disease_name=None):
        if target is not None:
            ensembl_id = self.get_ensembl_id(target)
        else:
            ensembl_id = self.ensembl_id

        efo_id = self.get_efo_id(disease_name)
        efo_id = efo_id.replace(":", "_")

        variables = PublicationVariables.replace('{ensembl_id}', ensembl_id)
        variables = variables.replace('{efo_id}', efo_id)

        r = requests.post(self.otp_base_url, json={"query": PublicationQuery, "variables": variables})
        api_response = json.loads(r.text)
        if 'errors' in api_response:
            print("Error in API response:", api_response['errors'])
        return api_response

    @staticmethod
    def get_disease_knowndrugs(disease_name: str = None):
        efo_id = get_efo_id(disease_name)
        efo_id = efo_id.replace(":", "_")

        variables = {"efoId": efo_id}
        otp_base_url = "https://api.platform.opentargets.org/api/v4/graphql"
        r = requests.post(otp_base_url, json={"query": DiseaseKnownDrugs, "variables": variables})
        api_response = json.loads(r.text)
        if 'errors' in api_response:
            print("Error in API response:", api_response['errors'])
        return api_response
