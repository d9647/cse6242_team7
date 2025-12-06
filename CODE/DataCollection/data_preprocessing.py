# =====================================
# CSE 6242 Team #7
# Fall 2025
# Input: Crime_Data_from_{year}_to_{year}.csv 
# Input: {year}_Population_and_Poverty_at_Split_Tract/{year}_Population_and_Poverty_at_Split_Tract.shp
# Input: {year}_Population_and_Poverty_at_Split_Tract.csv
# Input: TRACT_ZIP_03{year}.xlsx 
# Output: output/{year}_pop_census_with_geoid_zcta.csv
# Output: output/{year}_crime_with_geoid_zcta.csv
# =====================================
# Manually Download Input Files From:
# 1. https://catalog.data.gov/dataset/crime-data-from-2020-to-present
# 2. https://catalog.data.gov/dataset/crime-data-from-2010-to-2019
# 3. Tract to Zip files from: 
#       https://www.huduser.gov/apps/public/uspscrosswalk/home
# 4. Split Tract Census Datas Year By Year from: 
#       https://data.lacounty.gov/search?q=Population%20and%20Poverty%20by%20Split%20Tract


import os
import re
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point

# =====================================
# Load ZIP–Tract crosswalk once globally
# =====================================
def load_zip_crosswalk(year: int):
    """Load HUD ZIP-TRACT crosswalk and prepare GEOID->ZCTA mapping for LA County (06037)"""
    base_dir = os.path.dirname(__file__)
    crosswalk_path = os.path.join(base_dir, f"TRACT_ZIP_03{year}.xlsx")
    #normalize and standardize, only use 2024 tract to zip file:
    #if year <= 2019:
    #    crosswalk_path = os.path.join(base_dir, f"TRACT_ZIP_032019.xlsx")
    #else:
    #    crosswalk_path = os.path.join(base_dir, f"TRACT_ZIP_032024.xlsx")

    print(f"loading ZIP-Tract crosswalk from {crosswalk_path}")
    xwalk = pd.read_excel(crosswalk_path)
    xwalk.columns = xwalk.columns.str.upper().str.strip()

    # keep only LA County tracts (FIPS 06037)
    xwalk["TRACT"] = xwalk["TRACT"].astype(str).str.zfill(11)
    xwalk = xwalk[xwalk["TRACT"].str.startswith("06037")].copy()

    # keep highest RES_RATIO per tract
    xwalk = (
        xwalk.sort_values("RES_RATIO", ascending=False)
        .drop_duplicates("TRACT")
        .rename(columns={"ZIP": "ZCTA"})
    )
    # ensure ZCTA is a 5-digit string (no .0)
    xwalk["ZCTA"] = xwalk["ZCTA"].astype(str).str.split(".").str[0].str.zfill(5)
    
    print(f"prepared ZIP-Tract mapping for {len(xwalk)} LA County tracts.")
    return xwalk[["TRACT", "ZCTA"]]

def standardize_crime_headers(crime_df: pd.DataFrame):
    # capitalize all column names
    crime_df.columns = crime_df.columns.str.strip().str.upper()
    crime_df["DATE RPTD"] = pd.to_datetime(crime_df["DATE RPTD"], errors="coerce")


