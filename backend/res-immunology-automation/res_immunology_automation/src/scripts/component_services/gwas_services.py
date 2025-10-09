import requests
import time

def get_gwas_studies(efo_id):

    base_url = f"https://www.ebi.ac.uk/gwas/api/v2/efotraits/{efo_id}/studies/"
    params = {"fullPvalueSet": False, "includeChildTraits": True, "includeBgTraits": False, "size": 1000}
    headers = {"Accept": "application/json"}

    response = requests.get(base_url, params = params, headers=headers)
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return None

    data = response.json()
    # print (data)
    filtered_studies = []

    pages_available = data.get("page", {}).get("totalPages", 1)
    print("Total pages available:", pages_available)
    for page in range(1, pages_available+1):
        if page > 1:
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


if __name__ == "__main__":
    # Example: Fetch only studies for Atopic Dermatitis (EFO_0000270)
    # efo_id = "MONDO_0004979"
    efo_id = "EFO_0000319"
    # Ensure this matches the GWAS Catalog trait name
    studies = get_gwas_studies(efo_id)
    for study in studies:
        for k,v in study.items():
            print(f"{k} : {v}")
        print("+"*50)
    # if not studies:
    #     print("No relevant GWAS studies found.")
