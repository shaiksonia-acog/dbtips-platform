import requests
import json
import time
import re
import pandas as pd
import os

gwas_data_path = '/app/res-immunology-automation/res_immunology_automation/src/gwas_data'

def prepare_variant_lists(variants):
    """
    Split variants into rsID and region-based formats acceptable to VEP.
    Examples:
        rs174877-?         → rs174877
        chr5:115005093-A   → 5 115005093 A
        chr17:2038180-G    → 17 2038180 G
    """
    rsid_list = []
    region_list = []

    for v in variants:
        v = v.strip()
        if v.startswith("rs"):
            clean_rsid = re.split(r"[-\s]", v)[0]
            rsid_list.append(clean_rsid)

        elif v.startswith("chr"):
            clean = v.replace("chr", "")
            match = re.match(r"(\d+|X|Y|MT):(\d+)-([ACGT])", clean)
            if match:
                chrom, pos, alt = match.groups()
                formatted = f"{chrom} {pos} {alt}"
                region_list.append(formatted)
            else:
                print(f"⚠️ Skipping invalid variant format: {v}")

    return rsid_list, region_list


def post_vep_ids(rsids, batch_size=200):
    """POST to /vep/human/id in batches."""
    results = []
    url = "https://rest.ensembl.org/vep/human/id"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    # Additional query parameters
    params = {
        "AlphaMissense": 1,
        "CADD": 1,
        "ClinVar": 1,
        "one_consequence_per_variant": 1,
        "domains": 1,
    }

    for i in range(0, len(rsids), batch_size):
        batch = rsids[i:i + batch_size]
        payload = {"ids": [r.split("-")[0] for r in batch]}  # strip allele for API

        print(f"🧬 Sending ID batch {i//batch_size + 1} ({len(batch)} variants)")
        try:
            resp = requests.post(url, headers=headers, params=params, json=payload)
            resp.raise_for_status()
            batch_results = resp.json()

            # # Map original variant string to output
            # for original, result in zip(batch, batch_results):
            #     result["input_original"] = original
            results.extend(batch_results)

        except Exception as e:
            print(f"❌ Batch failed: {e}")
        time.sleep(0.5)
    
    return results
    

def post_vep_regions(regions, batch_size=200):
    """POST to /vep/human/region in batches, skipping variants with '?'."""
    results = []
    url = "https://rest.ensembl.org/vep/human/region"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    # Additional query parameters
    params = {
        "AlphaMissense": 1,
        "CADD": 1,
        "ClinVar": 1,
        "one_consequence_per_variant": 1,
        "domains": 1,
    }

    for i in range(0, len(regions), batch_size):
        batch = regions[i:i + batch_size]

        valid_batch = []
        for r in batch:
            if "?" in r:
                # Directly append a dummy entry if allele is unknown
                results.append({
                    "id": "?",
                    "input": r,
                    "Clinical Significance": None,
                    "Pfam": None,
                    "Consequence": None,
                    "Alphamissense": {"score": None, "category": None},
                    "CADD": None,
                    "SIFT": {"score": None, "category": None},
                    "PolyPhen": {"score": None, "category": None},
                    "input_original": r
                })
                continue
            valid_batch.append(r)

        # Skip VEP call if no valid variants in this batch
        if not valid_batch:
            continue

        # Prepare clean format for VEP: remove "chr", replace ":" and "-" with spaces
        normalized_batch = [
            r.replace("chr", "").replace(":", " ").replace("-", " ") + " G A"
            for r in valid_batch
        ]

        payload = {"variants": normalized_batch}
        print(f"🧬 Sending region batch {i // batch_size + 1} ({len(valid_batch)} variants)")

        try:
            resp = requests.post(url, headers=headers, params=params, json=payload)
            resp.raise_for_status()
            batch_results = resp.json()

            # # Map back to original inputs
            # for original, result in zip(valid_batch, batch_results):
            #     result["input_original"] = original
            results.extend(batch_results)

        except Exception as e:
            print(f"❌ Batch failed: {e}")

        time.sleep(0.5)

    return results


