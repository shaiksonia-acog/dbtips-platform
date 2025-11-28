import os

chromosomes = [str(i) for i in range(1, 23)] + ['X', 'Y'] # store as strings for easier matching

def fetch_variants(disease, asso_file_path):
    chromosome_dict = {chrom: [] for chrom in chromosomes}

    with open(asso_file_path, "r") as af:
        header_line = af.readline().strip().lstrip("#")
        headers = header_line.split("\t")

        fields_to_keep = ["Chromosome", "rsID"]
        missing_fields = [f for f in fields_to_keep if f not in headers]
        if missing_fields:
            raise ValueError(f"Missing expected fields: {missing_fields}")

        chrom_idx = headers.index("Chromosome")
        rsid_idx = headers.index("rsID")

        for line in af:
            parts = line.strip().split("\t")
            if len(parts) <= max(chrom_idx, rsid_idx):
                continue  # skip malformed lines

            chrom = parts[chrom_idx].strip()
            rsid = parts[rsid_idx].strip()

            if chrom in chromosome_dict:
                chromosome_dict[chrom].append(rsid)

    # Save variants per chromosome
    for chrom, rsids in chromosome_dict.items():
        if not rsids:
            continue  # skip empty chromosomes
        if chrom == 'X':
            chrom = '23'
        elif chrom == 'Y':
            chrom = '24'    
        variants_path = f"/shared/VEP/GWAS/diseases/{disease}/chrs/{chrom}/input"
        os.makedirs(variants_path, exist_ok=True)
        variants_file = os.path.join(variants_path, "variants.txt")

        with open(variants_file, "w") as fout:
            fout.write("\n".join(rsids))

        print(f"Saved {len(rsids)} variants to {variants_file}")

fetch_variants("glaucoma", "/home/amani/dbtips-mrl-test/dbtips-platform-copy/backend/res-immunology-automation/res_immunology_automation/src/scripts/cached_data_json/disease/MONDO_0005041.tsv")

            