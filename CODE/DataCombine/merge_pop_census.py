import os
import pandas as pd

# Define the canonical column order
COLUMN_ORDER = [
    'OBJECTID', 'CT', 'FIP', 'CITY',
    'SPA', 'SPA_NAME', 'HD', 'HD_NAME',
    'POP_AGE_0_4', 'POP_AGE_5_9', 'POP_AGE_10_14', 'POP_AGE_15_17',
    'POP_AGE_18_19', 'POP_AGE_20_24', 'POP_AGE_25_29', 'POP_AGE_30_34',
    'POP_AGE_35_44', 'POP_AGE_45_54', 'POP_AGE_55_64', 'POP_AGE_65_74',
    'POP_AGE_75_84', 'POP_AGE_85_100',
    'POP_WHITE', 'POP_BLACK', 'POP_AIAN', 'POP_ASIAN', 'POP_HNPI', 'POP_HISPANIC',
    'POP_MALE', 'POP_FEMALE',
    'POV_WHITE', 'POV_BLACK', 'POV_AIAN', 'POV_ASIAN', 'POV_HNPI', 'POV_HISPANIC',
    'POP_TOTAL', 'POV_TOTAL',
    'AREA_SQMIL', 'POP_DENSITY', 'POV_RATE',
    'SHAPE__AREA', 'SHAPE__LENGTH',
    'GEOID', 'ZCTA', 'YEAR','ZCTA_YEAR_KEY'
]

def validate_df(df):
    # --- DTYPE SUMMARY ---
    print(df.dtypes.value_counts())
    print("-" * 60)
    #print(df.dtypes)
    print("-" * 60)
    print(df.columns)
    print("-" * 60)

def merge_yearly_population_data(start_year: int = 2013, end_year: int = 2023):
    """
    Merge yearly population CSV files (e.g., 2013-2023) into one combined CSV.
    Each input file must be named like: <year>_Population_With_GeoID_ZCTA.csv
    Output is saved as: merged_population_census.csv in the same folder.
    """
    base_dir = os.path.dirname(__file__)
    output_file = os.path.join(base_dir, "merged_population_census.csv")

    all_dfs = []

    for year in range(start_year, end_year + 1):
        file_path = os.path.join(base_dir, f"{year}_pop_census_with_geoid_zcta.csv")
        if not os.path.exists(file_path):
            print(f"skipping {year}: file not found → {file_path}")
            continue

        df = pd.read_csv(file_path)
        df["YEAR"] = year
        df["ZCTA"] = pd.to_numeric(df["ZCTA"], errors="coerce").astype("Int64")
        
        validate_df(df)
        
        all_dfs.append(df)
        print(f"...loaded {year} ({len(df):,} rows)")

    if not all_dfs:
        print("!! no valid data files found — nothing to merge.")
        return



    # Align all columns in case some years differ slightly
    merged_df = pd.concat(all_dfs, ignore_index=True, sort=True)

    # --- Add derived key column ---
    merged_df["ZCTA_YEAR_KEY"] = merged_df.apply(
        lambda row: f"{int(row['ZCTA'])}_{row['YEAR']}"
        if pd.notna(row["ZCTA"])
        else pd.NA,
        axis=1
    )


    # Reorder columns explicitly
    merged_df = merged_df[COLUMN_ORDER]

    merged_df.to_csv(output_file, index=False)
    print(f"\n merged {len(all_dfs)} years → {len(merged_df):,} total rows")
    print(f"Saved merged dataset to: {output_file}")
    
    




merge_yearly_population_data()
