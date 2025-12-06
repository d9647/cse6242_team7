===========================================================
PROJECT OVERVIEW
===========================================================
Title: Smart Crime Insights: Patterns and Demographics Analysis in Los Angeles City
Description:
    This project analyzes Los Angeles crime data to uncover temporal, spatial,
    and demographic patterns and to assess how the COVID-19 pandemic affected
    crime dynamics. It integrates census data, spatial regression, time-series
    forecasting, and interactive dashboards.

team007final/
├── CODE/
│    ├── DataCollection/
│    │     ├── data_preprocessing.py
│    │     
│    ├── DataCombine/
│    │     ├── merge_crime.py
│    │     ├── merge_pop_census.py
│    │
│    ├── LocationGeocoding/
│    │     ├── crime_data_geocode.ipynb
│    │
│    ├── GWR/
│    │     ├── (spatial regression notebooks & scripts)
│    │
│    ├── TimeSeries/
│    │     ├── TimeSeriesStudy.ipynb
│    │
│    ├── Smart Crime Insights_Patterns and Demographics Analysis in Los Angeles City CSE 6242 Team007.twbx
│
├── DOC/
│    ├── team007poster.pdf
│    ├── team007report.pdf
│
└── README.txt   (this file)

Note:
    Due to file size restrictions, raw and processed data files are not included
    in this submission. Initial input files must be downloaded manually. Users
    may need to rename datasets as required by the scripts and must place all
    data files into the appropriate /CODE/ subfolders before running any steps
    beginning with DataCombine onward.

    The dashboard is also accessible online at:
    https://public.tableau.com/shared/XG84W6H94?:display_count=n&:origin=viz_share_link

===========================================================
GLOBAL ENVIRONMENT & DEPENDENCIES
===========================================================
Recommended environment:
    - Python 3.9+ (conda/virtualenv)
    - Jupyter Notebook / JupyterLab
    - Tableau Desktop / Tableau Public

Core Python packages (used across steps):
    - General: pandas, numpy, matplotlib, seaborn, logging, warnings, os, re, time
    - Geospatial: geopandas, shapely, fiona, pyproj, mgwr, pysal
    - Stats / ML / Time Series: scipy, statsmodels, scikit-learn, prophet
    - Geocoding: geopy
    - Optional: tqdm

Example conda setup:

    conda create -n la_crime_env python=3.9
    conda activate la_crime_env
    conda install pandas numpy matplotlib seaborn scipy scikit-learn statsmodels
    conda install -c conda-forge geopandas shapely fiona pyproj pysal mgwr prophet geopy
    pip install tqdm

===========================================================
1. DATA COLLECTION
===========================================================
Location:
    - Code: Code/DataCollection/

Purpose:
    Standardize and geo-enrich LA crime and census data by assigning Census
    Tract GEOIDs and ZCTAs using tract shapefiles and HUD crosswalks. Output
    yearly, harmonized datasets for downstream steps.

Inputs (download manually):
    1) Crime:
       - Crime_Data_from_2010_to_2019.csv  
       - Crime_Data_from_2020_to_Present.csv  

    2) HUD tract–ZIP crosswalk:
       - TRACT_ZIP_032019.xlsx (2010–2019)
       - TRACT_ZIP_032024.xlsx (2020–2023)

    3) Census split-tract (per year):
       - {year}_Population_and_Poverty_at_Split_Tract.csv
       - {year}_Population_and_Poverty_at_Split_Tract.shp

Recommended local layout:

    Data/DataCollection/
        Crime_Data_from_2010_to_2019.csv
        Crime_Data_from_2020_to_Present.csv
        TRACT_ZIP_032019.xlsx
        TRACT_ZIP_032024.xlsx
        {year}_Population_and_Poverty_at_Split_Tract.*
        output/   (created by script)

Processing script:
    - File: Code/DataCollection/data_preprocessing.py

Key functions:
    • load_zip_crosswalk(year)
        - Load HUD crosswalk, filter LA County (FIPS 06037), keep ZIP with
          highest RES_RATIO.

    • process_crime_data(crime_df, tract_shp, year, xwalk)
        - Standardize columns, convert dates, filter by YEAR.
        - Spatial join with tract shapefile for GEOID/CT.
        - Add ZCTA via crosswalk and create ZCTA_YEAR_KEY.

    • process_population_data(pop_csv, year, xwalk)
        - Align census column names (POP/POV, CT/FIP).
        - Fix header inconsistencies, create GEOID if needed.
        - Attach ZCTA via crosswalk, output standardized yearly file.

    • main(year, xwalk, crime_df)
        - Orchestrates yearly processing and writes to output/.

