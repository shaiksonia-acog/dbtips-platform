import requests
import xml.etree.ElementTree as ET
import re
import time

MESH_TREE_TO_AREA = {
    'C01': 'Bacterial Infections',
    'C02': 'Virus Diseases',
    'C03': 'Parasitic Diseases',
    'C04': 'Neoplasms',
    'C05': 'Musculoskeletal Diseases',
    'C06': 'Digestive System Diseases',
    'C07': 'Stomatognathic Diseases',
    'C08': 'Respiratory Tract Diseases',
    'C09': 'Otorhinolaryngologic Diseases',
    'C10': 'Nervous System Diseases',
    'C11': 'Eye Diseases',
    'C12': 'Urologic Diseases',
    'C13': 'Female Genital Diseases and Pregnancy Complications',
    'C14': 'Cardiovascular Diseases',
    'C15': 'Hemic and Lymphatic Diseases',
    'C16': 'Congenital, Hereditary, and Neonatal Diseases',
    'C17': 'Skin and Connective Tissue Diseases',
    'C18': 'Nutritional and Metabolic Diseases',
    'C19': 'Endocrine Diseases',
    'C20': 'Immune System Diseases',
    'C21': 'Disorders of Environmental Origin',
    'C22': 'Animal Diseases',
    'C23': 'Pathological Conditions, Signs and Symptoms',
    'C24': 'Occupational Diseases'
}

def efoid_to_meshid_mapper(term_id):
    """
    Given an EFO ID or a MeSH ID, return the corresponding cross-reference(s).
    Automatically detects the type based on prefix.
    """

    base_url = "https://www.ebi.ac.uk/ols4/api"

    if term_id.upper().startswith("EFO"):
        # EFO → MeSH
        iri = f"http://www.ebi.ac.uk/efo/{term_id.replace(':', '_')}"
        url = f"{base_url}/ontologies/efo/terms?iri={iri}"
        r = requests.get(url)
        if r.status_code != 200:
            return {"error": "Failed to fetch EFO term"}
        data = r.json()
        if not data.get("_embedded"):
            return {"error": "EFO term not found"}

        term = data["_embedded"]["terms"][0]
        label = term.get("label")

        # Try all possible xref locations
        xrefs = []
        if "obo_xref" in term:
            xrefs.extend(term["obo_xref"])
        if "annotation" in term:
            ann = term["annotation"]
            for key in ["hasDbXref", "database_cross_reference", "xref"]:
                if key in ann:
                    xrefs.extend(ann[key])

        # Filter MeSH xrefs
        mesh_xrefs = [x for x in xrefs if isinstance(x, str) and x.startswith("MESH:")]
        mesh_ids = [x.replace("MESH:", "") for x in mesh_xrefs]
        return mesh_ids

    else:
        return {"error": "Unknown ID type. Use EFO_XXXX."}


def predict_disease_area_from_title_abstract(title:str, abstract:str):
    return ""
    # Invoke LLM to predict the disease area from the title/abstract of the paper

def pmid_to_meshid_mapper(pmid):
    """Fetch MeSH terms and MeSH IDs from PubMed"""
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        'db': 'pubmed',
        'id': pmid,
        'retmode': 'xml'
    }
    response = requests.get(url, params=params)
    #print (response.text)
    mesh_terms = []
    
    if response.status_code == 200:
        root = ET.fromstring(response.text)
        for mesh_heading in root.findall(".//MeshHeading"):
            descriptor = mesh_heading.find("DescriptorName")
            qualifier = mesh_heading.find("QualifierName")
            #if descriptor is not None and descriptor.attrib.get('MajorTopicYN') == "Y":
            if descriptor is not None and qualifier is not None and ((descriptor.attrib.get('MajorTopicYN') == "Y") or (qualifier.attrib.get('MajorTopicYN') == "Y")):
                term = descriptor.text
                mesh_id = descriptor.attrib.get('UI')
                mesh_terms.append((mesh_id))
    return mesh_terms

def fetch_mesh_tree_numbers_batch(mesh_ids):
    """Fetch tree numbers for a list of MeSH IDs using NLM MeSH API"""
    result = {}
    for mesh_id in mesh_ids:
        url = f"https://id.nlm.nih.gov/mesh/{mesh_id}.json"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code != 200:
                result[mesh_id] = []
                continue
            data = response.json()
            # Tree numbers are directly under 'treeNumber' key
            tree_numbers = data.get('treeNumber', [])
            result[mesh_id] = tree_numbers
        except:
            result[mesh_id] = []
        time.sleep(0.1)
    return result

def map_mesh_to_disease_area(mesh_ids):
    """Map MeSH terms to disease areas using tree numbers"""
    #mesh_ids = [mesh_id for _, mesh_id in mesh_terms if mesh_id]
    tree_mapping = fetch_mesh_tree_numbers_batch(mesh_ids)
    areas = set()
    for mesh_id in mesh_ids:
        tree_numbers = tree_mapping.get(mesh_id, [])
        if isinstance(tree_numbers, str):
            for prefix, area in MESH_TREE_TO_AREA.items():
                if prefix in tree_numbers:
                    areas.add(area)
        for tn in tree_numbers:
            for prefix, area in MESH_TREE_TO_AREA.items():
                if prefix in tn:
                    areas.add(area)
    return list(areas)


# if __name__ == "__main__":
#     # In market intelligence section, for each trial record, do the following. 
#     efoid = "EFO_0001645"
#     mesh_ids = efoid_to_meshid_mapper(efoid)
#     disease_areas = map_mesh_to_disease_area(mesh_ids)
#     print (efoid, disease_areas)
#     print ()

#     # In literature section, for each PMID, do the following. 

#     pmid_list = [
#     ('34323223')
#     ]
#     for pmid in pmid_list:
#         mesh_ids = pmid_to_meshid_mapper(pmid)
#         if mesh_ids:
#             disease_areas = map_mesh_to_disease_area(mesh_ids)
#         else:
#             # Some PMIDs will not have MeSH terms. 
#             # In sucb cases, rely on LLM to predict disease area based on title/abstract.
#             title = "sample title"
#             abstract = "sample abstract"
#             disease_areas = predict_disease_area_from_title_abstract (title, abstract)
#         print (pmid, disease_areas)