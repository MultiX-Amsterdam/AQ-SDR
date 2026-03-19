
import os
import numpy as np 
import json
import shutil
import requests
import zipfile
import sys
import time
import pandas as pd
from pathlib import Path

import matplotlib.pyplot as plt
import geopandas as gpd
import multiprocessing as mp

from shapely.geometry import Point


from utils.geoutils import *
from preprocessing_scripts import metadata_creation 
from preprocessing_scripts import create_lcs_only




import argparse

import random
import time

start = time.time()

SEED=1999
def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    print(f'Seed set to: {seed}')

LAST_UPDATE = 2025
DOWNLOAD_LUCHTMEETNETCSVS = False

parser = argparse.ArgumentParser(description="Process directory and config arguments.")

parser.add_argument("--eu_data", required=True, help="Path to eu_data, where original data is from")
parser.add_argument("--dummy_holder", default="/tmp/dummy_holder", required=False, help="Path to DUMMY_HOLDER")

args = parser.parse_args()

DUMMY_HOLDER = args.dummy_holder
eu_data = args.eu_data
FINAL_DIR = os.path.join(eu_data,'luchtmeetnet_csvs_hold')

print("FINAL_DIR:", FINAL_DIR)
print("DUMMY_HOLDER:", DUMMY_HOLDER)
print("eu_data:", eu_data)


required_subdirs = [
    "luchtmeetnet_csvs",
]

# Check eu_data
if not os.path.isdir(eu_data):
    sys.stderr.write(f"Error: eu_data does not exist or is not a directory: {eu_data}\n")
    sys.exit(1)

# Check required subdirectories
missing = []
for subdir in required_subdirs:
    path = os.path.join(eu_data, subdir)
    if not os.path.isdir(path):
        missing.append(subdir)

if missing:
    sys.stderr.write("Error: You cannot start without eu_data having required data. Make sure the naming is identical as well. eu_data is missing required subdirectories:\n")
    for m in missing:
        sys.stderr.write(f"  - {m}\n")
    sys.exit(1)



for path in [FINAL_DIR, DUMMY_HOLDER]:
    if not os.path.exists(path):
        print(f" {path} does not exist. Creating directory.")
        os.makedirs(path, exist_ok=True)
    else:
        print(f"{path} already exists. We recommend you delete both before starting to avoid any unexpected overwriting. The code will continue running.")



#Example of the paths I used:
# FINAL_DIR = '/home/dum/preprocessed_final'
# DUMMY_HOLDER = '/home/dum/dummy_trial'
# eu_data = '/home/dum/eu_data/'
# KEEP_DUMMY = True

# Variable mapping dictionary

variable_mapping = {
    'PM10': 'pm10',
    'P1': 'pm10',
    'P2': 'pm25',
    'SO2': 'so2',
    'PM2.5': 'pm25',
    'PM25': 'pm25',
    'NO2': 'no2',
    'NO': 'no',
    'humidity': 'rh',
    'U': 'rh',
    'temperature': 'temp',
    'T': 'temp',
    'O3': 'o3',
    'O':'o',
    'CO': 'co',
    'Ox': 'ox',
    'NH3':'nh3',
    'NOx':'nox',
}


val_id = 'VAL_PRE'
metadata_creation.ROOT = f'{FINAL_DIR}/data'
create_lcs_only.ROOT = f'{FINAL_DIR}/data'
FULL_METADATA_PATH = f'{FINAL_DIR}/metadata/full_metadata.json'
FULL_GRIDS_PATH = f'{FINAL_DIR}/metadata/grids/gridded_5km.json'
STATIONS_WITHIN_GRIDS_PATH = f'{FINAL_DIR}/metadata/stations_within_grids/stations_within_grids_5000.json'
LCS_BULK_PATH = f'{FINAL_DIR}/final_dataset/prepared_lcs_bulk'
TEST_SET_PATH = f'{FINAL_DIR}/final_dataset/pre_prepared_datasets_unfiltered'


OFFICIAL_STATIONS_ROOT = f'{eu_data}/luchtmeetnet_csvs'