# =============================================
# process crime data into yearly
# add: geoid / zcta for each crime record
# output: {year}_crime_with_geoid_zcta.csv
# =============================================
def process_crime_data(crime_df: pd.DataFrame, tract_shp: str, year: int, xwalk: pd.DataFrame):
    """
    Process crime data:
    - Convert DATE RPTD and DATE OCC to datetime
    - Filter by the given YEAR
    - Spatially join to add GEOID (from tract shapefile)
    - Merge to add ZCTA (from crosswalk)
    - Output per-year CSV file
    """

    print("initial crime data summary:")
    #print(crime_df.dtypes)
    #print(crime_df.columns)

    # ensure all column names uppercase
    crime_df.columns = crime_df.columns.str.strip().str.upper()

    # convert DATE RPTD to datetime if exists
    if "DATE RPTD" in crime_df.columns:
        crime_df["DATE RPTD"] = pd.to_datetime(crime_df["DATE RPTD"], errors="coerce")

    # convert DATE OCC to datetime
    if "DATE OCC" not in crime_df.columns:
        raise ValueError("!! could not find 'DATE OCC' column in crime data.")
    crime_df["DATE OCC"] = pd.to_datetime(crime_df["DATE OCC"], errors="coerce")

    # create YEAR column (from DATE OCC)
    crime_df["YEAR"] = crime_df["DATE OCC"].dt.year

    # filter records to match only this year
    before_filter = len(crime_df)
    crime_df = crime_df[crime_df["YEAR"] == year].copy()
    print(f"filtered {len(crime_df):,}/{before_filter:,} records for year {year}")

    # ensure coordinates exist
    for col in ["LAT", "LON"]:
        if col not in crime_df.columns:
            raise ValueError(f"!! missing column '{col}' in crime data.")

    # drop invalid coordinate rows
    crime_df = crime_df.dropna(subset=["LAT", "LON"])
    print(f"{len(crime_df):,} records with valid coordinates.")

    # convert to GeoDataFrame
    gdf_points = gpd.GeoDataFrame(
        crime_df,
        geometry=gpd.points_from_xy(crime_df["LON"], crime_df["LAT"]),
        crs="EPSG:4326"
    )

    # load tract shapefile
    print(f"loading tract shapefile {tract_shp}")
    tracts = gpd.read_file(tract_shp).to_crs("EPSG:4326")

    # normalize tract column name to CT
    if "CT20" in tracts.columns:
        tracts = tracts.rename(columns={"CT20": "CT"})
    elif "CT10" in tracts.columns:
        tracts = tracts.rename(columns={"CT10": "CT"})
    elif "CT" not in tracts.columns:
        raise ValueError("!! neither 'CT20' nor 'CT10' exists in tracts file.")

    # ensure GEOID exists
    if "GEOID" not in tracts.columns:
        tracts["GEOID"] = "06037" + tracts["CT"].astype(str).str.zfill(6)
        print("GEOID column created in tracts.")

    # spatial join: assign GEOID to each crime record
    joined = gpd.sjoin(gdf_points, tracts[["GEOID", "CT", "geometry"]], how="left", predicate="within")
    crime_with_geoid = pd.DataFrame(joined.drop(columns="geometry"))
    print(f"spatial join complete — {crime_with_geoid['GEOID'].notna().sum()} records matched with GEOID.")

    # add ZCTA using crosswalk
    crime_with_geoid = crime_with_geoid.merge(xwalk, left_on="GEOID", right_on="TRACT", how="left")
    crime_with_geoid = crime_with_geoid.drop(columns=["TRACT"])
    print(f"added ZCTA (matched: {crime_with_geoid['ZCTA'].notna().sum()}, unmatched: {crime_with_geoid['ZCTA'].isna().sum()})")

    # create ZCTA_YEAR_KEY — only if ZCTA is not NaN
    crime_with_geoid["ZCTA_YEAR_KEY"] = crime_with_geoid.apply(
        lambda row: f"{int(row['ZCTA'])}_{int(row['YEAR'])}"
        if pd.notna(row["ZCTA"]) and pd.notna(row["YEAR"])
        else pd.NA,
        axis=1
    )

    # capitalize all final headers for consistency
    crime_with_geoid.columns = crime_with_geoid.columns.str.upper()

    print("** FINAL crime data summary:")
    #print(crime_with_geoid.dtypes)
    #print(crime_with_geoid.columns)

    # output file per year
    output_path = os.path.join(os.path.dirname(__file__), f"output/{year}_crime_with_geoid_zcta.csv")
    crime_with_geoid.to_csv(output_path, index=False)
    print(f"** saved {year} crime dataset ----> {output_path}")

    return output_path


