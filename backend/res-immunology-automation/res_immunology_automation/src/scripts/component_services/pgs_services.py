import requests
import gzip
import io
import csv
import pandas as pd
import time
import re


def split_score_dict(rsid_to_score):
    """
    Split input dict into three separate dicts:
      1. rsid_dict: keys like rs123
      2. chrpos_dict: keys like chr1:12345 or 1:12345
      3. gene_dict: keys like BRCA1, APOE
    """
    rsid_pattern = re.compile(r"^rs\d+$", re.IGNORECASE)
    chrpos_pattern = re.compile(r"^(?:chr)?([0-9]{1,2}|[XYM]):\d+$", re.IGNORECASE)

    rsid_dict = {}
    chrpos_dict = {}
    gene_dict = {}

    for key, score in rsid_to_score.items():
        if rsid_pattern.match(key):
            rsid_dict[key] = score
        elif chrpos_pattern.match(key):
            normalized = re.sub(r"^chr", "", key, flags=re.IGNORECASE)
            chrpos_dict[normalized] = score
        else:
            gene_dict[key] = score

    return rsid_dict, chrpos_dict, gene_dict


# def stream_pgs_score_variants(score_file_url):
#     """
#     Stream only rsID and effect_weight columns from a gzipped PGS score file.
#     Efficient and memory-safe.
#     """
#     with requests.get(score_file_url, stream=True) as r:
#         r.raise_for_status()
#         with gzip.GzipFile(fileobj=r.raw) as gz:
#             text_stream = io.TextIOWrapper(gz, encoding='utf-8')
#             data_lines = (line for line in text_stream if not line.startswith('#'))
#             reader = csv.DictReader(data_lines, delimiter='\t')
#             for row in reader:
#                 rsid = row.get("rsID")
#                 weight = row.get("effect_weight")
#                 if rsid and weight:
#                     yield rsid, float(weight)



# def stream_pgs_score_variants(score_file_url):
#     """
#     Stream variant IDs and weights from a gzipped PGS score file.
#     Handles flexible column naming (e.g., rsID/RSID/rsid, effect_weight/snp_weight/etc.).
#     Efficient and memory-safe.
#     """
#     with requests.get(score_file_url, stream=True) as r:
#         r.raise_for_status()
#         with gzip.GzipFile(fileobj=r.raw) as gz:
#             text_stream = io.TextIOWrapper(gz, encoding="utf-8")
#             data_lines = (line for line in text_stream if not line.startswith("#"))
#             reader = csv.DictReader(data_lines, delimiter="\t")

#             # Normalize column names (case-insensitive matching)
#             lower_headers = {col.lower(): col for col in reader.fieldnames}
#             rsid_col = next((lower_headers[c] for c in ["rsid", "variant_id", "snp"] if c in lower_headers), None)
#             weight_col = next((lower_headers[c] for c in ["effect_weight", "snp_weight", "weight"] if c in lower_headers), None)

#             if not rsid_col or not weight_col:
#                 raise ValueError(
#                     f"Could not find required columns in file. Found columns: {reader.fieldnames}"
#                 )

#             for row in reader:
#                 rsid = row.get(rsid_col)
#                 weight = row.get(weight_col)
#                 if rsid and weight:
#                     try:
#                         yield rsid.strip(), float(weight)
#                     except ValueError:
#                         continue  # skip rows with invalid numbers


