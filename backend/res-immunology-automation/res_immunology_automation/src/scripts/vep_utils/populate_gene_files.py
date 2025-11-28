import json
import os
gene_data_dir = "/home/amani/dbtips-mrl-test/dbtips-platform-copy/backend/res-immunology-automation/res_immunology_automation/src/scripts/cached_data_json/gene_data_files"
def populate(pgs_with_genes_file, cache_file):
    with open(pgs_with_genes_file, 'r') as f:
        cache = json.load(f)

    gene_files = {}
    unique_genes = set()
    pgs_data = cache.get('/genomics/pgscatalog/', [])
    rename_scores = {"Percent risk score for gene": "risk_score", 
                     "Percent protective score for gene": "protective_score",
                     "Overall effect of gene (in per cent) in disease risk prediction": "overall_effect_score"
                     }
    
    for idx, entry in enumerate(pgs_data):
        
        pgs_id = entry.get('PGS ID')
        print(f"Processing PGS ID: {pgs_id} {idx + 1} out of {len(pgs_data)}")
        for gene_entry, score in entry.get('targets_score', {}).items():
            gene_symbol = gene_entry
            unique_genes.add(gene_symbol)
            if gene_symbol not in gene_files:
                gene_files[gene_symbol] = {}
            for k, v  in score.items():
                renamed_key = rename_scores.get(k, k)
                gene_files[gene_symbol][pgs_id] = gene_files[gene_symbol].get(pgs_id, {})
                gene_files[gene_symbol][pgs_id][renamed_key] = round(v, 5)
            # gene_files[gene_symbol][pgs_id] = score
        
    
    print(f"Total unique genes found: {len(unique_genes)}")
    with open(cache_file, "r") as f:
        cache_data = json.load(f)
        cache_data['/genomics/pgscatalog_unique_genes/'] = list(unique_genes)
        with open(cache_file, "w") as f:
            json.dump(cache_data, f, indent=4)
            
    os.makedirs(gene_data_dir, exist_ok=True)
    os.chmod(gene_data_dir, 0o777) 
    for gene_symbol, entries in gene_files.items():
        file_name = f"{gene_symbol}_data.json"
        file_path = os.path.join(gene_data_dir, file_name)
        if os.path.exists(file_path):
            with open(file_path, 'r') as gf:
                existing_data = json.load(gf)
            existing_data.update(entries)
            entries = existing_data
        with open(file_path, 'w') as gf:
            json.dump(entries, gf, indent=4)
        os.chmod(file_path, 0o777)
        # print(f"Created file: {file_path} with {len(entries)} entries.")



if __name__ == "__main__":
    # disease = "age-related_macular_degeneration"
    # populate(f"/shared/VEP/PGS/diseases/{disease}/{disease}_with_scores.json", f"/home/amani/dbtips-mrl-test/dbtips-platform-copy/backend/res-immunology-automation/res_immunology_automation/src/scripts/cached_data_json/disease/{disease}.json")

    # # Populate HeatMap Data in GWAS
    heatmap_dir = "/shared/VEP/heatmap/new_targets_heatmap"
    targets = os.listdir(heatmap_dir)
    for target in targets:
        print("updating heatmap for target:", target)
        populate_heatmaps_data(target, heatmap_dir)