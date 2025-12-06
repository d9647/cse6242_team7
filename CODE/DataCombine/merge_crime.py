import os
import pandas as pd

# Canonical column order
COLUMN_ORDER = [
    "DR_NO","DATE RPTD","DATE OCC","TIME OCC","AREA","AREA NAME",
    "RPT DIST NO","PART 1-2","CRM CD","CRM CD DESC","MOCODES",
    "VICT AGE","VICT SEX","VICT DESCENT","PREMIS CD","PREMIS DESC",
    "WEAPON USED CD","WEAPON DESC","STATUS","STATUS DESC",
    "CRM CD 1","CRM CD 2","CRM CD 3","CRM CD 4",
    "LOCATION","CROSS STREET","LAT","LON",
    "GEOID","CT","ZCTA","YEAR","ZCTA_YEAR_KEY"
]

def merge_crime_csvs(input_dir, output_file):
    all_dfs = []

    for year in range(2013, 2024):
        file_path = os.path.join(input_dir, f"{year}_crime_with_geoid_zcta.csv")
        if not os.path.exists(file_path):
            print(f"skipping {year}: File not found → {file_path}")
            continue

        df = pd.read_csv(file_path)
        print(f"...loaded {year}: {df.shape[0]:,} rows")

        # --- Drop 'INDEX_RIGHT' if exists ---
        df = df.drop(columns=["INDEX_RIGHT"], errors="ignore")

        # --- Ensure key numeric columns are Int64 (nullable integer) ---
        for col in ["CT", "GEOID", "YEAR", "ZCTA"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

        # --- Reorder columns, keeping only those that exist ---
        cols = [c for c in COLUMN_ORDER if c in df.columns]
        df = df.reindex(columns=cols)

        all_dfs.append(df)

    if not all_dfs:
        print("!! No valid crime files to merge.")
        return

    merged = pd.concat(all_dfs, ignore_index=True)

    # --- Save final merged dataset ---
    merged.to_csv(output_file, index=False)
    print(f"merged {len(all_dfs)} files → {len(merged):,} total rows")
    print(f"saved merged dataset → {output_file}")

    # --- Type check summary ---
    print("\n ... final dtypes:")
    print(merged.dtypes.loc[["GEOID","CT","YEAR","ZCTA"]])

if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)
    input_dir = base_dir
    output_file = os.path.join(base_dir, "merged_crime_data.csv")

    merge_crime_csvs(input_dir, output_file)