LUCHTMEETNET_CSV_METADATA_PATH = f'{OFFICIAL_STATIONS_ROOT}/luchtmeetnet_meetlocaties.csv' #https://data.rivm.nl/data/luchtmeetnet/Metadata/luchtmeetnet_meetlocaties.csv
# Paths
official_station_dummy = f'{DUMMY_HOLDER}/luchtmeetnet_csvs'

zip_dir = f'{OFFICIAL_STATIONS_ROOT}/zipfiles'
extract_dir = f'{official_station_dummy}/all_years_official'
clipped_dir = f'{official_station_dummy}/all_years_official_clipped'
separated_dir = f"{official_station_dummy}/separated_dir"
final_official_station = f"{official_station_dummy}/final_official_station"
luchtmeetnet_csv_dbscan = f"{FINAL_DIR}/luchtmeetnet_csvs_dbscan"

source_root = DUMMY_HOLDER
target_root = FINAL_DIR


root_sencom_id = f'{DUMMY_HOLDER}/sencom_id'
sencom_root = f'{DUMMY_HOLDER}/sencom_root'
sencom_final_root = f'{DUMMY_HOLDER}/sencom_final_root'
sencom_dbscan_root = f'{DUMMY_HOLDER}/sencom_final_root_dbscan'
root_sencom_hourly = f'{eu_data}/sencom_hourly'


# new_luchtmeetnet_csvs_root = f'{DUMMY_HOLDER}/luchtmeetnet_csvs_dbscan'
# luchtmeetnet_csvs_root = f'{eu_data}/luchtmeetnet_csvs'

lucht_root_dbscan = f'{DUMMY_HOLDER}/lucht_root_dbscan'
lucht_root = f'{eu_data}/lucht_root'

crowd_stations_root = f'{eu_data}/crowd_stations_root'
crowd_stations_dbscan_root = f'{DUMMY_HOLDER}/crowd_stations_root_dbscan'

knmi_dest_dir = os.path.join(DUMMY_HOLDER, "KNMI")
knmi_root = f'{eu_data}/KNMI'


crowd_stations_root = f'{eu_data}/crowd_stations_root'
# new_crowd_stations_root = f'{eu_data}/crowd_stations_root_dbscan'
YEAR_HOURS = 8760

make_endofhour = True

def create_paths(station,root):
    return os.path.join(root,station), os.path.join(root,station,f'{station}.json'), os.path.join(root,station,f'{station}.csv')

def drop_nan_years(df, make_endofhour = False):
    # Create a copy of the original DataFrame
    df_copy = df.copy()

    # Convert the 'time' column to datetime and extract the year
    df_copy['time2'] = pd.to_datetime(df_copy['time'], unit='s')

    if make_endofhour:
        df_copy['time2'] = df_copy['time2'] + pd.Timedelta(hours=1)
        df_copy['time'] = df_copy['time2'].astype('int64') // 10**9  # back to epoch seconds


    df_copy['year'] = df_copy['time2'].dt.year

    # Calculate the percentage of non-NA values for each column in each year
    percent_non_na = df_copy.groupby('year').apply(lambda x: x.count() / YEAR_HOURS, include_groups=False)
    
    # Find the columns where any year has less than 65% non-NA values
    columns_to_replace = percent_non_na.columns[percent_non_na.lt(0.65).any()]

    # For these columns, replace the values for the years where it has less than 65% non-NA values with NA
    for column in columns_to_replace:
        years_to_replace = percent_non_na.index[percent_non_na[column] < 0.65]
        df_copy.loc[df_copy['year'].isin(years_to_replace), column] = np.nan

    # Return the modified DataFrame without the 'time2' and 'year' columns
    return df_copy.iloc[:,:-2].dropna(how='all',ignore_index = True)



def create_paths(station,root):
    return os.path.join(root,station), os.path.join(root,station,f'{station}.json'), os.path.join(root,station,f'{station}.csv')

def write_json_file(file_path, data):
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)


make_endofhour = False
YEAR_HOURS = 8760