def parse_vep_entry(entry, variant_map):
    """Extract relevant fields from VEP JSON entry."""
    result = {
        "id": entry.get("id"),
        "input": entry.get("input"),
        "Clinical Significance": None,
        "Pfam": None,
        "Consequence": entry.get("most_severe_consequence"),
        "Alphamissense": {"score": None, "category": None},
        "CADD": None,
        "SIFT": {"score": None, "category": None},
        "PolyPhen": {"score": None, "category": None},
    }

    # Transcript-level info
    transcript = entry.get("transcript_consequences", [{}])[0]

     # Consequence
    if "most_severe_consequence" in entry:
        result["Consequence"] = entry.get("most_severe_consequence")

    # Original input
    if "input" in entry:
        input_val = entry.get("input")

        if input_val:
            # rsID case
            if input_val.startswith("rs"):
                result["input_original"] = variant_map[input_val]
            else:
                # region-like input such as "4 46866778 T G A"
                parts = input_val.split()
                if len(parts) >= 3:
                    chrom, pos, alt = parts[0], parts[1], parts[2]
                    result["input_original"] = f"chr{chrom}:{pos}-{alt}"
                else:
                    result["input_original"] = input_val
        else:
            result["input_original"] = None

    # ClinVar significance
    for coloc in entry.get("colocated_variants", []):
        if "clin_sig" in coloc:
            result["Clinical Significance"] = coloc["clin_sig"]

    # AlphaMissense
    am = transcript.get("alphamissense")
    if am and isinstance(am, dict):
        result["Alphamissense"]["score"] = am.get("am_pathogenicity")
        result["Alphamissense"]["category"] = am.get("am_class")

    # CADD
    if "cadd_phred" in transcript:
        result["CADD"] = transcript["cadd_phred"]

    # SIFT
    if "sift_score" in transcript:
        result["SIFT"]["score"] = transcript["sift_score"]
        result["SIFT"]["category"] = transcript.get("sift_prediction")

    # PolyPhen
    if "polyphen_score" in transcript:
        result["PolyPhen"]["score"] = transcript["polyphen_score"]
        result["PolyPhen"]["category"] = transcript.get("polyphen_prediction")

    # Pfam domain
    if "domains" in transcript:
        for domain in transcript["domains"]:
            if domain.get("db") == "Pfam":
                result["Pfam"] = domain.get("name")

    return result


def annotate_variants(variants):
    rsid_list = [v for v in variants if v.startswith("rs")]
  
    variant_map = {}
    for v in rsid_list:
        if v.startswith("rs"):
            # e.g., rs201680145-G → rs201680145
            key = v.split("-")[0]
            variant_map[key] = v

    region_list = [v for v in variants if v.lower().startswith("chr")]
    print(f"🧩 {len(rsid_list)} rsIDs | {len(region_list)} chr:pos variants")

    all_entries = []

    if rsid_list:
        all_entries.extend(post_vep_ids(rsid_list,))
        
    if region_list:
        all_entries.extend(post_vep_regions(region_list))

    parsed_results = [parse_vep_entry(e,  variant_map) for e in all_entries]

    # Save combined JSON
    annotation_file_path = os.path.join(gwas_data_path, 'annotated_variants.json')
    if not os.path.exists(annotation_file_path):
        with open(annotation_file_path, "w") as f:
            json.dump(parsed_results, f, indent=4)
        print(f"✅ Saved {len(parsed_results)} annotated variants to annotated_variants.json")

    # Flatten and merge score + category
    flat_data = []
    for r in parsed_results:
        flat_data.append({
            "Input": r["input_original"],
            "Consequence": r.get("Consequence"),
            "AlphaMissense": f"{r['Alphamissense']['score']} ({r['Alphamissense']['category']})",
            "SIFT": f"{r['SIFT']['score']} ({r['SIFT']['category']})",
            "PolyPhen": f"{r['PolyPhen']['score']} ({r['PolyPhen']['category']})",
            "CADD": r.get("CADD"),
            "Pfam": r.get("Pfam"),
            "Pfam_url": f"https://www.ebi.ac.uk/interpro/entry/pfam/{r.get('Pfam')}"
        })

    # Create dataframe
    df = pd.DataFrame(flat_data)

    # Save as TSV
    score_file_path = os.path.join(gwas_data_path, 'variant_scores.tsv')
    if not os.path.exists(score_file_path):
        df.to_csv(score_file_path, sep="\t", index=False)

    print(f"✅ Saved {len(df)} results to {score_file_path}")
    print(df.head())

    return df






# if __name__ == "__main__":
#     gwas_path = "/app/res-immunology-automation/res_immunology_automation/src/gwas_data/EFO_0000319.tsv"
#     gwas_df = pd.read_csv(gwas_path, sep="\t")

#     variant_list = (
#     gwas_df["Variant and Risk Allele"]
#     .dropna()             # remove missing values
#     .astype(str)          # ensure all are strings
#     .unique()             # get unique entries
#     .tolist()             # convert to Python list
# )
#     print(variant_list[:10])



    # variant_list = [
    #     "rs750484931-A",
    #     "chr19:15179052-A",
    #     "rs201680145-G",
    #     "rs121913529",
    #     "chr4:111681501-?",
    # ]

# results = annotate_variants(variant_list)