Outputs (per year, in Data/DataCollection/output/):
    - {year}_crime_with_geoid_zcta.csv
    - {year}_pop_census_with_geoid_zcta.csv

Dependencies:
    - pandas, numpy, geopandas, shapely, re, os, fiona, pyproj, (optional) tqdm

Run example:
    conda activate la_crime_env
    cd team007final/CODE/DataCollection
    python data_preprocessing.py

===========================================================
2. DATA COMBINE
===========================================================
Location:
    - Code: Code/DataCombine/

Purpose:
    Merge yearly crime and population outputs (2010–2023) into two
    consolidated datasets for time series, GWR/OLS, and Tableau.

Code files:
    - merge_crime.py
    - merge_pop_census.py

Inputs (from step 1, placed under Data/DataCombine/):
    - 2010_crime_with_geoid_zcta.csv
    - 2010_pop_census_with_geoid_zcta.csv
    - ...
    - 2023_crime_with_geoid_zcta.csv
    - 2023_pop_census_with_geoid_zcta.csv

Outputs (Data/DataCombine/):
    - merged_crime_data.csv
    - merged_population_census.csv

Processing details:
    merge_crime.py
        - Load yearly *_crime_with_geoid_zcta.csv (e.g., 2013–2023).
        - Drop redundant columns (e.g., INDEX_RIGHT).
        - Cast CT, GEOID, YEAR, ZCTA to Int64 where applicable.
        - Reorder columns to a canonical schema.
        - Concatenate all years → merged_crime_data.csv.

    merge_pop_census.py
        - Load yearly *_pop_census_with_geoid_zcta.csv.
        - Coerce ZCTA to Int64 and align YEAR.
        - Concatenate with aligned columns.
        - Add ZCTA_YEAR_KEY = "<ZCTA>_<YEAR>".
        - Save merged_population_census.csv.

Dependencies:
    - pandas, numpy, os

Run example:
    conda activate la_crime_env
    cd team007final/CODE/DataCombine
    python merge_crime.py
    python merge_pop_census.py

===========================================================
3. LOCATION GEOCODING
===========================================================
Location:
    - Code: Code/LocationGeocoding/

Purpose:
    Geocode crime records with LAT = 0 and LON = 0 to improve spatial
    completeness for GWR/OLS and Tableau maps.

Code:
    - crime_data_geocode.ipynb

Processing:
    - Load merged_crime_data.csv (from DataCombine).
    - Filter LAT == 0 and LON == 0.
    - Clean LOCATION (uppercase, trim, expand abbreviations).
    - Build address:
          "<standardized LOCATION>, Los Angeles, CA, USA"
    - Use geopy + Nominatim + RateLimiter to geocode.
    - Save updated rows with new LAT/LON to CSV.

Input (from step 2):
    - Data/LocationGeocoding/merged_crime_data.csv
      (copy of Data/DataCombine/merged_crime_data.csv)

Output:
    - Data/LocationGeocoding/crime_data_geoinfo_missing_geocoded.csv

Dependencies:
    - pandas, geopy, re, time

Note:
    - Optionally merge the geocoded LAT/LON back into merged_crime_data.csv
      before GWR.

Run example:
    conda activate la_crime_env
    cd team007final/CODE/LocationGeocoding
    jupyter notebook crime_data_geocode.ipynb

===========================================================
4. TIME SERIES FORECASTING
===========================================================
Location:
    - Code: Code/TimeSeries/

Code:
    - TimeSeriesStudy.ipynb

Data used (from steps 2 & 3, under Data/TimeSeries/):
    - Merge_populationone_census.csv
        (copy of merged_population_census.csv)
    - merged_crime_racecode_crimeCode.csv
        (merged_crime_data.csv joined with crime_data_geoinfo_missing_geocoded.csv)

Description:
    Notebook that merges crime + demographic data, selects key predictors
    for monthly crime counts, and fits SARIMAX and Prophet models. Produces
    2024–2025 forecasts and evaluation metrics.

