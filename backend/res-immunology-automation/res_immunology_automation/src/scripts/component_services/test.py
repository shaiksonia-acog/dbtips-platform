from Bio import Entrez
import time
import io

def get_mesh_tree_number(disease_name):
    Entrez.email = "Your.Email.Here@example.com"
    
    try:
        # Step 1: Search MeSH
        with Entrez.esearch(db="mesh", term=disease_name) as search_handle:
            search_results = Entrez.read(search_handle)
        
        if not search_results["IdList"]:
            print(f"No MeSH record found for '{disease_name}'.")
            return None
        
        mesh_id = search_results["IdList"][0]
        time.sleep(1)  # be polite
        
        # Step 2: Fetch the MeSH record
        with Entrez.efetch(db="mesh", id=mesh_id, retmode="xml") as fetch_handle:
            # Read as bytes
            data = fetch_handle.read()  
            # Wrap in BytesIO to satisfy Entrez.read
            mesh_record = Entrez.read(io.BytesIO(data))
        
        # Extract TreeNumbers
        tree_numbers = []
        descriptor = mesh_record.get("DescriptorRecord", [None])[0]
        if descriptor and "TreeNumberList" in descriptor:
            tree_numbers = list(descriptor["TreeNumberList"])
        
        return tree_numbers if tree_numbers else None
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


# Example usage
disease = "Cardiovascular Disease"
tree_numbers = get_mesh_tree_number(disease)

if tree_numbers:
    print(f"MeSH tree number(s) for '{disease}':")
    for number in tree_numbers:
        print(number)

# Example for a more general term
disease_2 = "Diabetes Mellitus"
tree_numbers_2 = get_mesh_tree_number(disease_2)

if tree_numbers_2:
    print(f"\nMeSH tree number(s) for '{disease_2}':")
    for number in tree_numbers_2:
        print(number)
