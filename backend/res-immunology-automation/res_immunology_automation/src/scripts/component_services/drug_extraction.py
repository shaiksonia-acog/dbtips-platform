import requests
import logging
import os
import json,time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry



OT_GRAPHQL_URL = "https://api.platform.opentargets.org/api/v4/graphql"
CHEMBL_API_URL = "https://www.ebi.ac.uk/chembl/api/data/target"

def chembl_sessions_request(url, headers=None, params=None):
    if not headers:
        headers = {
        "Accept": "application/json",
        "User-Agent": "my-script/1.0 (amani@aganitha.ai)"
        }

    # Configure retry strategy
    retry_strategy = Retry(
        total=5,                # total retries
        backoff_factor=2,       # wait time between retries (exponential backoff)
        status_forcelist=[429, 500, 502, 503, 504],  # retry on these errors
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    http = requests.Session()
    http.mount("https://", adapter)
    http.mount("http://", adapter)

    try:
        if params:
            response = http.get(url, headers=headers, params=params, timeout=30)
        else:
            response = http.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        return response


def get_ensg_from_symbol(gene_symbol: str) -> str:
    
    query = """
    query searchGene($queryString: String!) {
      search(queryString: $queryString) {
        hits {
          id
          name
        }
      }
    }
    """
    variables = {"queryString": gene_symbol}
    response = requests.post(OT_GRAPHQL_URL, json={"query": query, "variables": variables})
    response.raise_for_status()
    data = response.json()
    
    hits = data["data"]["search"]["hits"]
    if hits:
        print("hits: ", hits[0]["id"])
        return hits[0]["id"]  # ENSG ID
    else:
        return None

def fetch_uniprot_from_ot(ensembl_id: str):
    """
    Fetch UniProt IDs from Open Targets given Ensembl ID.
    Returns a list of UniProt accessions.
    """
    query = f"""
    {{
      target(ensemblId: "{ensembl_id}") {{
        approvedSymbol
        id
        proteinIds {{
          id
          source
        }}
      }}
    }}
    """
    response = requests.post(OT_GRAPHQL_URL, json={"query": query})
    response.raise_for_status()
    data = response.json()
    print(f"datas: {data}")
    if "errors" in data:
        raise ValueError(f"OT error: {data['errors']}")

    protein_ids = data.get("data", {}).get("target", {}).get("proteinIds", [])
    if not protein_ids:
        return None
    
    # Prefer Swiss-Prot
    swissprot = next((p for p in protein_ids if p["source"] == "uniprot_swissprot"), None)
    if swissprot:
        print(swissprot)
        return swissprot
    
    # Fallback: TrEMBL
    trembl = next((p for p in protein_ids if p["source"] == "uniprot_trembl"), None)
    return trembl


def fetch_chembl_from_uniprot(uniprot_id: str):
    """
    Fetch ChEMBL target IDs for a given UniProt accession.
    Returns a list of ChEMBL IDs (could be empty if no mapping).
    """
    url = f"{CHEMBL_API_URL}/search.json?q={uniprot_id}"
    # response = requests.get(url)
    try:
        response = chembl_sessions_request(url)
        response.raise_for_status()
        # print("response: ", response.content)
        data = response.json()
        chembl_ids = [t["target_chembl_id"] for t in data.get("targets", [])]
        print("chembl_ids: ", chembl_ids)
        return chembl_ids
    except Exception as e:
        return []


def map_target_to_chembl(target: str):
    """
    Full pipeline:
    - Take gene symbol (e.g., BRCA2)
    - Resolve to Ensembl ID
    - Fetch UniProt IDs from Open Targets
    - Map each UniProt ID to ChEMBL IDs
    Returns dict of UniProt -> ChEMBL mappings
    """
    ensembl_id = get_ensg_from_symbol(target)
    uniprot_id_dict = fetch_uniprot_from_ot(ensembl_id)
    result = {}
    if not uniprot_id_dict or 'id' not in uniprot_id_dict:
        return []
    chembl_ids = fetch_chembl_from_uniprot(uniprot_id_dict['id'])
    
    return chembl_ids

def get_target_chembl_id(target_input):
    """
    Given a gene symbol or ChEMBL target ID, returns the ChEMBL target ID.
    """
    if target_input.upper().startswith("CHEMBL"):
        return target_input
    url = f"https://www.ebi.ac.uk/chembl/api/data/target.json?target_components__target_component_synonyms__component_synonym__iexact={target_input}&limit=1"
    # resp = requests.get(url)
    resp = chembl_sessions_request(url)
    if resp.status_code == 200:
        targets = resp.json().get("targets", [])
        if targets:
            return targets[0]["target_chembl_id"]
    return None

def get_drugs_for_target(target_chembl_id):
    """
    Returns a list of drugs (dicts) that act on the given target (from ChEMBL).
    """
    url = f"https://www.ebi.ac.uk/chembl/api/data/mechanism.json?target_chembl_id={target_chembl_id}&limit=1000"
    # resp = requests.get(url)
    resp = chembl_sessions_request(url)
    drugs = []
    time.sleep(1)
    if resp.status_code == 200:
        seen = set()
        for mech in resp.json().get("mechanisms", []):
            mol = mech.get("molecule_chembl_id")
            if mol and mol not in seen:
                seen.add(mol)
                # Optionally fetch pref_name
                mol_url = f"https://www.ebi.ac.uk/chembl/api/data/molecule/{mol}.json"
                # mol_resp = requests.get(mol_url)
                mol_resp = chembl_sessions_request(mol_url)
                pref_name = mol_resp.json().get("pref_name") if mol_resp.status_code == 200 else None
                print("drug name: ", pref_name)
                drugs.append({"molecule_chembl_id": mol, "pref_name": pref_name})
                time.sleep(1)
    return drugs

def fetch_molecule_type(chembl_id):
    """
    Given a ChEMBL ID, fetches the molecule type (e.g., 'Small molecule', 'Protein').
    Returns 'NA' if not found or on error.
    """
    url = f"https://www.ebi.ac.uk/chembl/api/data/molecule/{chembl_id}.json"
    # resp = requests.get(url)
    resp = chembl_sessions_request(url)
    if resp.status_code == 200:
        return resp.json().get("molecule_type", "NA")
    return "NA"

def fetch_moa_targets_for_ids(chembl_ids, filter_target=None):
    """
    For a list of ChEMBL IDs, fetches mechanism of action (MoA) and target information.
    If filter_target is set, only returns mechanisms for that target.
    Returns a list of tuples: (chembl_id, mechanism_of_action, target_symbol).
    """
    mechanisms = []
    for chembl_id in chembl_ids:
        url = f"https://www.ebi.ac.uk/chembl/api/data/mechanism.json?molecule_chembl_id={chembl_id}&limit=1000"
        # resp = requests.get(url)
        resp = chembl_sessions_request(url)
        if resp.status_code == 200:
            for mech in resp.json().get("mechanisms", []):
                tgt_id = mech.get("target_chembl_id")
                if filter_target and tgt_id != filter_target:
                    continue
                moa = mech.get("mechanism_of_action") or "NA"
                tgt_symbol = fetch_target_symbol(tgt_id) if tgt_id else "NA"
                mechanisms.append((chembl_id, moa, tgt_symbol))
    return mechanisms

def fetch_target_symbol(target_chembl_id):
    """
    Given a ChEMBL target ID, fetches the gene symbol (GENE_SYMBOL) for the target.
    Falls back to the preferred name if no gene symbol is found.
    """
    url = f"https://www.ebi.ac.uk/chembl/api/data/target/{target_chembl_id}.json"
    # resp = requests.get(url)
    resp = chembl_sessions_request(url)
    if resp.status_code == 200:
        target = resp.json()
        for comp in target.get("target_components", []):
            for syn in comp.get("target_component_synonyms", []):
                if syn.get("syn_type") == "GENE_SYMBOL":
                    return syn.get("component_synonym", "NA")
        return target.get("pref_name", "NA")
    return "NA"

def extract_moa_keyword(moa):
    """
    Extracts a keyword from the MoA string (e.g., 'inhibitor', 'agonist').
    """
    for kw in ["inhibitor", "agonist", "antagonist", "modulator", "blocker", "activator"]:
        if kw in moa.lower():
            return kw
    return moa.split()[-1] if moa else "NA"

def get_moa_short(moa_targets):
    """
    For a list of (chembl_id, moa, target) tuples, returns a short MoA string.
    Format: 'GENE_SYMBOL: keyword' for each pair, comma-separated for multiple pairs.
    Returns 'NA' if no valid pairs are found.
    """
    short_blocks = []
    for chembl_id, moa, target in moa_targets:
        if target and target != "NA":
            moa_kw = extract_moa_keyword(moa)
            short_blocks.append(f"{target}: {moa_kw}")
    return ", ".join(short_blocks) if short_blocks else "NA"

def get_indications_for_drug(chembl_id):
    """
    Returns a list of indication dicts for a given drug ChEMBL ID.
    Each dict contains at least 'indication_name' and 'max_phase_for_ind'.
    """
    url = f"https://www.ebi.ac.uk/chembl/api/data/drug_indication.json?molecule_chembl_id={chembl_id}&limit=1000"
    # resp = requests.get(url)
    resp = chembl_sessions_request(url)
    indications = []
    if resp.status_code == 200:
        for ind in resp.json().get("drug_indications", []):
            # Use efo_term or mesh_heading as indication name
            name = (ind.get("efo_term") or ind.get("mesh_heading") or "NA")
            indications.append({
                "indication_name": name,
                "max_phase_for_ind": ind.get("max_phase_for_ind", "NA")
            })
    return indications

def get_approval_status_from_indication(ind):
    """
    Returns 'Approved' if max_phase_for_ind is 4, else 'Not Approved' or 'NA'.
    """
    try:
        if float(ind.get("max_phase_for_ind", 0)) == 4:
            return "Approved"
        else:
            return "Not Approved"
    except Exception:
        return "NA"

def get_drug_synonyms(chembl_id):
    """
    Returns a list of all synonyms (including pref_name) for a given ChEMBL drug ID.
    """
    url = f"https://www.ebi.ac.uk/chembl/api/data/molecule/{chembl_id}.json"
    # resp = requests.get(url)
    resp = chembl_sessions_request(url)
    names = set()
    if resp.status_code == 200:
        data = resp.json()
        if data.get("pref_name"):
            names.add(data["pref_name"])
        for syn in data.get("molecule_synonyms", []):
            if syn.get("synonym"):
                names.add(syn["synonym"])
            if syn.get("molecule_synonym"):
                names.add(syn["molecule_synonym"])
    return list(names)

class DrugExtractor:
    def __init__(self, llm_client, cache_dir="cached_data_json/llm_drug_extraction"):
        self.llm_client = llm_client
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, nct_id: str) -> str:
        """Returns the file path for a given nct_id"""
        return os.path.join(self.cache_dir, f"{nct_id}.json")

    def _load_from_cache(self, nct_id: str) -> list:
        """Load cached result for given nct_id if it exists"""
        cache_file = self._get_cache_path(nct_id)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                    return data.get("extracted_drugs", [])
            except Exception as e:
                logging.warning(f"Failed to load cache for {nct_id}: {e}")
        return None

    def _save_to_cache(self, nct_id: str, drugs: list):
        """Save extracted drugs to cache for given nct_id"""
        cache_file = self._get_cache_path(nct_id)
        try:
            with open(cache_file, "w") as f:
                json.dump({
                    "nct_id": nct_id,
                    "extracted_drugs": drugs
                }, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save cache for {nct_id}: {e}")


    def extract_drug_names(self, intervention_data):
        """
        Extracts clean drug names from trial intervention strings using LLM.
        Uses cache to avoid re-processing the same NCT ID.
        Limits to first 100 trials for testing.
        """
        prompt_template = (
                    '''
            You are a clinical-trials expert whose sole task is to extract CORE DRUG NAMES from a free-text list of interventions.

            Rules:
            1. Return **only** the exact, core drug name(s), separated by commas.
            2. Exclude all dosage, administration routes/forms (e.g., injected, inhaled, oral, topical, MDI, powder, patch, spray, infusion, intravenous, subcutaneous, intramuscular, nasal), formulation details, **stereochemical descriptors (e.g., 'racemic', 'levo', 'dex', 'D-'), and common salt or ester forms (e.g., 'tartrate', 'hydrochloride', 'acetate', 'fumarate', 'succinate', 'phosphate', 'sodium', 'potassium')**.
            3. Do **not** return “placebo” or vehicle controls.
            4. Do **not** extract generic drug-class terms (e.g. “corticosteroid(s)”, “NSAIDs”, “antibiotics”, "integrin antagonist")—only specific, named molecules. Exclude natural products, supplements, or herbal extracts.
            5. If a term is purely a route/formulation (e.g. “inhaled insulin”) or a non-drug formulation (e.g. “silver cream”), **do not** extract it.
            6. If **no** core drug name remains after filtering, output a completely empty string (no characters).
            7. If a single intervention description refers to a combination of multiple core drug names (e.g., linked by '/', '+', 'and', or listed together), extract *each* core drug name individually.

            Examples:

            Example 1
            input:
            VC005 low dose group, VC005 high dose group, VC005 Placebo group
            output:
            VC005

            Example 2
            input:
            CGB-500 with 0.5% tofacitinib, CGB-500 Ointment with 1% tofacitinib, Vehicle (placebo)
            output:
            CGB-500, tofacitinib

            Example 3
            input:
            Dual Integrin Antagonist
            output:
            

            Example 4
            input:
            Placebo, Levalbuterol tartrate MDI, racemic albuterol MDI
            output:
            Levalbuterol, albuterol

            Example 5
            input:
            injected insulin, inhaled insulin, Insulin aspart, Human Insulin Inhalation Powder
            output:
            insulin aspart

            Example 6
            input:
            injected insulin, inhaled insulin, topical corticosteroids, Human Insulin Inhalation Powder, corticosteroids, Borage oil, Ginkgo biloba
            output:
            

            Example 7
            input:
            Budesonide/Formoterol pMDI, Salbutamol rescue inhaler
            output:
            budesonide, formoterol, salbutamol

            Example 8
            input:
            DrugX + DrugY combination tablet
            output:
            DrugX, DrugY
            '''
        )

        all_results = []
        for idx, row in enumerate(intervention_data, 1): 
            nct_id = row.get("nct_id")
            drug_name_str = row.get("drug_names", "")
            logging.info(f"Processing row {idx}/{len(intervention_data)}: nct_id {nct_id}")

            # Step 1: Try loading from cache
            cached_drugs = self._load_from_cache(nct_id)
            drugs = []

            if cached_drugs is not None:
                logging.info(f"Loaded from cache: {nct_id}")
                drugs = cached_drugs
            else:
                # Step 2: If not cached, run LLM extraction
                prompt = prompt_template + f"\ninput:\n{drug_name_str}\n\noutput:"
                response = self.llm_client.extract_drugs(prompt)
                drugs = [d.strip() for d in response.split(',') if d.strip()]
                self._save_to_cache(nct_id, drugs)

            #  Step 3: Preserve original fields + add drug info
            enriched_row = dict(row)  # Copy all original fields (e.g., status, phase)
            enriched_row["original_drug_names"] = drug_name_str
            enriched_row["extracted_drugs"] = drugs
            all_results.append(enriched_row)

        logging.info(f"All rows processed. Total extracted: {len(all_results)}")
        return all_results
