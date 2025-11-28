import requests
import pandas as pd
from io import BytesIO
import urllib.parse
from bs4 import BeautifulSoup
import re, os, csv
from collections import defaultdict
from typing import List, Dict, Any

cache_dir= "/app/res-immunology-automation/res_immunology_automation/src/scripts/cached_data_json"
mirna_families_file_path = f"{cache_dir}/targetscan_mirna_families.csv"

class TargetScanError(Exception):
    """Custom exception for TargetScan related errors."""
    pass


def fetch_targetscan_families() -> str | None:
    """
    Fetches the miRNA family data from TargetScan, extracts the two specified 
    columns, and saves the result to a CSV file using robust header matching.
    """
    url = "https://www.targetscan.org/cgi-bin/targetscan/vert_80/mirna_families.cgi"
    
    params = {
        "db": "vert_80",
        "species": "Human"
    }

    headers = {
        # Mimic a real browser
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # 💡 CORRECTED DEFINITION: Use clean, simple strings for dictionary keys/lookups
    REQUIRED_COLUMNS = {
        "Human microRNA family": "Family Name",  # Internal key maps to CSV header
        "MiRBase Accessions": "MiRBase Accessions" # Clean internal key
    }
    
    # Define the unique prefixes for robust matching against the headers_list
    HUMAN_FAMILY_PREFIX_MATCH = "Human microRNA family"
    MIRBASE_PREFIX_MATCH = "miRBase miRNAs (all species) in this family"


    try:
        print("Downloading Entries Data from TargetScan...")
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status() 

        soup = BeautifulSoup(response.text, 'html.parser')

        table = soup.find('table', id='restable') 
        
        if not table:
            raise TargetScanError("Could not find the main results table (id='restable') on the page.")

        header_row = table.find('tr')
        if not header_row:
             raise TargetScanError("Could not find table header row.")
             
        # Get all header texts (cleaned of tags and stripped)
        headers_list = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]

        column_indices: Dict[str, int] = {}
        
        # 💡 CORRECTED MAPPING LOGIC: Use partial matching for both headers
        for i, header_text in enumerate(headers_list):
            if header_text.startswith(HUMAN_FAMILY_PREFIX_MATCH):
                # Store index using the clean internal key 'Human microRNA family'
                column_indices[HUMAN_FAMILY_PREFIX_MATCH] = i
                
            elif header_text.startswith(MIRBASE_PREFIX_MATCH):
                # Store index using the clean internal key 'MiRBase Accessions'
                column_indices["MiRBase Accessions"] = i

        # -------------------------------------------------------------
        # Verify both columns were found
        
        # Check if the internal keys for the required columns exist in column_indices
        if HUMAN_FAMILY_PREFIX_MATCH not in column_indices or "MiRBase Accessions" not in column_indices:
            
            # This complex error checking is needed because we use simple keys for storage:
            found_keys = list(column_indices.keys())
            if HUMAN_FAMILY_PREFIX_MATCH not in found_keys:
                raise TargetScanError(f"Missing expected column: '{HUMAN_FAMILY_PREFIX_MATCH}' (could not be matched).")
            if "MiRBase Accessions" not in found_keys:
                raise TargetScanError(f"Missing expected column: '{MIRBASE_PREFIX_MATCH}' (could not be matched).")

        # -------------------------------------------------------------
        
        # 5. Extract data row by row
        data_list: List[Dict[str, str]] = []
        rows = table.find_all('tr')[1:] 

        # Define the exact keys for lookup/output
        OUTPUT_KEYS = {
            HUMAN_FAMILY_PREFIX_MATCH: REQUIRED_COLUMNS[HUMAN_FAMILY_PREFIX_MATCH],
            "MiRBase Accessions": REQUIRED_COLUMNS["MiRBase Accessions"] 
        }

        for row in rows:
            cols = row.find_all('td')
            if cols:
                record = {}
                for required_header_key, output_key in OUTPUT_KEYS.items():
                    col_index = column_indices[required_header_key]

                    if col_index < len(cols):
                        record[output_key] = cols[col_index].get_text(strip=True)
                    else:
                        record[output_key] = "N/A"
                
                data_list.append(record)

        # 6. Create DataFrame and Save to CSV
        if not data_list:
            print("No data extracted from the table rows.")
            return None

        df = pd.DataFrame(data_list)
        df.to_csv(mirna_families_file_path, index=False)
        
        print(f"Data saved to CSV file: '{mirna_families_file_path}'")
        
        return mirna_families_file_path
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return None
    except TargetScanError as e:
        print(f"TargetScan Data Error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def get_mir_family(mir_name: str):
    """Identify standardized miRNA family name from various input formats."""
    if not mir_name:
        return None

    # 1. Normalize to lowercase
    mir = mir_name.lower()

    # 2. Remove species prefix (hsa-, mmu-) BUT keep 'mir-' 
    # Logic: Match 3-4 letters + hyphen ONLY if followed by 'mir' or 'let'
    mir = re.sub(r'^[a-z]{3,4}-(?=mir|let)', '', mir)

    # 3. Remove arm suffixes (-5p, -3p)
    mir = re.sub(r'-(5p|3p)$', '', mir)

    # 4. Remove letter suffixes from the number (e.g., mir-33a -> mir-33)
    # Using [a-z]+ handles single 'a' or double 'ab' suffixes
    mir = re.sub(r'([0-9]+)[a-z]+$', r'\1', mir)

    # 5. Extract and format
    # Matches 'mir' followed optionally by hyphen/space, then number
    m = re.match(r'(mir|let)[-\s]?([0-9]+)', mir)
    
    if not m:
        return None

    # Return standardized format "mir-NUMBER"
    return f"{m.group(1)}-{m.group(2)}"

def fetch_mirna_entries(target: str, target_scan_file_path: str):
    """Fetch miRNA family entries from cached TargetScan families file."""
    matched_families = []
    # Loaded entries from TargetScan file
    with open(target_scan_file_path, "r") as f:
        reader = csv.DictReader(f)
        families = [row['Family Name'] for row in reader if any(row.values())]
    
    # Identify Target Family
    targets_to_be_matched = list({target, get_mir_family(target)})
    print("Target and its family:", targets_to_be_matched)
    
    # Identify matching families from targetscan file
    for family in set(families): # Use set(families) if there might be duplicates in the file
        # Check if the current family entry starts with ANY of the target strings
        for tar in targets_to_be_matched:
            if any(match_targ in family.lower() for match_targ in [tar.lower()+"-5p", tar.lower()+"-3p"]):
                matched_families.append(family)
    
    return matched_families


def download_targetscan_file(target_with_loc: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Download a TargetScan predicted targets Excel file, extract required fields, 
    and categorize the results by the specific miRNA found in the 'Representative miRNA' column.
    
    Returns:
        Dict[str, List[Dict[str, Any]]]: Dictionary where keys are unique miRNA names (e.g., 'mir-33-3p')
                                         and values are lists of target records.
    """
    url = f"https://www.targetscan.org/vert_80/temp/TargetScan8.0__{target_with_loc}.Human.predicted_targets.xlsx"
    
    # TargetScan Excel column names
    required_columns = {
        "Representative miRNA": "Representative miRNA",
        "Target gene": "Representative Target",
        "Gene name": "Gene name",
    }
    extra_columns = [
        "Cumulative weighted context++ score",
        "Aggregate PCT"
    ]
    
    # The actual column containing the specific miRNA (e.g., mir-33-3p) is embedded in the first column.
    # We must include it to group the results later.
    mirna_column = "Representative miRNA" # This column contains all specific miRNAs for grouping.

    # 1️⃣ Download the file
    try:
        response = requests.get(url, timeout=15)
    except requests.RequestException as e:
        raise TargetScanError(f"Network error while downloading file: {e}")

    if response.status_code != 200:
        raise TargetScanError(f"Failed to download file. HTTP status: {response.status_code}")

    # 2️⃣ Validate content type (TargetScan sometimes returns HTML error pages)
    content_type = response.headers.get("Content-Type", "")
    if "application" not in content_type and "excel" not in content_type:
        raise TargetScanError("URL did not return a valid Excel file. "
                              "Probably this miRNA has no predicted file on TargetScan.")

    # 3️⃣ Try loading Excel
    try:
        df = pd.read_excel(BytesIO(response.content))
    except Exception as e:
        raise TargetScanError(f"Downloaded file is not a valid Excel file: {e}")

    # Clean column names
    df.columns = (
        df.columns
        .str.replace('"', '', regex=False)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    # 4️⃣ Validate required columns
    all_needed_cols = list(required_columns.keys()) + extra_columns
    missing = [col for col in all_needed_cols if col not in df.columns]
    if missing:
        raise TargetScanError(f"Missing expected columns in the file: {missing}")

    # 5️⃣ Extract needed fields
    final_df = df[all_needed_cols].rename(columns=required_columns)

    # 6️⃣ Add UTR link
    def make_utr_link(row):
        # NOTE: The 'Representative miRNA' column usually contains the specific miRNA name 
        # (e.g., hsa-miR-33-3p) which is needed for the UTR link.
        gene = urllib.parse.quote(str(row["Representative Target"]))
        mir = urllib.parse.quote(str(row[mirna_column])) # Use the specific miRNA name here
        return f"https://www.targetscan.org/cgi-bin/targetscan/vert_80/targetscan.cgi?utr={gene}&mir={mir}"

    final_df["Link to sites in UTR"] = final_df.apply(make_utr_link, axis=1)
    
    # Fill NA/NaN values in object (string) columns with empty string
    final_df = final_df.fillna({col: "" for col in final_df.select_dtypes(include='object').columns})

    ## 7️⃣ Categorize and Return Data by Unique miRNA 🚀
    
    # Convert the entire DataFrame into a list of dictionaries (records)
    all_records = final_df.to_dict(orient="records")
    
    # Use defaultdict to group the records
    categorized_data = defaultdict(list)

    for record in all_records:
        # The key for grouping is the specific miRNA name from the source column
        mirna_key = record[mirna_column]
        
        # Add the record to the list corresponding to its miRNA key
        categorized_data[mirna_key].append(record)

    # Convert defaultdict back to a standard dict for the final return
    return dict(categorized_data)


def get_target_predictions_for_all_locs(target: str):
    target_pred = defaultdict(list)

    #step1: download target scan family file if not exists
    print("mirna_families_file_path:", mirna_families_file_path)
    if not os.path.exists(mirna_families_file_path):
        print("Downloading TargetScan families file...")
        families_file = fetch_targetscan_families()
        print("Downloaded families file:", families_file)
        if not families_file:
            print("Could not fetch TargetScan families file.")
            return target_pred
        
    #Step2: filter miRNA entries from TargetScan families file for given target
    mirna_entries = fetch_mirna_entries(target, mirna_families_file_path)
    print("Matched entries:", mirna_entries)
    if not mirna_entries:
        print(f"No miRNA family found for target: {target}")
        return target_pred

    for entry in mirna_entries:
        # normalize entry for URL
        entry = entry.replace("/","_")
        try:
            print(f"Downloading file for TargetScan entry: {entry}")
            dict_response = download_targetscan_file(entry)
            
            # Collect predictions for both 5p and 3p locations for given target
            for i in ["5p", "3p"]:
                try:
                    target_with_loc = target.lower().replace("mir", "hsa-miR") + f"-{i}"
                    target_pred[i].extend(dict_response[target_with_loc])
                except KeyError:
                    target_pred[i].extend([])
        
        except TargetScanError as e:
            print(f"ERROR: {e}")
            continue

    return target_pred

def extract_seq_of_prime_loc(seq: str):

    # Find continuous uppercase stretches
    blocks = [(m.group(), m.start(), m.end()) for m in re.finditer(r'[A-Z]+', seq)]

    result = {}

    if blocks:
        # 5p = first uppercase block
        five_p_seq, five_p_start, five_p_end = blocks[0]
        result["5p"] = {
            "sequence": f"{five_p_start + 1} - {five_p_seq} - {five_p_end}",
            "start": five_p_start + 1,   # convert to 1-based indexing
            "end": five_p_end
        }

    if len(blocks) > 1:
        # 3p = second uppercase block
        three_p_seq, three_p_start, three_p_end = blocks[1]
        result["3p"] = {
            "sequence": f"{three_p_start + 1} - {three_p_seq} - {three_p_end}",
            "start": three_p_start + 1,
            "end": three_p_end
        }

    return result

def search_gene_id(gene_query: str, species: str = "Homo sapiens"):
    """
    Search NCBI Gene using flexible miRNA query + species filter.
    Works even if the user enters non-official symbols like 'mir-33a'.
    """
    query = f'({gene_query}[Gene Name]) AND "{species}"[Organism]'

    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "gene",
        "term": query,
        "retmode": "json",
        "sortby": "relevance"
    }

    r = requests.get(url, params=params)
    r.raise_for_status()
    ids = r.json()["esearchresult"]["idlist"]
    print("ids: ", ids)
    if not ids:
        raise ValueError(f"No NCBI Gene found for query='{gene_query}' in {species}")

    return ids[0]   # return top hit


def fetch_gene_summary(gene_id: str):
    """Retrieve eSummary for a gene id."""
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {"db": "gene", "id": gene_id, "retmode": "xml"}

    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.content


def extract_mirbase_url(gene_summary):
    """Extract first miRBase link present in 'otherlinks' or 'dblinks'."""
    soup = BeautifulSoup(gene_summary, "xml")
    for dbtag in soup.find_all("Dbtag"):
        dbname = dbtag.find("Dbtag_db")
        if dbname and dbname.get_text() == "miRBase":
            accession = dbtag.find("Dbtag_tag").find("Object-id").find("Object-id_str").get_text()
            mirbase_url = f"https://mirbase.org/hairpin/{accession}?acc={accession}"
            print(mirbase_url)
            return mirbase_url
    raise ValueError("miRBase link not found in NCBI Gene data.")


def parse_mirbase_page(url: str):
    """Extract sequence, structure, RNAcentral link from miRBase HTML."""
    r = requests.get(url)
    r.raise_for_status()
    with open("mirbase_page.html", "w") as f:
        f.write(r.text)  # For debugging purposes

    soup = BeautifulSoup(r.text, "html.parser")

    seq = None
    seq_msa = None
    struct = None
    rnacentral = None

    # Sequence
    seq_div_tag = soup.find("div", id="hairpinSequence")
    if seq_div_tag:
        span_tags = seq_div_tag.find_all('span')
        for span in span_tags:
            text = span.get_text(strip=True)

            # Sequence: contains A/U/C/G (case-insensitive)
            if any(nt in text.upper() for nt in ["A", "U", "C", "G"]):
                seq = text

            # Structure / MSA: contains '(' or '.'
            elif "(" in text or "." in text:
                seq_msa = text
    # Structure
    
    struct_tag = soup.find("pre", class_="hairpin frame")
    if struct_tag:
        struct = struct_tag.get_text(strip=True)

    # RNAcentral link
    for a in soup.find_all("a", href=True):
        if "rnacentral.org/rna" in a["href"]:
            rnacentral = a["href"]
            break

    return {
        "sequence": seq,
        "sequence_msa": seq_msa,
        "structure": struct,
        "rnacentral_url": rnacentral,
    }


def fetch_mirna_info(gene_query: str):
    """Entire pipeline: search → summary → miRBase page → extract info."""
    gene_id = search_gene_id(gene_query)
    summary = fetch_gene_summary(gene_id)
    mirbase_url = extract_mirbase_url(summary)
    details = parse_mirbase_page(mirbase_url)
    prime_seq = extract_seq_of_prime_loc(details["sequence"])
    details.update(prime_seq)

    return {
        "gene_id": gene_id,
        "mirbase_url": mirbase_url,
        **details
    }

# ---------------------
# Example usage
# ---------------------

if __name__ == "__main__":
    # for target predictions
    target = "mir-33a"
    # fetch_targetscan_families()
    results = get_target_predictions_for_all_locs(target)
    with open("target_predictions_33a.json", "w") as f:
        import json
        json.dump(results, f, indent=2)

    # for miRNA info
    # result = fetch_mirna_info("mir-33b")
    # print(result)


    
