import json
import os

def populate_heatmaps_data(target, heatmap_dir):
    # heatmap_dir = "/shared/VEP/heatmap/output_heatmap"
    heatmap_file = os.path.join(f"{heatmap_dir}/{target}", f"{target}.json")
    if os.path.exists(heatmap_file):
        with open(heatmap_file, 'r') as f:
            heatmap_data = json.load(f)
        cache_file = f"/home/amani/dbtips-mrl-test/dbtips-platform-copy/backend/res-immunology-automation/res_immunology_automation/src/scripts/cached_data_json/target/{target.lower()}.json"
        print("updating cache file:", cache_file)
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        if not os.path.exists(cache_file):
            with open(cache_file, 'w') as f:
                json.dump({}, f)
        with open(cache_file, 'r') as f:
            target_cache = json.load(f)
        target_cache['/genomics/evidence-heatmap/'] = heatmap_data
        with open(cache_file, 'w') as f:
            json.dump(target_cache, f, indent=4)
        print(f"Heatmap data for {target} populated in cache.")

if __name__ == "__main__":

    # # Populate HeatMap Data in GWAS
    heatmap_dir = "/shared/VEP/heatmap/new_targets_heatmap"
    targets = os.listdir(heatmap_dir)
    for target in targets:
        print("updating heatmap for target:", target)
        populate_heatmaps_data(target, heatmap_dir)