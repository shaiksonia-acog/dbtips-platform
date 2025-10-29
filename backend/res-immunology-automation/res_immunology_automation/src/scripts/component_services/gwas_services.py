import requests
import time

def get_gwas_studies(efo_id, child_trait: bool= True):

    base_url = f"https://www.ebi.ac.uk/gwas/api/v2/efotraits/{efo_id}/studies/"
    params = {"fullPvalueSet": False, "includeChildTraits": child_trait, "includeBgTraits": False, "size": 1000}
    headers = {"Accept": "application/json"}

    response = requests.get(base_url, params = params, headers=headers)
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return []

    data = response.json()
    # print (data)
    filtered_studies = []

    pages_available = data.get("page", {}).get("totalPages", 1)
    print("Total pages available:", pages_available)
    for page in range(0, pages_available):
        if page > 0:
            time.sleep(1)  # To avoid hitting rate limits
            params["page"] = page
            response = requests.get(base_url, params=params, headers=headers)
            if response.status_code != 200:
                print(f"Error on page {page}: {response.status_code}")
                continue
            data = response.json()

        if "_embedded" in data:
            if 'studies' in data['_embedded']:
                for study in data["_embedded"]["studies"]:
                    if "efoTraits" in study:
                        trait = study.get("efoTraits")[0].get("label").lower()
                        filtered_studies.append({
                            "First author": study.get("firstAuthor") or "Not available",
                            "Study accession": study["accessionId"],
                            "Pub. date": study.get("publicationDate") or "Not available",
                            "Journal": study.get("journal") or "Not available",
                            "Title": study.get("title") or "Not available",
                            "Reported trait": study.get("reportedTrait") or "Not available",
                            "Trait(s)": study.get("efoTraits")[0].get("label") or "Not available",
                            "Discovery sample ancestry": study.get("discoverySampleAncestry") or "Not available",
                            "Replication sample ancestry": study.get("replicationSampleAncestry") or "Not available",
                            "Association count": study.get("associationCount") or 0,
                            "Summary statistics": study.get("summaryStatistics") or "Not available"
                        })
                    else:
                        filtered_studies.append({})
    return filtered_studies

def fetch_gwas_studies_including_related_measurements(efo_id, disease):
    additional_terms = {
            "cardiovascular diseases": {
                "with_child": ['EFO_0004298'],
                "without_child": ['EFO_0005106', 'EFO_0004340', 'EFO_0004338', 'EFO_0007861']
            },
            "obesity": {
                "with_child": [],
                "without_child": ['EFO_0004302', 'EFO_0001074', 'EFO_0022016', 'EFO_0007830', 'EFO_0004529', 'EFO_0006842'] 
            },
            "urologic diseases":{
                "with_child": [],
                "without_child": ['OBA_0004158', 'EFO_0005116', 'OBA_VT0005265']
            }
        }
    genomics_data = []
    efo_ids_with_child = additional_terms.get(disease, {}).get("with_child", [])
    efo_ids_without_child = additional_terms.get(disease, {}).get("without_child", [])
    efo_ids_with_child.append(efo_id)
    print("efo_ids_with_child: ", efo_ids_with_child)
    print("efo_ids_without_child: ", efo_ids_without_child)
    for ef_id in efo_ids_with_child:
        print(f"fetching data for {ef_id} from efo ids with child")
        data = get_gwas_studies(ef_id, True)
        genomics_data.extend(data)
    if efo_ids_without_child:
        for ef_id in efo_ids_without_child:
            print(f"fetching data for {ef_id} from efo ids without child")
            data = get_gwas_studies(ef_id, False)
            genomics_data.extend(data)
    
    return genomics_data

    
if __name__ == "__main__":
    # Example: Fetch only studies for Atopic Dermatitis (EFO_0000270)
    # efo_id = "MONDO_0004979"
    disease = "cardiovascular diseases"
    efo_id = "EFO_0000319"
    # Ensure this matches the GWAS Catalog trait name
    # studies = get_gwas_studies(efo_id)
    studies = fetch_gwas_studies_including_related_measurements(efo_id, disease)
    print(f"Total studies found for {efo_id}: {len(studies)}")
    # if not studies:
    #     print("No relevant GWAS studies found.")
