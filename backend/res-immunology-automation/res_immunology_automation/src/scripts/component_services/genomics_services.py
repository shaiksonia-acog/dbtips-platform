import requests
from datetime import datetime
import time

def get_child_traits(trait_id):
    """
    Get all child trait IDs for a given trait using the trait endpoint.
    """
    try:
        url = f"https://www.pgscatalog.org/rest/trait/{trait_id}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            # Get child trait IDs from child_associated_pgs_ids or child_traits
            child_traits = {}
            
            # Also check for child_traits field
            if 'child_traits' in data:
                for child in data.get('child_traits', []):
                    child_id = child.get('id')
                    if child_id and child_id not in child_traits:
                        child_traits[child_id] = child.get('label', '')
            
            return child_traits
        else:
            print(f"Warning: Could not fetch trait details for {trait_id}")
            return []
    except Exception as e:
        print(f"Error fetching child traits: {e}")
        return []


def fetch_pgs_data_for_single_trait(trait_id):
    """
    Fetch PGS data for a single trait ID (no child traits).
    """
    base_url = "https://www.pgscatalog.org/rest/score/search"
    output = []
    params = {'trait_id': trait_id}
    current_url = base_url
    page_count = 1
    
    while current_url:
        # First request uses params, subsequent use the full 'next' URL
        if page_count == 1:
            response = requests.get(current_url, params=params)
        else:
            response = requests.get(current_url)
        
        # Check if the response is successful
        if response.status_code != 200:
            print(f"  Error: Unable to fetch data (Status Code: {response.status_code})")
            break
        
        data = response.json()
        results = data.get('results', [])
        
        # If no results, we're done
        if not results:
            break
        
        # Process each result
        for result in results:
            if result:
                pgs_id = result.get('id', '')
                pgs_name = result.get('name', '')
                pgs_publication = result.get('publication', {})
                pgs_publication_id = pgs_publication.get('id', '')
                pgs_publication_first_author = pgs_publication.get('firstauthor', '')
                pgs_publication_journal = pgs_publication.get('journal', '')
                
                # Handle date parsing safely
                date_pub = pgs_publication.get('date_publication', '1900-01-01')
                try:
                    pgs_publication_year = datetime.strptime(date_pub, '%Y-%m-%d').year
                except:
                    pgs_publication_year = 1900
                
                pgs_reported_trait = result.get('trait_reported', '')
                pgs_number_of_variants = result.get('variants_number', 0)
                pgs_scoring_file = result.get('ftp_scoring_file', '')
                pgs_ancestry_distribution = result.get('ancestry_distribution', {})
                
                output.append({
                    'PGS ID': pgs_id,
                    'PGS Name': pgs_name,
                    'PGS Publication ID': pgs_publication_id,
                    'PGS Publication First Author': pgs_publication_first_author,
                    'PGS Publication Journal': pgs_publication_journal,
                    'PGS Publication Year': pgs_publication_year,
                    'PGS Reported Trait': pgs_reported_trait,
                    'PGS Number of Variants': pgs_number_of_variants,
                    'PGS Scoring File': pgs_scoring_file,
                    'PGS Ancestry Distribution': pgs_ancestry_distribution,
                    'Source Trait ID': trait_id  # Track which trait this came from
                })
        
        # Get the next page URL
        current_url = data.get('next')
        
        if current_url:
            page_count += 1
            time.sleep(0.3)
    
    return output


def fetch_pgs_data(disease_name, trait_id, include_child_traits=True):
    """
    Fetch ALL PGS data for a trait ID, including child traits if specified.
    This mimics the behavior of the PGS Catalog UI.
    
    Args:
        trait_id: The EFO trait ID (e.g., 'EFO_0009690')
        include_child_traits: If True, also fetch data for child traits (default: True)
    
    Returns:
        List of dictionaries containing PGS data
    """
    try:
        print(f"Fetching PGS data for trait: {trait_id}")
        print("-" * 60)
        
        all_output = {}
        trait_ids_to_fetch = {trait_id: disease_name}

        
        # Get child traits if requested
        if include_child_traits:
            print("Fetching child traits...")
            child_traits = get_child_traits(trait_id)
            if child_traits:
                print(f"Found {len(child_traits)} child trait(s): {', '.join(child_traits)}")
                trait_ids_to_fetch.update(child_traits)
                print(f"Total traits to fetch (including parent): {trait_ids_to_fetch}")
            else:
                print("No child traits found.")
            print("-" * 60)
        
        # Fetch data for each trait
        # for idx, tid in enumerate(trait_ids_to_fetch, 1):
        for idx, (tid, trait) in enumerate(trait_ids_to_fetch.items(), 1):

            trait_type = "Parent trait" if tid == trait_id else "Child trait"
            print(f"\n[{idx}/{len(trait_ids_to_fetch)}] Fetching {trait_type}: {tid}")
            
            trait_data = fetch_pgs_data_for_single_trait(tid)
            
            if trait_data:
                print(f"  ✓ Found {len(trait_data)} record(s)")
                for td in trait_data:
                    if td['PGS ID'] not in all_output:
                        td['mapped_diseases'] = [trait]
                        all_output[td['PGS ID']] = td  # Use PGS ID as key to avoid duplicates
                    else:
                        all_output[td['PGS ID']]['mapped_diseases'].append(trait)
                
            else:
                print(f"  ✗ No records found")
            
            time.sleep(0.3)
        
        print("\n" + "-" * 60)
        print(f"Total PGS records fetched: {len(all_output)}")

        
        return list(all_output.values())
        
    except Exception as e:
        print(f"Exception occurred: {e}")
        raise e

if __name__ == "__main__":
    # Fetch and print the data

    disease_name = "urinary system disease"
    trait_id = "EFO_0009690"
    results = fetch_pgs_data(disease_name, trait_id, include_child_traits=True)
    for entry in results:
        print(json.dumps(entry, indent=2))
    results_no_children = fetch_pgs_data(disease_name, trait_id, include_child_traits=False)
    print (len(results_no_children))
    for entry in results_no_children:
        print(json.dumps(entry, indent=2))
