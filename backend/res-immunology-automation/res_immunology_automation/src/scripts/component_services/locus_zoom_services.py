import pandas as pd
import numpy as np
import os, csv
from typing import List
from decimal import getcontext
import math
from decimal import Decimal, InvalidOperation

from .vep_annotation_service import annotate_variants

# from populate_gwas_asso_data import filter_asso_by_efo_id, prepare_variants_data, fetch_ld_data

gwas_data_path = '/app/res-immunology-automation/res_immunology_automation/src/gwas_data'
getcontext().prec = 100


def safe_to_decimal(x):
    try:
        return Decimal(str(x).strip())
    except (InvalidOperation, TypeError):
        return Decimal('NaN')


def neglog10_decimal(pval):
    try:
        if pval.is_nan() or pval == 0:
            return np.nan
        # log10(p) = ln(p) / ln(10)
        return float(-pval.ln() / Decimal(math.log(10)))
    except Exception:
        return np.nan


# # load Asso data Filter Asso data by EFOId and generate a variant df
def filter_asso_by_efo_id(studies: List[str], efo_id: str) -> pd.DataFrame:
    """
    Filter the GWAS Association data for given efo_id
    """
    print("Filtering the Associations data")
    filtered_df = None
    associations_file_path = os.path.join(gwas_data_path, 'associations.tsv')
    if os.path.exists(associations_file_path):
        with open(associations_file_path, 'r') as file:
            reader = csv.DictReader(file, delimiter='\t')
            filtered_rows = [row for row in reader if efo_id in row.get('MAPPED_TRAIT_URI', '') or row.get("STUDY ACCESSION", "") in studies]

        if len(filtered_rows) > 0:
            filtered_df = pd.DataFrame(filtered_rows)
            return filtered_df
        else:
            raise ValueError(f"Associations data doesn't exists for given {efo_id}")
    else:
        raise FileNotFoundError("The GWAS Acssociations data file does not exist.")

# Filter columns in variants file
def prepare_variants_data(df):
    """
    Drop unnecessary columns from variants data 
    """
    print("Adjusting and Sorting by Chromosome")
    new_df = pd.DataFrame() 
    df.columns = [col.strip() for col in df.columns]  # Clean up column names
    
    # Detect necessary columns for plotting
    required_columns = {"CHR_ID", "CHR_POS", "P-VALUE", "SNPS"}
    other_cols = {
                "PUBMEDID":"PubMed ID", "STRONGEST SNP-RISK ALLELE": "Variant and Risk Allele","SNPS": "rsID", 
                "FIRST AUTHOR": "Author", "MAPPED_GENE": "Mapped gene(s)", "DISEASE/TRAIT":"Reported trait", 
                "MAPPED_TRAIT": "Mapped Trait",
                "STUDY ACCESSION": "Study Accession", "RISK ALLELE FREQUENCY": "RAF", "OR or BETA": "OR or BETA",
                "95% CI (TEXT)": "CI"
                }
    if not required_columns.issubset(df.columns):
        raise ValueError(f"TSV file must contain these columns: {required_columns}")
    
    # Add derived columns if necessary
    if "Neglog10(pvalue)" not in df.columns:
        df["P-VALUE"] = df["P-VALUE"].apply(safe_to_decimal)
        df["P-VALUE"] = pd.to_numeric(df["P-VALUE"], errors="coerce")
        new_df['pvalue'] = df['P-VALUE']
        # new_df["Neglog10(pvalue)"] = -np.log10(df["P-VALUE"].replace(0, np.nan))  # Avoid log(0) error
        df["Neglog10(pvalue)"] = df["P-VALUE"].apply(neglog10_decimal)

    # Convert types
    df["Chromosome"] = pd.Categorical(df["CHR_ID"], categories=[str(i) for i in range(1, 23)] + ["X", "Y"], ordered=True)
    new_df["Chromosome"] = df["Chromosome"].cat.remove_unused_categories()
    new_df["Position"] = pd.to_numeric(df["CHR_POS"], errors="coerce")
    new_df['rsID'] = df['SNPS']
    for k,v in other_cols.items():
        new_df[v] = df[k]
    return new_df.sort_values("Chromosome")