def stream_pgs_score_variants(score_file_url):
    """
    Stream variant IDs (rsID or chr:pos:alleles) and weights from a gzipped PGS score file.
    Handles flexible column naming and constructs SNP IDs if rsID column is missing.
    Efficient and memory-safe.
    """
    with requests.get(score_file_url, stream=True) as r:
        r.raise_for_status()
        with gzip.GzipFile(fileobj=r.raw) as gz:
            text_stream = io.TextIOWrapper(gz, encoding="utf-8")
            data_lines = (line for line in text_stream if not line.startswith("#"))
            reader = csv.DictReader(data_lines, delimiter="\t")

            lower_headers = {col.lower(): col for col in reader.fieldnames}

            # Synonyms for key columns
            rsid_synonyms = ["rsid", "variant_id", "snp"]
            weight_synonyms = ["effect_weight", "snp_weight", "weight"]
            chr_synonyms = ["chr_name", "chr"]
            pos_synonyms = ["chr_position", "chr_pos", "pos", "position", "POS"]
            ea_synonyms = ["effect_allele", "ea", "EA", "minor_allele", "alt_allele"]
            oa_synonyms = ["other_allele", "oa", "OA", "ref_allele", "wild_type"]

            # Identify columns
            rsid_col = next((lower_headers[c] for c in rsid_synonyms if c in lower_headers), None)
            weight_col = next((lower_headers[c] for c in weight_synonyms if c in lower_headers), None)

            chr_col = next((lower_headers[c] for c in chr_synonyms if c in lower_headers), None)
            pos_col = next((lower_headers[c] for c in pos_synonyms if c in lower_headers), None)
            ea_col = next((lower_headers[c] for c in ea_synonyms if c in lower_headers), None)
            oa_col = next((lower_headers[c] for c in oa_synonyms if c in lower_headers), None)

            if not weight_col:
                raise ValueError(
                    f"Could not find weight column in file. Found columns: {reader.fieldnames}"
                )

            if not rsid_col and not (chr_col and pos_col and ea_col and oa_col):
                raise ValueError(
                    f"Could not find rsID column or the required columns "
                    f"for SNP ID construction (chr, pos, ea, oa). Found: {reader.fieldnames}"
                )

            for row in reader:
                # Use rsID if available
                if rsid_col:
                    rsid = row.get(rsid_col)
                else:
                    chr_name = row.get(chr_col)
                    pos = row.get(pos_col)
                    ea = row.get(ea_col)
                    oa = row.get(oa_col)
                    if chr_name and pos and ea and oa:
                        rsid = f"{chr_name.strip()}:{pos.strip()}:{ea.strip()}:{oa.strip()}"
                    else:
                        continue

                weight = row.get(weight_col)
                if rsid and weight:
                    try:
                        yield rsid.strip(), float(weight)
                    except ValueError:
                        continue  # skip rows with invalid numbers

def count_pgs_rows(score_file_url):
    """Return number of variant rows in the PGS score file."""
    count = 0
    for _ in stream_pgs_score_variants(score_file_url):
        count += 1
    return count

def annotate_rsids_with_genes(rsids, batch_size=200, verbose=True):
    """
    Query Ensembl VEP in batches to get gene names for each rsID.
    Includes debug print statements for progress monitoring.
    """
    endpoint = "https://rest.ensembl.org/vep/human/id"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    
    rsid_to_genes = {}
    total = len(rsids)
    
    if verbose:
        print(f"🔍 Annotating {total} rsIDs via Ensembl VEP (batch size: {batch_size})")
    
    start_time = time.time()
    for i in range(0, total, batch_size):
        batch = rsids[i:i+batch_size]
        if verbose:
            print(f"→ Processing batch {i//batch_size + 1} "
                  f"({i+1}–{min(i+batch_size, total)} of {total}) ...", end=" ")
        
        try:
            response = requests.post(endpoint, headers=headers, json={"ids": batch})
            response.raise_for_status()
            results = response.json()
            
            for entry in results:
                rsid = entry.get("id")
                genes = set()
                for tc in entry.get("transcript_consequences", []):
                    if "gene_symbol" in tc:
                        genes.add(tc["gene_symbol"])
                rsid_to_genes[rsid] = list(genes)
            
            end_time = time.time()
            batch_time = end_time - start_time

            if verbose:
                print(f"✅ done ({len(results)} annotated)")
                print(f"✅ done ({len(results)} annotated) in {batch_time:.2f}s")
            
            # Be nice to the API (optional short delay)
            time.sleep(0.2)
        
        except requests.exceptions.RequestException as e:
            print(f"\n⚠️  Batch {i//batch_size + 1} failed: {e}")
            continue

    if verbose:
        print(f"\n✅ Completed annotation of {len(rsid_to_genes)} rsIDs total.")
    
    return rsid_to_genes