# Make sure directories exist
os.makedirs(zip_dir, exist_ok=True)
os.makedirs(extract_dir, exist_ok=True)
if DOWNLOAD_LUCHTMEETNETCSVS:
    # Loop through years
    for year in range(1976, LAST_UPDATE+1):
        
        url = f"https://data.rivm.nl/data/luchtmeetnet/Vastgesteld-jaar/{year}/{year}.zip"
        zip_path = os.path.join(zip_dir, f"{year}.zip")
        
        try:
            print(f"Downloading {year}...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Save zip file
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Extract contents
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)
            
            print(f"Finished {year}")
        except Exception as e:
            print(f"Failed {year}: {e}")
else:

    for year_zip in os.listdir(zip_dir):
        
        zip_path = os.path.join(zip_dir,year_zip)
        
            
            # Extract contents
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)
        

print('Unzipped files')
# Make sure output folder exists
os.makedirs(clipped_dir, exist_ok=True)
print('Clipping the top rows')
# Loop through all CSV files
for filename in os.listdir(extract_dir):
    if filename.endswith(".csv"):
        input_path = os.path.join(extract_dir, filename)
        output_path = os.path.join(clipped_dir, filename)

        # Find the first non-comment line (the header)
        with open(input_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        header_line_index = None
        for i, line in enumerate(lines):
            if not line.startswith("#"):
                header_line_index = i
                break

        if header_line_index is None:
            print(f"No header found in {filename}, skipping.")
            continue

        # Load CSV, skipping comment lines
        df = pd.read_csv(input_path, skiprows=header_line_index, delimiter=';')

        # Save cleaned CSV
        df.to_csv(output_path, index=False)

        print(f" Processed {filename} → {output_path}")


# Find the first non-comment line (the header)
with open(LUCHTMEETNET_CSV_METADATA_PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()

header_line_index = None
for i, line in enumerate(lines):
    if not line.startswith("#"):
        header_line_index = i
        break

# Load CSV, skipping comment lines
df = pd.read_csv(LUCHTMEETNET_CSV_METADATA_PATH, skiprows=header_line_index, delimiter=';')

luchtmeetnet_metadata = pd.read_csv(LUCHTMEETNET_CSV_METADATA_PATH, skiprows=header_line_index, delimiter=';')


Path(separated_dir).mkdir(parents=True, exist_ok=True)

# Load metadata dataframe (make sure you already have luchtmeetnet_metadata loaded)
# Example:
# luchtmeetnet_metadata = pd.read_csv("/path/to/luchtmeetnet_metadata.csv")
print('Separating based on station')
def process_csv(file_path: Path, luchtmeetnet_metadata: pd.DataFrame):
    filename = file_path.stem  # e.g., "2020_NO2"
    year, param = filename.split("_", 1)

    df = pd.read_csv(file_path)

    # Keep only required columns
    cols = [
        "meetlocatie_id", "einddatumtijd", "waarde",
        "eenheid", "meetopstelling_id", "bron_id", "accreditatienummer"
    ]
    df = df[cols]

    # Loop over unique stations
    for station_id, group in df.groupby("meetlocatie_id"):
        # Prepare output folder
        station_folder = Path(separated_dir) / str(station_id)
        station_folder.mkdir(parents=True, exist_ok=True)

        # Rename columns for output
        out_df = group.rename(columns={
            "einddatumtijd": "time",
            "waarde": param
        })[["time", param]]

        # Save CSV
        out_csv_path = station_folder / f"{year}_{station_id}^{param}.csv"
        out_df.to_csv(out_csv_path, index=False)

        # Collect metadata
        meta_row = luchtmeetnet_metadata[luchtmeetnet_metadata["meetlocatie_id"] == station_id]
        if not meta_row.empty:
            longitude = meta_row["lengtegraad"].values[0]
            latitude = meta_row["breedtegraad"].values[0]
            station_area = meta_row.get("plaatsnaam", pd.Series(["Unknown"])).values[0]
        else:
            longitude, latitude, station_area = None, None, "Unknown"


        if 'eenheid' in group.columns:
            unit = group['eenheid'].iloc[0]
            if 'µ' in unit: 
                unit = unit.replace('µ','u')
            if 'm³' in unit:
                unit = unit.replace('³','3')

        meta_dict = {
            "Adminstrator": group["bron_id"].iloc[0],
            "stream_unit": unit,
            "longitude": longitude,
            "latitude": latitude,
            "StationArea": station_area,
            "MeasuringSensor": group["meetopstelling_id"].iloc[0],
            "AccreditationNumber": group["accreditatienummer"].iloc[0],
        }

        # Save JSON
        out_json_path = station_folder / f"{year}_{station_id}^{param}.json"
        with open(out_json_path, "w", encoding="utf-8") as f:
            json.dump(meta_dict, f, indent=4, ensure_ascii=False)


for file in Path(clipped_dir).glob("*.csv"):
    process_csv(file, luchtmeetnet_metadata)


# Ensure output root exists
os.makedirs(final_official_station, exist_ok=True)

# Process each station folder
for station_folder in os.listdir(separated_dir):
    station_path = os.path.join(separated_dir, station_folder)
    if not os.path.isdir(station_path):
        continue

    # Create output folder for this station
    out_folder = os.path.join(final_official_station, station_folder+'_VAL')
    os.makedirs(out_folder, exist_ok=True)

    # Collect CSV data and JSON metadata
    param_data = {}  # param -> list of yearly dfs
    available_params = set()
    sensor_map = {}
    stream_units = {}

    for fname in os.listdir(station_path):
        fpath = os.path.join(station_path, fname)

        if fname.endswith(".csv"):
            # Parse year, station, parameter from filename
            year, rest = fname.split("_", 1)
            station_id, param_part = rest.split("^")
            param = param_part.replace(".csv", "")

            available_params.add(param)

            # Read CSV
            df = pd.read_csv(fpath)

            # Standardize columns: expect a datetime column and a value column
            if "time" in df.columns:
                time_col = "time"
            else:
                time_col = df.columns[0]

            value_col = [c for c in df.columns if c != time_col][0]

            # Convert time to epoch
            df[time_col] = pd.to_datetime(df[time_col], utc=True, errors="coerce")
            df = df.dropna(subset=[time_col])
            df["epoch"] = df[time_col].astype("int64") // 10**9

            # Keep only epoch + param
            df = df[["epoch", value_col]].rename(columns={value_col: param})

            if param not in param_data:
                param_data[param] = []
            param_data[param].append(df)

        elif fname.endswith(".json"):
            # Extract year from filename
            year = fname.split("_")[0]
            with open(fpath, "r") as f:
                meta = json.load(f)

            # Extract needed fields
            measuring_sensor = meta.get("MeasuringSensor")
            stream_unit = meta.get("stream_unit")

            if measuring_sensor:
                sensor_map[year] = measuring_sensor

            if stream_unit:
                param = fname.split("^")[1].replace(".json", "")
                stream_units[param] = stream_unit

    # Merge all years for each parameter
    merged_params = {}
    for param, dfs in param_data.items():
        merged = pd.concat(dfs).groupby("epoch", as_index=False).first()
        merged_params[param] = merged

    # Merge parameters into one dataframe
    merged_df = None
    for param, df in merged_params.items():
        if merged_df is None:
            merged_df = df
        else:
            merged_df = pd.merge(merged_df, df, on="epoch", how="outer")

    if merged_df is not None:
        merged_df = merged_df.sort_values("epoch").rename(columns={'epoch':'time'})
        merged_df.to_csv(os.path.join(out_folder, f"{station_folder}_VAL.csv"), index=False)

    # Create final JSON
    final_json = {
        "Adminstrator": meta.get('Adminstrator'),
        "longitude": meta.get('longitude'),
        "latitude": meta.get('latitude'),
        "location": meta.get('StationArea'),
        "AccreditationNumber": meta.get('AccreditationNumber'),
        "type": meta.get('type'),
        "available_streams": sorted(list(available_params)),
        "sensor": sensor_map,
        "stream_units": stream_units,
        "datastreams_links": "https://data.rivm.nl/data/luchtmeetnet/"
    }

    with open(os.path.join(out_folder, f"{station_folder}_VAL.json"), "w") as f:
        json.dump(final_json, f, indent=2)

shutil.copytree(final_official_station, FINAL_DIR,dirs_exist_ok=True)
    
    
