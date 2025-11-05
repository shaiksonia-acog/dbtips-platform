import os

import re
import pandas as pd

def parse_vep_header(line):
    """
    Robust VEP header parser.
    Handles tab- or space-separated headers, and fixes merged plugin fields automatically.
    """
    # Remove leading '#' and strip whitespace/newlines
    line = line.lstrip("#").strip()

    # Split by tab if present, otherwise by any whitespace
    headers = line.split("\t") if "\t" in line else re.split(r"\s+", line)
    headers = [h.strip() for h in headers if h.strip()]

    fixed_headers = []

    for h in headers:
        # Case 1: merged headers (e.g. am_pathogenicityCADD_phred)
        # Find patterns like wordWord or word_numberWord or field1field2 with underscores
        # Example: "am_pathogenicityCADD_phred" → ["am_pathogenicity", "CADD_phred"]
        if re.search(r"[a-z]CADD_|[a-z]Polyphen|[a-z]SIFT|[a-z]PrimateAI|[a-z]MutPred", h):
            parts = re.split(r"(?=[A-Z])", h)  # split before uppercase
            for part in parts:
                part = part.strip()
                if part:
                    fixed_headers.extend(re.split(r"(?<!_)_", part)) if "_" in part else fixed_headers.append(part)
        else:
            # For other merged cases like field1field2 (no underscores, both alphabetic)
            # Example: am_pathogenicityCADD_phred → am_pathogenicity + CADD_phred
            split_match = re.findall(r"[A-Z]?[a-z0-9_]+", h)
            if len(split_match) > 1 and not h.endswith(split_match[-1]):
                fixed_headers.extend(split_match)
            else:
                fixed_headers.append(h)

    # Deduplicate while preserving order
    seen = set()
    cleaned = []
    for h in fixed_headers:
        if h not in seen:
            cleaned.append(h)
            seen.add(h)

    return cleaned

def append_vep_fields(asso_file_path, output_file, vep_lookup, fields_to_keep):
    """
    Append VEP annotation fields to association file using pandas.
    """

    # Load associations TSV safely
    df = pd.read_csv(asso_file_path, sep="\t", dtype=str).fillna("NA")

    # Make sure RSID column exists
    rsid_col = "rsid" if "rsid" in df.columns else df.columns[3]  # fallback if unnamed
    print(f"Using RSID column: {rsid_col}")

    # Convert vep_lookup (dict) to DataFrame
    # Example: vep_lookup = { "rs123": ["HIGH", "missense_variant", ...], ... }
    vep_df = pd.DataFrame.from_dict(vep_lookup, orient="index", columns=fields_to_keep)
    vep_df.index.name = rsid_col
    vep_df.reset_index(inplace=True)

    # Merge association data with VEP annotations
    merged = df.merge(vep_df, on=rsid_col, how="left")

    # Replace missing merged values with "NA"
    merged.fillna("NA", inplace=True)

    # Write the combined data back to TSV
    merged.to_csv(output_file, sep="\t", index=False)

    print(f"✅ Merged file written to {output_file}")

    print(f"✅ Annotated file written to: {output_file}")


def annotate_vep_data(disease, asso_file_path): 
    # Fields you want to extract from VEP files
    fields_to_keep = [
        "IMPACT", 
        "am_class", "am_pathogenicity", "CADD_phred",
        "Polyphen2_HDIV_rankscore", "SIFT4G_converted_rankscore"
    ]
    VEP_DIR = f"/shared/VEP/GWAS/diseases/{disease}/chrs"
    # Output file name
    base, ext = os.path.splitext(asso_file_path)
    output_file = f"{base}_vep{ext}"

    # Step 1: Build a lookup dict for RSID → selected VEP values
    vep_lookup = {}

    for chrm_dir in os.listdir(VEP_DIR):
        print("Processing: ", chrm_dir)
        chrm_file_path = os.path.join(VEP_DIR, f"{chrm_dir}/output/variants_output.txt")
        print("chrm_file_path: ", chrm_file_path)
        if not os.path.isfile(chrm_file_path):
            continue

        with open(chrm_file_path, "r") as fin:
            header_indices = None
            headers = []

            for line in fin:
                # Skip metadata
                if line.startswith("##"):
                    continue

                # Capture header line
                if line.startswith("#Uploaded"):
                    # print("header line: ", repr(line))
                    # headers = [h.strip() for h in line.lstrip("#").rstrip("\n").split("\t")]
                    # print("headers: ", repr(headers))
                    # header_indices = [headers.index(f) for f in fields_to_keep if f in headers]
                    # print("header_indices:", header_indices)
                    # missing = [f for f in fields_to_keep if f not in headers]
                    # if missing:
                    #     print("⚠️ Missing fields:", missing)
                    # else:
                    #     print("✅ All fields found!")
                    # continue
                    if line.startswith("#") and not line.startswith("##"):
                        headers = parse_vep_header(line)
                        missing = [f for f in fields_to_keep if f not in headers]
                        header_indices = [headers.index(f) for f in fields_to_keep if f in headers]
                        print("header_indices:", header_indices)
                        if missing:
                            print("⚠️ Missing fields:", missing)
                        else:
                            print("✅ All fields found!")

                # Process data lines
                if header_indices:
                    parts = line.strip().split()
                    rsid = parts[0] if header_indices else None
                    if rsid:
                        if rsid not in vep_lookup:
                            vep_lookup[rsid] = [parts[i] if i < len(parts) else "" for i in header_indices]
                        # print("vep_lookup:", rsid, vep_lookup[rsid])

    append_vep_fields(asso_file_path, output_file, vep_lookup, fields_to_keep)

annotate_vep_data("urologic_diseases","/home/amani/dbtips-mrl-test/dbtips-platform-copy/backend/res-immunology-automation/res_immunology_automation/src/scripts/cached_data_json/disease/EFO_0009690.tsv")