def convert_float_to_int(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.select_dtypes(include=["float64"]).columns:
        # keep only specific float columns
        if re.match(r"(POP\d{2}_DENSITY|POV\d{2}_PERCENT)", col) \
           or col in ["SHAPE__AREA", "SHAPE__LENGTH", "AREA_SQMIL"]:
            continue
        df[col] = df[col].fillna(0).astype(int)

    return df


def standardize_year_headers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove 2-digit year codes (e.g., 17, 22) from column names 
    like POP22_AGE_0_4 or POV17_TOTAL → POP_AGE_0_4, POV_TOTAL.
    """
    new_columns = {}
    for col in df.columns:
        new_col = re.sub(r'^(POP|POV)\d{2}_', r'\1_', col)  # remove 2-digit year after POP/POV
        new_columns[col] = new_col
    df = df.rename(columns=new_columns)
    return df



def standardize_census_headers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize census dataframe headers to make columns consistent across years.
    Rules:
    1. SPA_XXXX or SPAXX → SPA
    2. HD_XXXX or HDXX → HD
    3. CT10, CT20 → CT
    4. FIPXX → FIP
    5. Drop CT10FIPXX, CSA, and CT20FIPXXCSA columns if present
    """
    # drop inconsistent combined columns if they exist
    drop_cols = [col for col in df.columns if re.match(r'CT\d{2}FIP\d{2}', col)] + ["CSA"] + \
                [col for col in df.columns if re.match(r'CT\d{2}FIP\d{2}CSA', col)] 
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

    rename_map = {}
    for col in df.columns:
        new_col = col

        # 1) SPA_XXXX or SPAXX -> SPA
        if re.match(r"^SPA(_\d{4}|\d{2})$", col):
            new_col = "SPA"

        # 2) HD_XXXX or HDXX -> HD
        elif re.match(r"^HD(_\d{4}|\d{2})$", col):
            new_col = "HD"

        # 3) CT10 or CT20 -> CT
        elif re.match(r"^CT\d{2}$", col):
            new_col = "CT"

        # 4) FIPXX -> FIP
        elif re.match(r"^FIP\d{2}$", col):
            new_col = "FIP"

        rename_map[col] = new_col

    # apply renaming
    df = df.rename(columns=rename_map)
    return df

def fix_2023_header_issues(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "POPP23_AGE_15_17": "POP23_AGE_15_17",
        "AREA-SQMIL": "AREA_SQMIL",
        "POV23_RATE": "POV23_PERCENT"
    }
    df = df.rename(columns=rename_map)
    
    return df

def fix_minor_header_typos(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "OBJECTID_1": "OBJECTID",
        "POV_HNPL": "POV_HNPI",
        "POP_HNPA": "POP_HNPI",
        "POV_PERCENT":"POV_RATE"
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    return df

# =============================================
# process census data into yearly
# add: geoid / zcta for each census record
# note: map with xwalk track->zcta file (yearly)
# output: {year}_pop_census_with_geoid_zcta.csv
# =============================================
def process_population_data(pop_csv: str, year: int, xwalk: pd.DataFrame):
    #debug
    #print(list(xwalk.columns))
    #return

    """add GEOID+ZCTA to population file"""
    print(f"loading population data from {pop_csv}")
    pop_df = pd.read_csv(pop_csv)
    pop_df.columns = pop_df.columns.str.strip().str.upper()
    
    if year == 2023:
        pop_df = fix_2023_header_issues(pop_df)
        #print(pop_df.dtypes)
    
    #print(pop_df.head())
    #print(pop_df.dtypes)
    convert_float_to_int(pop_df)
    pop_df = standardize_year_headers(pop_df)
    pop_df = standardize_census_headers(pop_df)
    pop_df = fix_minor_header_typos(pop_df)
    
    #print(pop_df.dtypes)
    
    #debug only
    #print(list(pop_df.columns))
    #return

    # dnsure GEOID
    if "GEOID" not in pop_df.columns:
        pop_df["GEOID"] = "06037" + pop_df["CT"].astype(str).str.zfill(6)
        print("GEOID column created in population file.")

    # add ZCTA
    pop_df = pop_df.merge(xwalk, left_on="GEOID", right_on="TRACT", how="left")
    pop_df = pop_df.drop(columns=["TRACT"])

    pop_df["ZCTA"] = pd.to_numeric(pop_df["ZCTA"], errors="coerce").astype("Int64")

    #print(pop_df.dtypes)
    # Find unmatched rows (GEOIDs with no matching TRACT in xwalk)
    unmatched = pop_df[pop_df['ZCTA'].isna()] if 'ZCTA' in pop_df.columns else pop_df[pop_df['TRACT'].isna()]

    if not unmatched.empty:
        print(f"!! {len(unmatched)} GEOID(s) had no matching TRACT in xwalk:")
        print(unmatched[['GEOID']].head(20))  # show first 20 for preview
    else:
        print("all GEOIDs successfully matched to a TRACT.")
    
    print("added ZCTA to population data.")

    # Output
    output_path = os.path.join(os.path.dirname(__file__), f"output/{year}_pop_census_with_geoid_zcta.csv")
    pop_df.to_csv(output_path, index=False)
    print(f"saved population data with geoid+zcta → {output_path}")
    return output_path


def main(year: int, xwalk: pd.DataFrame, crime_df: pd.DataFrame):
#def main(year: int, crime_df: pd.DataFrame):
    base_dir = os.path.dirname(__file__)

    # Load crosswalk once
    #xwalk = load_zip_crosswalk(year)
    tract_shp = os.path.join(base_dir, f"{year}_Population_and_Poverty_at_Split_Tract/{year}_Population_and_Poverty_at_Split_Tract.shp")
    pop_csv = os.path.join(base_dir, f"{year}_Population_and_Poverty_at_Split_Tract.csv")

    if year == 2023:
        tract_shp = os.path.join(base_dir, f"{year}_Population_and_Poverty_at_Split_Tract/CT20FIP23CSA_POP23_POV23.shp")
    
    crime_output = process_crime_data(crime_df, tract_shp, year, xwalk)
    pop_output = process_population_data(pop_csv, year, xwalk)

    print("\n** processing complete!\n")
    print(f"** crime data with geoid+zcta -> {crime_output}")
    print(f"** population data with geoid+zcta -> {pop_output}")


if __name__ == "__main__":
    
    base_dir = os.path.dirname(__file__)
    
    # Pick source CSVs and shapefile
    crime_csv_1 = os.path.join(base_dir, "Crime_Data_from_2010_to_2019.csv")
    crime_csv_2 = os.path.join(base_dir, "Crime_Data_from_2020_to_Present.csv")

        
    print(f".... loading crime data........")
    crime_df_1 = pd.read_csv(crime_csv_1)
    crime_df_2 = pd.read_csv(crime_csv_2)
    
    standardize_crime_headers(crime_df_1)
    standardize_crime_headers(crime_df_2)
    
    # Load crosswalk once
    xwalk = load_zip_crosswalk(2019)
    main(2010, xwalk, crime_df_1)
    main(2011, xwalk, crime_df_1)
    main(2012, xwalk, crime_df_1)
    main(2013, xwalk, crime_df_1)
    main(2014, xwalk, crime_df_1)
    main(2015, xwalk, crime_df_1) 
    main(2016, xwalk, crime_df_1)
    main(2017, xwalk, crime_df_1)
    main(2018, xwalk, crime_df_1)
    main(2019, xwalk, crime_df_1)
    
    xwalk = load_zip_crosswalk(2024)
    main(2020, xwalk, crime_df_2)
    main(2021, xwalk, crime_df_2)
    main(2022, xwalk, crime_df_2)
    main(2023, xwalk, crime_df_2)