def annotate_variantids_with_genes(variants, batch_size=100, verbose=True):
    """
    Query Ensembl VEP in batches to get gene names for chr:pos formatted variants.
    Uses the /vep/human/region endpoint.
    
    Args:
        variants (list): List of variants in 'chr:pos' or 'chr:pos-ref/alt' format.
        batch_size (int): Number of variants per request.
        verbose (bool): Print progress messages.
    
    Returns:
        dict: Mapping {variant_id: [gene_symbols]}
    """
    endpoint = "https://rest.ensembl.org/vep/human/region"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    variant_to_genes = {}
    total = len(variants)

    if verbose:
        print(f"🔍 Annotating {total} variants via Ensembl VEP (region endpoint, batch size: {batch_size})")

    start_time = time.time()
    for i in range(0, total, batch_size):
        batch = variants[i:i + batch_size]
        if verbose:
            print(f"→ Processing batch {i // batch_size + 1} "
                  f"({i + 1}–{min(i + batch_size, total)} of {total}) ...", end=" ")

        try:
            response = requests.post(endpoint, headers=headers, json={"variants": batch})
            response.raise_for_status()
            results = response.json()

            for entry in results:
                variant = entry.get("input")
                genes = set()
                for tc in entry.get("transcript_consequences", []):
                    if "gene_symbol" in tc:
                        genes.add(tc["gene_symbol"])
                variant_to_genes[variant] = list(genes)

            batch_time = time.time() - start_time
            if verbose:
                print(f"✅ done ({len(results)} annotated) in {batch_time:.2f}s")

            time.sleep(0.2)  # small delay to avoid API throttling

        except requests.exceptions.RequestException as e:
            print(f"\n⚠️  Batch {i // batch_size + 1} failed: {e}")
            continue

    if verbose:
        print(f"\n✅ Completed annotation of {len(variant_to_genes)} variants total.")

    return variant_to_genes


def annotate_pgs_varinats(pgs_file_url):
    rsid_to_score = {rsid: score for rsid, score in stream_pgs_score_variants(pgs_file_url)}
    # rsid_to_score = dict(list(rsid_to_score.items())[:10])
    print(f"Total variants: {len(rsid_to_score)}")


    # Positive and negative lists
    positive_values = [v for v in rsid_to_score.values() if v > 0]
    negative_values = [v for v in rsid_to_score.values() if v < 0]
    abs_values = [abs(v) for v in rsid_to_score.values()]

    # Sums
    positive_sum = sum(positive_values)
    print("positive_sum", positive_sum)

    negative_sum = sum(negative_values)
    print("negative_sum", negative_sum)

    abs_sum = sum(abs_values)
    print("abs_sum", abs_sum)

    rsids = list(rsid_to_score.keys())
    print(rsids[:10])

    # rsids_to_be_annotated = rsids[:10]
    # print("rsids_to_be_annotated")
    # print(rsids_to_be_annotated)
    # rsid_to_genes = annotate_rsids_with_genes(rsids_to_be_annotated)

    # rsid_to_genes = annotate_rsids_with_genes(rsids)
    # rsid_to_genes = annotate_variantids_with_genes(rsids)
    # print("rsid_to_genes", len(rsid_to_genes))

    if all(str(r).lower().startswith("rs") for r in rsids):
        print("Detected rsID format — using annotate_rsids_with_genes()")
        rsid_to_genes = annotate_rsids_with_genes(rsids)
    elif all(":" in str(r) for r in rsids):
        print("Detected chr:pos:allele format — using annotate_variantids_with_genes()")
        rsid_to_genes = annotate_variantids_with_genes(rsids)
    else:
        raise ValueError("Mixed or unrecognized variant ID format in input list.")

    # # Print first few annotations
    # for rsid, genes in list(rsid_to_genes.items())[:5]:
    #     print(f"{rsid}: {genes}")

    rows = []
    for rsid, genes in rsid_to_genes.items():
        score = rsid_to_score.get(rsid)
        for gene in genes:
            rows.append((rsid, gene, score))

    df = pd.DataFrame(rows, columns=["rsid", "gene", "score"])
    print("Variant-to-Gene Annotation")
    print(df.shape)

    # # ✅ 1️⃣ Compute cumulative score per gene
    # gene_scores = df.groupby("gene", as_index=False)["score"].sum()

    # # ✅ 2️⃣ Sort by total score (optional)
    # gene_scores = gene_scores.sort_values(by="score", ascending=False)

    # ✅ Compute positive and negative cumulative scores separately per gene
    gene_scores = df.groupby("gene", as_index=False).agg(
        positive_score=("score", lambda x: x[x > 0].sum()),
        negative_score=("score", lambda x: x[x < 0].sum()),
        total_abs_score=("score", lambda x: x.abs().sum())

    )

    # ✅ Normalize (handle divide-by-zero safely)
    gene_scores["Percent risk score for gene"] = gene_scores["positive_score"] / positive_sum * 100 if positive_sum != 0 else 0
    gene_scores["Percent protective score for gene"] = gene_scores["negative_score"] / negative_sum * 100 if negative_sum != 0 else 0
    gene_scores["Overall effect of gene (in per cent) in disease risk prediction"] = gene_scores["total_abs_score"] / abs_sum * 100 if abs_sum != 0 else 0

    # Fix -0.0 values (floating point artifacts)
    gene_scores["Percent risk score for gene"] = gene_scores["Percent risk score for gene"].abs()
    gene_scores["Percent protective score for gene"] = gene_scores["Percent protective score for gene"].abs()

    # ✅ Keep only the percentage columns
    gene_scores = gene_scores[["gene", "Percent risk score for gene", "Percent protective score for gene", "Overall effect of gene (in per cent) in disease risk prediction"]]

    gene_dict = gene_scores.set_index("gene").to_dict(orient="index")
    print(f"Dictionary has been created for {pgs_file_url}")

    return gene_dict

    # print("Per-Gene Cumulative Effect Weight")
    # print(gene_scores)