def prepare_vep_data(df):
    """
    Drop unnecessary columns from variants data 
    """
    print("Adjusting and Sorting by Chromosome")
    new_df = pd.DataFrame() 
    df.columns = [col.strip() for col in df.columns]  # Clean up column names
    
    required_columns = {"CHR_ID", "CHR_POS", "P-VALUE", "SNPS"}
    other_cols = {
        "PUBMEDID":"PubMed ID",
        "STRONGEST SNP-RISK ALLELE": "Variant and Risk Allele",
        "SNPS": "rsID", 
        "FIRST AUTHOR": "Author",
        "MAPPED_GENE": "Mapped gene(s)",
        "DISEASE/TRAIT":"Reported trait", 
        "MAPPED_TRAIT": "Mapped Trait",
        "STUDY ACCESSION": "Study Accession",
        "RISK ALLELE FREQUENCY": "RAF",
        "OR or BETA": "OR or BETA",
        "95% CI (TEXT)": "CI"
    }

    if not required_columns.issubset(df.columns):
        raise ValueError(f"TSV file must contain these columns: {required_columns}")
    
    # --- ✅ Proper Decimal-safe handling of P-VALUE ---
    if "Neglog10(pvalue)" not in df.columns:
        df["P-VALUE_decimal"] = df["P-VALUE"].apply(safe_to_decimal)
        new_df['pvalue'] = df["P-VALUE_decimal"]
        # new_df['pvalue'] = df['P-VALUE'].apply(lambda x: float(x) if not x.is_nan() else np.nan)
        new_df["Neglog10(pvalue)"] = df["P-VALUE_decimal"].apply(neglog10_decimal)
    else:
        new_df['pvalue'] = pd.to_numeric(df["P-VALUE"], errors="coerce")
        new_df["Neglog10(pvalue)"] = pd.to_numeric(df["Neglog10(pvalue)"], errors="coerce")

    # --- Chromosome handling ---
    df["Chromosome"] = pd.Categorical(df["CHR_ID"], categories=[str(i) for i in range(1, 23)] + ["X", "Y"], ordered=True)
    new_df["Chromosome"] = df["Chromosome"].cat.remove_unused_categories()
    new_df["Position"] = pd.to_numeric(df["CHR_POS"], errors="coerce")
    new_df['rsID'] = df['SNPS']

    # --- Copy other columns ---
    for k, v in other_cols.items():
        if k in df.columns:
            new_df[v] = df[k]

    # VEP annotation
    print("VEP Annotation")
    variant_list = (
    new_df["Variant and Risk Allele"]
    .dropna()             # remove missing values
    .astype(str)          # ensure all are strings
    .unique()             # get unique entries
    .tolist()             # convert to Python list
    )

    varinat_VEP_scores = annotate_variants(variant_list)

    # Merge based on equivalent columns
    merged_df = pd.merge(
        new_df,
        varinat_VEP_scores,
        left_on="Variant and Risk Allele",
        right_on="Input",
        how="left"     # change to 'left' if you want to keep all GWAS rows
    )

    # Drop the redundant "Input" column
    merged_df.drop(columns=["Input"], inplace=True)
    return merged_df.sort_values("Chromosome")

    # return new_df.sort_values("Chromosome")

def generate_variants(studies: List[str], requested_efo:str, variants_associate_path: str) -> str:

    df = None
    try:
        # variants_associate_path = os.path.join(gwas_data_path, f'{requested_efo}.tsv')
        if not os.path.exists(variants_associate_path):
            df = filter_asso_by_efo_id(studies, requested_efo)
            if df.empty:
                return None
            df.to_csv("filtered.df")
            df = prepare_variants_data(df)
            df.to_csv(variants_associate_path, sep='\t', index=False)
            print("Generated variants data")
            
        return variants_associate_path
    except ValueError as e:
        return None

    except FileNotFoundError as e:
        raise e
    
def generate_vep(variants_associate_path: str, vep_associate_path: str):
    df = None
    try:
        # variants_associate_path = os.path.join(gwas_data_path, f'{requested_efo}.tsv')
        if os.path.exists(variants_associate_path):
            df = df.read_csv(variants_associate_path)
            df = prepare_vep_data(df)
            df.to_csv(vep_associate_path, sep='\t', index=False)
            return vep_associate_path
    
        else:
            return None
    except ValueError as e:
        return None

    except FileNotFoundError as e:
        raise e

if __name__ == "__main__":
    disease = "cardiovascular diseases"
    requested_efo = "EFO_0000319"
    with open(f"/app/res-immunology-automation/res_immunology_automation/src/scripts/cached_data_json/disease/{disease.replace(' ', '_').lower()}", "r") as f:
        import json
        data = json.load(f)
        studies = data["/genomics/gwas-studies/"]
        studies_ids = list(set([item["Study accession"] for item in gwas_studies if "Study accession" in item]))

        load_data(studies_ids, requested_efo, f"/app/res-immunology-automation/res_immunology_automation/src/scripts/cached_data_json/disease/{requested_efo}.tsv")