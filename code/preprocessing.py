"""
preprocessing.py — Data Pipeline for Chicago 311 Service Delivery Analysis

Downloads raw data from public APIs, cleans, merges, and produces/saves datasets in data/derived-data/.

Data sources:
  1. Chicago 311 Service Requests (2021–2024) — Chicago Data Portal
  2. American Community Survey 5-Year Estimates — U.S. Census Bureau
  3. Chicago Community Area Boundaries — Chicago Data Portal
  4. Chicago Census Tract Boundaries — Chicago Data Portal
"""

import os
import time
import requests
import pandas as pd
import numpy as np
import geopandas as gpd

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw-data")
DERIVED_DIR = os.path.join(BASE_DIR, "data", "derived-data")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(DERIVED_DIR, exist_ok=True)

# Constants
JOHNSON_INAUGURATION = pd.Timestamp("2023-05-15")
STUDY_START = "2021-01-01"
STUDY_END = "2024-12-31"

# URLs
# Socrata SODA API endpoint — supports $limit/$offset pagination
URL_311_API = "https://data.cityofchicago.org/resource/v6vf-nfxy.csv"
URL_COMMUNITY_AREAS = "https://data.cityofchicago.org/resource/igwz-8jzy.geojson"
URL_CENSUS_TRACTS = "https://data.cityofchicago.org/resource/74p9-q2aq.geojson"
URL_ACS = "https://api.census.gov/data/2022/acs/acs5"


# Download 311 Service Requests (paginated to bypass Socrata's default row limit)
def _get_with_retry(url, params=None, max_attempts=6, timeout=120):
    """GET request with exponential backoff retry on network errors."""
    for attempt in range(max_attempts):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as exc:
            if attempt == max_attempts - 1:
                raise
            wait = 2 ** attempt          # 1, 2, 4, 8, 16, 32 s
            print(f"\n  [retry {attempt+1}/{max_attempts-1}] {exc} — waiting {wait}s...")
            time.sleep(wait)


def download_311(output_path):
    if os.path.exists(output_path):
        print(f"Already exists: {output_path}")
        return

    PAGE_SIZE = 50_000
    all_chunks = []
    offset = 0
    print("Downloading 311 data via Socrata API (paginated)...")

    while True:
        params = {
            "$limit":  PAGE_SIZE,
            "$offset": offset,
            "$where":  f"created_date >= '{STUDY_START}' AND created_date <= '{STUDY_END}'",
            "$order":  "created_date ASC",
        }
        r = _get_with_retry(URL_311_API, params=params, timeout=120)

        chunk = pd.read_csv(pd.io.common.StringIO(r.text), low_memory=False)
        if chunk.empty:
            break

        all_chunks.append(chunk)
        offset += len(chunk)
        print(f"  Downloaded {offset:,} rows so far...", end="\r")

        if len(chunk) < PAGE_SIZE:
            break   # last page

        time.sleep(0.25)   # be polite to the API

    df_all = pd.concat(all_chunks, ignore_index=True)
    df_all.to_csv(output_path, index=False)
    print(f"\nSaved: {output_path} ({len(df_all):,} rows, "
          f"{os.path.getsize(output_path) / 1e6:.0f} MB)")


