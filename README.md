# Chicago 311 Service Delivery Analysis

This project processes and visualizes Chicago 311 service request data (2021–2024) and American Community Survey demographics to analyze service delivery patterns around the Johnson administration transition.

**Dashboard:** [from-request-to-resolution.streamlit.app](https://from-request-to-resolution.streamlit.app)

##### Group Members
- Iraj Butt — iraj
- Fatima Hussain — fatimazehra
- Faizan Rashid — faizan1

## Setup

```
conda env create -f environment.yml
conda activate chicago_311
```

## Project Structure

```
data/
    raw-data/                     # Raw data files (downloaded by preprocessing.py)
        311_service_requests.csv  # Chicago 311 requests (2021–2024)
        acs_cook_county_tracts.csv # American Community Survey data
    derived-data/                 # Processed data and output files
        311_cleaned.parquet       # Cleaned 311 data (~31 MB)
        community_area_stats.csv  # Aggregated community area demographics
        community_areas.geojson   # Chicago community area boundaries
code/
    preprocessing.py              # Downloads, cleans, and processes all data
    generate_figures.qmd          # Generates all 11 static figures
streamlit-app/
    app.py                        # Interactive Streamlit dashboard
    utils.py                      # Shared utility functions
    requirements.txt              # Streamlit-specific dependencies
final_project.qmd                 # Project writeup (renders to PDF and HTML)
```

## Usage

1. Run preprocessing to download and clean data:

    ```
    python code/preprocessing.py
    ```

    This downloads 311 requests from the Socrata API, ACS data from the Census Bureau, and geographic boundaries from the Chicago Data Portal. Output is saved to `data/derived-data/`. The raw 311 CSV exceeds 100 MB and is excluded from the repository via `.gitignore`; rerun preprocessing to regenerate it.

2. Render the writeup:

    ```
    quarto render final_project.qmd
    ```

3. Run the dashboard locally:

    ```
    streamlit run streamlit-app/app.py
    ```

## Data Sources

- **Chicago 311 Service Requests (2021–2024):** City of Chicago Data Portal (Socrata API) — request dates, completion dates, service categories, and geolocation (326,000+ records)
- **American Community Survey 5-Year Estimates:** U.S. Census Bureau — population, median income, and poverty rates at the census-tract level for Cook County
- **Chicago Community Area Boundaries:** City of Chicago Data Portal — GeoJSON boundaries for Chicago's 77 community areas
