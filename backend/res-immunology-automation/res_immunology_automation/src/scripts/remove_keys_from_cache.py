import os
import json

# === CONFIGURATION ===
DISEASE_FOLDER_PATH = "/app/res-immunology-automation/res_immunology_automation/src/scripts/cached_data_json/disease"  
TARGET_DISEASE_FOLDER_PATH = "/app/res-immunology-automation/res_immunology_automation/src/scripts/cached_data_json/target_disease"  
TARGET_FOLDER_PATH = "/app/res-immunology-automation/res_immunology_automation/src/scripts/cached_data_json/target"  


def remove_key_from_json(file_path, keys_to_remove):
    """Remove a specific key from JSON and overwrite the same file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for key in keys_to_remove:
        # If it's a dict, remove directly
            if isinstance(data, dict):
                data.pop(key, None)

        # Save back to the same file (pretty print optional)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✅ Updated: {file_path}")

    except Exception as e:
        print(f"⚠️ Error processing {file_path}: {e}")


def main(FOLDER_PATH, ends_with_str, KEYS_TO_REMOVE):
    for filename in os.listdir(FOLDER_PATH):
        if filename.endswith(ends_with_str):
            file_path = os.path.join(FOLDER_PATH, filename)
            remove_key_from_json(file_path, KEYS_TO_REMOVE)



if __name__ == "__main__":
    # patent
    main(TARGET_DISEASE_FOLDER_PATH, '_diseases.json', ['/evidence/search-patent/'])
    print("removed patents")
    main(TARGET_DISEASE_FOLDER_PATH, '-obesity.json', ['/evidence/search-patent/'])
    print("removed patents obesity")
    main(TARGET_FOLDER_PATH, '.json', ['/market-intelligence/target-pipeline/', '/evidence/target-mouse-studies/'])
    print("pipeline")
    # main(TARGET_FOLDER_PATH, '.json', ['/target-assessment/paralogs/', '/evidence/target-mouse-studies/'])
    # print("removed paralogs and perturbation")
    # main(DISEASE_FOLDER_PATH, '.json', ['/genomics/gwas-studies'])
    # print("removed gwas")