# Download ACS Census Tract Data
def download_acs(output_path):
    if os.path.exists(output_path):
        print(f"Already exists: {output_path}")
        return pd.read_csv(output_path)

    print("Downloading ACS data from Census API...")
    params = {
        "get": "B01003_001E,B19013_001E,B17001_002E,NAME",
        "for": "tract:*",
        "in": "state:17 county:031",
    }
    r = requests.get(URL_ACS, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()

    df = pd.DataFrame(data[1:], columns=data[0])
    df.rename(
        columns={
            "B01003_001E": "population",
            "B19013_001E": "median_income",
            "B17001_002E": "poverty_pop",
        },
        inplace=True,
    )
    df["geoid"] = df["state"] + df["county"] + df["tract"]
    for col in ["population", "median_income", "poverty_pop"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df.to_csv(output_path, index=False)
    print(f"  Saved: {output_path} ({len(df)} tracts)")
    return df

# Download Geographic Boundaries
def download_geojson(url, output_path, label="GeoJSON"):
    if os.path.exists(output_path):
        print(f"Already exists: {output_path}")
        return gpd.read_file(output_path)

    print(f"Downloading {label}...")
    gdf = gpd.read_file(url)
    gdf.to_file(output_path, driver="GeoJSON")
    print(f"Saved: {output_path} ({len(gdf)} features)")
    return gdf

# Clean & Process 311 Data
def clean_311(raw_path):
    print("Loading raw 311 CSV (this may take a minute)...")
    df = pd.read_csv(raw_path, low_memory=False)

    # Standardize column names to lowercase
    df.columns = df.columns.str.lower()

    # Parse dates
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["closed_date"] = pd.to_datetime(df["closed_date"], errors="coerce")

    # Filter to study period
    mask = (df["created_date"] >= STUDY_START) & (df["created_date"] <= STUDY_END)
    df = df[mask].copy()
    print(f"  Filtered to {STUDY_START}–{STUDY_END}: {len(df):,} rows")

    # Compute response time in days
    df["response_time_days"] = (
        (df["closed_date"] - df["created_date"]).dt.total_seconds() / 86400
    )
    # Remove negative response times (data errors)
    df.loc[df["response_time_days"] < 0, "response_time_days"] = np.nan

    # Time components
    df["year"] = df["created_date"].dt.year
    df["month"] = df["created_date"].dt.month
    df["year_month"] = df["created_date"].dt.to_period("M").astype(str)

    # Administration period
    df["period"] = np.where(
        df["created_date"] < JOHNSON_INAUGURATION,
        "Pre-Johnson",
        "Johnson Admin",
    )

    return df

# Spatial Joins & Feature Engineering
def assign_community_areas(df, gdf_comm):
    """Maps 311 requests to community areas via spatial join."""
    # Check if community_area column exists and has good coverage
    if "community_area" in df.columns:
        coverage = df["community_area"].notna().mean()
        print(f"Existing community_area coverage: {coverage:.1%}")
        if coverage >= 0.95:
            # Normalize to clean integer strings: '63.0' -> '63'
            df["community_area"] = (
                pd.to_numeric(df["community_area"], errors="coerce")
                .astype("Int64")
                .astype(str)
                .replace("<NA>", pd.NA)
            )
            return df

    # Spatial join for records with valid coordinates
    has_coords = df["latitude"].notna() & df["longitude"].notna()
    print(f"  Records with coordinates: {has_coords.sum():,}")

    gdf_points = gpd.GeoDataFrame(
        df.loc[has_coords],
        geometry=gpd.points_from_xy(
            df.loc[has_coords, "longitude"], df.loc[has_coords, "latitude"]
        ),
        crs="EPSG:4326",
    )
    gdf_comm_proj = gdf_comm.to_crs("EPSG:4326")

    joined = gpd.sjoin(
        gdf_points,
        gdf_comm_proj[["area_numbe", "community", "geometry"]],
        how="left",
        predicate="within",
    )

    df.loc[has_coords, "community_area"] = joined["area_numbe"].values
    df.loc[has_coords, "community_name"] = joined["community"].values
    df["community_area"] = df["community_area"].astype(str)

    coverage = (df["community_area"] != "nan").mean()
    print(f"  Community area coverage after spatial join: {coverage:.1%}")
    return df


def build_community_stats(acs, gdf_tracts, gdf_comm):
    """Aggregate ACS tract data to community area level with income quintiles."""
    # Spatial join: tract centroids → community areas
    gdf_tracts_proj = gdf_tracts.to_crs("EPSG:4326").copy()
    gdf_tracts_proj["centroid"] = gdf_tracts_proj.geometry.centroid
    gdf_centroids = gdf_tracts_proj.set_geometry("centroid")

    gdf_comm_proj = gdf_comm.to_crs("EPSG:4326")

    tract_to_ca = gpd.sjoin(
        gdf_centroids[["geoid10", "centroid"]].rename(
            columns={"geoid10": "tract_geoid"}
        ),
        gdf_comm_proj[["area_numbe", "community", "geometry"]],
        how="left",
        predicate="within",
    )

    # Merge ACS with tract→community area mapping
    acs["geoid"] = acs["geoid"].astype(str)
    tract_to_ca["tract_geoid"] = tract_to_ca["tract_geoid"].astype(str)

    acs_merged = acs.merge(
        tract_to_ca[["tract_geoid", "area_numbe", "community"]],
        left_on="geoid",
        right_on="tract_geoid",
        how="inner",
    )
    print(f"  ACS tracts matched to community areas: {len(acs_merged)}")

    # Aggregate to community area level
    ca_stats = (
        acs_merged.groupby(["area_numbe", "community"])
        .agg(
            population=("population", "sum"),
            median_income=("median_income", "median"),
            poverty_pop=("poverty_pop", "sum"),
        )
        .reset_index()
    )
    ca_stats["poverty_rate"] = ca_stats["poverty_pop"] / ca_stats["population"]

    # Income quintiles
    ca_stats["income_quintile"] = pd.qcut(
        ca_stats["median_income"],
        q=5,
        labels=["Q1 (Lowest)", "Q2", "Q3", "Q4", "Q5 (Highest)"],
    )

    return ca_stats


def enrich_311_with_demographics(df, ca_stats):
    """Join community-area demographics onto 311 data."""
    # Error Found; normalize keys in community_area and area_numbe
    df["community_area_key"] = (
        pd.to_numeric(df["community_area"], errors="coerce")
        .astype("Int64")
        .astype(str)
        .replace("<NA>", pd.NA)
    )
    ca_stats["area_numbe_key"] = (
        pd.to_numeric(ca_stats["area_numbe"], errors="coerce")
        .astype("Int64")
        .astype(str)
    )

    df = df.merge(
        ca_stats[
            ["area_numbe_key", "community", "population", "median_income",
             "income_quintile", "poverty_rate"]
        ],
        left_on="community_area_key",
        right_on="area_numbe_key",
        how="left",
        suffixes=("", "_ca"),
    )
    df.drop(columns=["community_area_key", "area_numbe_key"], inplace=True)

    coverage = df["income_quintile"].notna().mean()
    print(f"  Income quintile coverage: {coverage:.1%}")
    return df

# Main pipeline
def main():
    print("Preprocessing Pipeline — Chicago 311 Service Delivery")

    # --- Download raw data ---
    print("\nDownloading 311 Service Requests (paginated)")
    raw_311_path = os.path.join(RAW_DIR, "311_service_requests.csv")
    download_311(raw_311_path)

    print("\nDownloading ACS Census Data")
    acs_path = os.path.join(RAW_DIR, "acs_cook_county_tracts.csv")
    acs = download_acs(acs_path)
    if isinstance(acs, type(None)):
        acs = pd.read_csv(acs_path)

    print("\nDownloading Community Area Boundaries")
    comm_path = os.path.join(RAW_DIR, "community_areas.geojson")
    gdf_comm = download_geojson(URL_COMMUNITY_AREAS, comm_path, "Community Areas")

    print("\nDownloading Census Tract Boundaries")
    tract_path = os.path.join(RAW_DIR, "census_tracts.geojson")
    gdf_tracts = download_geojson(URL_CENSUS_TRACTS, tract_path, "Census Tracts")

    # clean data
    print("\nCleaning 311 data...")
    df = clean_311(raw_311_path)

    # --- Spatial joins & feature engineering ---
    print("\nBuilding features...")

    print("Assigning community areas to 311 requests...")
    df = assign_community_areas(df, gdf_comm)

    print("Building community area statistics...")
    ca_stats = build_community_stats(acs, gdf_tracts, gdf_comm)

    print("Enriching 311 data with demographics...")
    df = enrich_311_with_demographics(df, ca_stats)

    # save data
    print("\nSaving derived data...")

    csv_311_path = os.path.join(DERIVED_DIR, "311_cleaned.csv")
    df.to_csv(csv_311_path, index=False)
    print(f"Saved: {csv_311_path} ({len(df):,} rows)")

    ca_path = os.path.join(DERIVED_DIR, "community_area_stats.csv")
    ca_stats.to_csv(ca_path, index=False)
    print(f"Saved: {ca_path} ({len(ca_stats)} community areas)")

    # Copy boundary to derived-data
    gdf_comm.to_file(
        os.path.join(DERIVED_DIR, "community_areas.geojson"), driver="GeoJSON"
    )

    # Summary
    print("\nPIPELINE COMPLETE\n")
    print(f"311 requests:       {len(df):,}")
    print(f"Date range:         {df['created_date'].min()} – {df['created_date'].max()}")
    print(f"Service types:      {df['sr_type'].nunique()}")
    print(f"Community areas:    {ca_stats.shape[0]}")
    print(f"Median response:    {df['response_time_days'].median():.1f} days")
    print(f"\nPeriod breakdown:")
    print(f"{df['period'].value_counts().to_string()}")


if __name__ == "__main__":
    main()
