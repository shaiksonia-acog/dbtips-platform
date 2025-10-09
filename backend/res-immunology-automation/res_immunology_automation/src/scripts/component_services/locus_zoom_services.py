import pandas as pd
import numpy as np
import os, csv
from typing import List
# from populate_gwas_asso_data import filter_asso_by_efo_id, prepare_variants_data, fetch_ld_data

gwas_data_path = '/app/res-immunology-automation/res_immunology_automation/src/gwas_data'

# # load Asso data Filter Asso data by EFOId and generate a variant df
def filter_asso_by_efo_id(efo_ids: List[str]):
    """
    Filter the GWAS Association data for given efo_id
    """
    print("Filtering the Associations data")
    filtered_df = None
    associations_file_path = os.path.join(gwas_data_path, 'associations.tsv')
    if os.path.exists(associations_file_path):
        with open(associations_file_path, 'r') as file:
            reader = csv.DictReader(file, delimiter='\t')
            filtered_rows = [row for row in reader if any(efo_id in row.get('MAPPED_TRAIT_URI', '') for efo_id in efo_ids)]

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
                "STUDY ACCESSION": "Study Accession", "RISK ALLELE FREQUENCY": "RAF", "OR or BETA": "OR or BETA",
                "95% CI (TEXT)": "CI"
                }
    if not required_columns.issubset(df.columns):
        raise ValueError(f"TSV file must contain these columns: {required_columns}")
    
    # Add derived columns if necessary
    if "Neglog10(pvalue)" not in df.columns:
        df["P-VALUE"] = pd.to_numeric(df["P-VALUE"], errors="coerce")
        new_df['pvalue'] = df['P-VALUE']
        new_df["Neglog10(pvalue)"] = -np.log10(df["P-VALUE"].replace(0, np.nan))  # Avoid log(0) error

    # Convert types
    df["Chromosome"] = pd.Categorical(df["CHR_ID"], categories=[str(i) for i in range(1, 23)] + ["X", "Y"], ordered=True)
    new_df["Chromosome"] = df["Chromosome"].cat.remove_unused_categories()
    new_df["Position"] = pd.to_numeric(df["CHR_POS"], errors="coerce")
    new_df['rsID'] = df['SNPS']
    for k,v in other_cols.items():
        new_df[v] = df[k]
    return new_df.sort_values("Chromosome")

def load_data(efo_ids: List[str], requested_efo:str) -> str:

    df = None
    try:
        variants_associate_path = os.path.join(gwas_data_path, f'{requested_efo}.tsv')
        if not os.path.exists(variants_associate_path):
            df = filter_asso_by_efo_id(efo_ids)
            if df.empty:
                return None
            df = prepare_variants_data(df)
            df.to_csv(variants_associate_path, sep='\t', index=False)
        return variants_associate_path
    except ValueError as e:
        return None

    except FileNotFoundError as e:
        raise e
    