Run:
    1) Open in Colab or local Jupyter.
    2) Point file paths to Data/TimeSeries/.
    3) If Prophet import fails, use the helper cells at the top (uncomment,
       re-run from top).
    4) Generate forecasts, plots, and summary tables.

Typical outputs:
    - Model evaluation table and time-series plots.
    - Optional PNG forecast charts.
    - Optional monthly aggregated CSV for Tableau.
    - Optional crime_population_merged.csv → filtered_crime_with_census.csv
      for GWR input.

Dependencies:
    - logging, warnings, os
    - pandas, numpy, seaborn, matplotlib
    - scipy.stats (pearsonr, spearmanr)
    - statsmodels (incl. SARIMAX, VIF)
    - scikit-learn (StandardScaler, LassoCV, RandomForestRegressor, metrics)
    - prophet

===========================================================
5. GEOGRAPHIC WEIGHTED REGRESSION (GWR) & OLS
===========================================================
Location:
   - Code: Code/GWR/

Purpose:
    Quantify how relationships between crime and socio-demographic factors
    vary across LA ZCTAs, using OLS as a global baseline and GWR for
    spatially varying coefficients.

Code:
    - Crime Research On LA City Based On GWR.ipynb

Processing:
    - Load ZCTA-level merged crime + population data.
    - Clip/clean geometries to LA City.
    - Check multicollinearity via VIF and select variables.
    - Fit global OLS.
    - Fit GWR with optimal bandwidth.
    - Export coefficients, residuals, and diagnostics.
    - Cluster residuals to identify hotspots and patterns.

Inputs (from steps 1 & 4):
    - Data/GWR/filtered_crime_with_census.csv
    - Data/GWR/la_city_zcta.geojson

Outputs (Data/GWR/output/):
    - ols_summary.csv
    - resid_ranges.csv
    - model_kpis.csv
    - clusters_by_year_K5.csv
    - la_zcta_years.geojson

Dependencies:
    - mgwr, geopandas, pysal, statsmodels
    - pandas, numpy
    - matplotlib, seaborn
    - shapely

Run example:
    conda activate la_crime_env
    cd team007final/CODE/GWR
    jupyter notebook
    (open the main GWR notebook and run all cells)

===========================================================
6. TABLEAU DASHBOARD
===========================================================
Location:
    - Code: Code/Tableau/
    - Packaged workbook:
        CODE/Smart Crime Insights_Patterns and Demographics Analysis in Los Angeles City CSE 6242 Team007.twbx

Purpose:
    Visualize descriptive, temporal, and spatial crime patterns plus
    model outputs (SARIMAX/Prophet, GWR/OLS, clustering) at the city
    and ZCTA levels.

Key inputs (from steps 4 & 5, under Data/Tableau/):
    • crime_monthly_2013_2025_prophet_combined.csv
    • zcta_crime_monthly_2013_2025_sarimax.xlsx
    • merged_crime_racecode_crimeCode.csv
    • Merge_populationone_census.csv
    • la_zcta_years.csv

Use in Tableau to build:
    - Crime distribution and density maps.
    - Trend/seasonality views.
    - Demographic correlation dashboards.
    - Pre/post COVID comparison.
    - ZCTA-level drill-downs and hotspot views.

Outputs (not stored in repo):
    - Final Tableau workbook in Tableau Cloud / local.
    - Screenshots used in poster and report.

Open packaged dashboard:
    1) Launch Tableau.
    2) Open the .twbx file under CODE/.
    3) Re-map data sources to your local Data folders if requested.

===========================================================
7. EXECUTION ORDER
===========================================================
Recommended sequence:

    1. DataCollection  
    2. DataCombine  
    3. LocationGeocoding  
    4. TimeSeries  
    5. GWR / OLS / Clustering  
    6. Tableau  

Notes:
    - Run DataCombine before LocationGeocoding, TimeSeries, and GWR.
    - Run LocationGeocoding before GWR for better spatial accuracy.
    - Double-check file paths in each script/notebook.
    - Some export cells in TimeSeries are turned off by default—enable them
      when you need outputs for Tableau or the report.

===========================================================
8. CONTACT / CONTRIBUTORS
===========================================================
Team 7:
    Ren Chao, Yiwei Chen, Wee Ding Ng, Chen Shi, Xuhua Tao, Shibo Zhao

Affiliation:
    Georgia Tech – CSE6242 Team 007
Date:
    11/14/2025

===========================================================
END OF README
===========================================================