def annotate_pgs_varinats_new(pgs_file_url):
    rsid_to_score = {rsid: score for rsid, score in stream_pgs_score_variants(PGS_file_url)}

    # Step 1: Split the dictionary
    rsid_dict, chrpos_dict, gene_dict = split_score_dict(rsid_to_score)

    all_rows = []

    # Step 2: Annotate rsIDs
    if rsid_dict:
        rsids = list(rsid_dict.keys())
        rsid_to_genes = annotate_rsids_with_genes(rsids)

        for rsid, genes in rsid_to_genes.items():
            score = rsid_dict.get(rsid)
            for gene in genes:
                all_rows.append((rsid, gene, score))

    # Step 3: Annotate chr:pos variants
    if chrpos_dict:
        chrpos_variants = list(chrpos_dict.keys())
        chrpos_to_genes = annotate_variantids_with_genes(chrpos_variants)

        for var, genes in chrpos_to_genes.items():
            score = chrpos_dict.get(var)
            for gene in genes:
                all_rows.append((var, gene, score))

    # Step 4: Keep gene_dict as-is (gene → self)
    if gene_dict:
        for gene, score in gene_dict.items():
            all_rows.append((gene, gene, score))

    # Step 5: Create DataFrame
    variant_gene_df = pd.DataFrame(all_rows, columns=["variant_id", "gene", "score"])

    print(variant_gene_df.head())
    print(f"\n✅ Total annotated entries: {len(variant_gene_df)}")

    # # ✅ 1️⃣ Compute cumulative score per gene
    # gene_scores = variant_gene_df.groupby("gene", as_index=False)["score"].sum()

    # ✅ Compute positive and negative cumulative scores separately per gene
    gene_scores = variant_gene_df.groupby("gene", as_index=False).agg(
        positive_score=("score", lambda x: x[x > 0].sum()),
        negative_score=("score", lambda x: x[x < 0].sum())
    )

    # ✅ 2️⃣ Sort by total score (optional)
    gene_scores = gene_scores.sort_values(by="score", ascending=False)


    print("Per-Gene Cumulative Effect Weight")
    print(gene_scores)





if __name__ == "__main__":
    PGS_file_url = "https://ftp.ebi.ac.uk/pub/databases/spot/pgs/scores/PGS001281/ScoringFiles/PGS001281.txt.gz"
    annotate_pgs_varinats(PGS_file_url)


    # PGS_file_url = "https://ftp.ebi.ac.uk/pub/databases/spot/pgs/scores/PGS004799/ScoringFiles/PGS004799.txt.gz"
    # annotate_pgs_varinats(PGS_file_url)
    # annotate_pgs_varinats_new(PGS_file_url)
    





