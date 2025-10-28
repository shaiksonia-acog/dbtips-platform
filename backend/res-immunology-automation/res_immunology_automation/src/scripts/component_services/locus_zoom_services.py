import pandas as pd
import numpy as np
import os, csv
from .vep_annotation_service import annotate_variants
# from populate_gwas_asso_data import filter_asso_by_efo_id, prepare_variants_data, fetch_ld_data

gwas_data_path = '/app/res-immunology-automation/res_immunology_automation/src/gwas_data'

# # load Asso data Filter Asso data by EFOId and generate a variant df
def filter_asso_by_efo_id(efo_id: str):
    """
    Filter the GWAS Association data for given efo_id
    """
    print("Filtering the Associations data")
    filtered_df = None
    associations_file_path = os.path.join(gwas_data_path, 'associations.tsv')
    if os.path.exists(associations_file_path):
        with open(associations_file_path, 'r') as file:
            reader = csv.DictReader(file, delimiter='\t')
            filtered_rows = [row for row in reader if efo_id in row.get('MAPPED_TRAIT_URI', '')]

        if len(filtered_rows) > 0:
            filtered_df = pd.DataFrame(filtered_rows)
            # print("filtered_df")
            # print(filtered_df.shape)
            # print(filtered_df.head)
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

    # VEP annotation
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

def load_data(efo_id: str):

    df = None
    try:
        variants_associate_path = os.path.join(gwas_data_path, f'{efo_id}.tsv')
        print("variants_associate_path")
        print(variants_associate_path)

        print(os.path.exists(variants_associate_path))
           

        if not os.path.exists(variants_associate_path):
            print("calling filter_asso_by_efo_id")
            df = filter_asso_by_efo_id(efo_id)
            if df.empty:
                return None
            df = prepare_variants_data(df)
            df.to_csv(variants_associate_path, sep='\t', index=False)
        return variants_associate_path
    except ValueError as e:
        return None

    except FileNotFoundError as e:
        raise e





# # Path to your TSV file
# file_path = "/app/res-immunology-automation/res_immunology_automation/src/gwas_data/EFO_0000319.tsv"

# # Read the TSV file
# df = pd.read_csv(file_path, sep="\t")

# # Extract the 'rsid' column as a list
# rsid_list = df["rsID"].dropna().astype(str).tolist()

# print(f"Total rsIDs found: {len(rsid_list)}")
# print(rsid_list)  # show first 10 for sanity check

load_data("EFO_0000319")
    