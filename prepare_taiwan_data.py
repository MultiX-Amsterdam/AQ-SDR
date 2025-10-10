import os
import json
from glob import glob
import shutil
import zipfile
import pandas as pd
from pathlib import Path
from pandas.api.types import is_datetime64_any_dtype
import tarfile
import gzip
import numpy as np

import argparse
import sys
import random
import subprocess
import warnings
warnings.filterwarnings("ignore")

import warnings
import time


from utils.geoutils import *
from preprocessing_scripts import metadata_creation_taiwan 
from preprocessing_scripts import create_lcs_only


from math import radians, cos, sin, asin, sqrt

from functools import reduce
from io import BytesIO
import time

start = time.time()


SEED=1999
def set_seed(seed):

    random.seed(seed)
    np.random.seed(seed)
    print(f'Seed set to: {seed}')


# download_and_process_iot_data.py
# 
# This script clones specified GitHub repositories into a temporary "dum" directory,
# processes only the folders named '2021' and '2022' within each clone,
# copies CSV files (and/or extracts TAR.GZ files) into the 'raw_data' directory,
# and finally removes the temporary clone directory.

# Paths
parser = argparse.ArgumentParser(description="Process directory and config arguments.")

parser.add_argument("--operation_root", required=True, help="Path where original data is at")
parser.add_argument("--final_root", required=True, help="Path to final_root, where original data is from")
parser.add_argument("--keep_dummy", action="store_true", help="action = False. default is that it will delete it")

args = parser.parse_args()

ROOT = args.operation_root
FINAL_ROOT = args.final_root
KEEP_DUMMY = args.keep_dummy
CHUNKSIZE = 1e15
# Note: if you have a lot of ram (> 64 gb), feel free to use the function #create_unsampled() instead of create_unsampled_memorysave. it should be faster.

print("Operation root:", ROOT)
print("Final root:", FINAL_ROOT)
print("KEEP_DUMMY:", KEEP_DUMMY)

print(f'Remove dummy folder is set to: {KEEP_DUMMY}')

# Check root
if not os.path.isdir(ROOT):
    sys.stderr.write(f"Error: root does not exist or is not a directory: {ROOT}\n")
    sys.exit(1)

os.makedirs(FINAL_ROOT,exist_ok=True)
PROCESSED_ROOT = f'{FINAL_ROOT}/lcs_data_dbscan'
REPO_ROOT = f'{ROOT}/downloaded_lcs'
RAW_ROOT = f'{FINAL_ROOT}/raw_data'
UNSAMPLED_ROOT = f'{FINAL_ROOT}/unsampled_data'
SAMPLED_ROOT = f'{FINAL_ROOT}/ood_data_sampled'
DEST_ROOT = f'{FINAL_ROOT}/data_final'





OG_ROOT = FINAL_ROOT
FULL_METADATA_PATH = f'{OG_ROOT}/metadata/full_metadata.json'
FULL_GRIDS_PATH = f'{OG_ROOT}/metadata/gridded_5km.json'
VAL_ID = 'VAL_PRE'



HOURS_PER_YEAR  = 365 * 24
THRESHOLD_RATIO = 0.60
THRESHOLD_HOURS = int(THRESHOLD_RATIO * HOURS_PER_YEAR)  # e.g., 0.60 * 8760 = 5256
YEARS = [2020, 2021, 2022,2023, 2024]
# YEARS = [2021, 2022]
BATCH_SIZE       = 1440
TAIWAN_TZ = 'Asia/Taipei'


REFERENCE_DATA_ROOT = f'{OG_ROOT}/ood_data_reference'
raw_data_dir = f'{REFERENCE_DATA_ROOT}/raw_data/'
output_base_dir = f'{REFERENCE_DATA_ROOT}/data_folders/'
# Configuration
data_folders_dir = f'{REFERENCE_DATA_ROOT}/data_folders/'
unsampled_dir = f'{REFERENCE_DATA_ROOT}/unsampled_data/'

# Ensure unsampled base d

# Configuration
data_unsampled_dir = f'{REFERENCE_DATA_ROOT}/unsampled_data/'
data_final_dir = f'{REFERENCE_DATA_ROOT}/data_final/'

# Configuration
bulk_dir = f'{OG_ROOT}/final_dataset/ood_data_bulk/'
ref_dir = f'{OG_ROOT}/ref_data_dbscan/'
out_dir = f'{OG_ROOT}/final_dataset/prepared_ood_datasets/'
threshold_km = 5.0  # distance threshold in kilometers
BATCH_SIZE = 1440
THRESHOLD_HOURS = 5256.0
processed_root = f'{OG_ROOT}/ref_data_dbscan/'



gov_data_list = [
    f'{ROOT}/downloaded_ref/MOENV_OD_2020.zip',
    f'{ROOT}/downloaded_ref/MOENV_OD_2021.zip',
    f'{ROOT}/downloaded_ref/MOENV_OD_2022.zip'
]



git_root = REPO_ROOT
raw_root = RAW_ROOT
# use this if u want to redownload the LASS data again
# if DOWNLOAD_DATA:
#     print('Downloading data from GitHub.')
#     repo_urls = [
#             'https://github.com/cclljj/TW-Civil-IoT-2017',
#             'https://github.com/cclljj/TW-Civil-IoT-2018',
#             'https://github.com/cclljj/TW-Civil-IoT-2019',
#             'https://github.com/cclljj/TW-Civil-IoT-2020',
#         ]

#         # Paths for dummy clone directory and target raw data directory

#     # Ensure directories exist
#     os.makedirs(git_root, exist_ok=True)

#     # Clone or pull each repository into git_root
#     for url in repo_urls:
#         print('Downloading:', url)
#         repo_name = os.path.basename(url)
#         dest = os.path.join(git_root, repo_name)
#         if os.path.isdir(dest):
#             print(f"Repository {repo_name} already exists, pulling latest changes...")
#             subprocess.run(['git', '-C', dest, 'pull'], check=True)
#         else:
#             print(f"Cloning {repo_name} into {dest}...")
#             subprocess.run(['git', 'clone', url, dest], check=True)

#     #     # List of GitHub repository URLs to clone
        

os.makedirs(raw_root, exist_ok=True)
# Define which year folders to process
years_to_process = {'2020','2021', '2022', '2023','2024'}

# Process each cloned repo
for repo in os.listdir(git_root):
    print(f"Processing {repo}")
    repo_path = os.path.join(git_root, repo)
    if not os.path.isdir(repo_path):
        continue

    for year in os.listdir(repo_path):
        if year not in years_to_process:
            continue
        year_dir = os.path.join(repo_path, year)
        if not os.path.isdir(year_dir):
            continue

        entries = set(os.listdir(year_dir))

        for fname in entries:
            src = os.path.join(year_dir, fname)

            # 1. Direct CSV
            if fname.lower().endswith('.csv'):
                shutil.copy2(src, raw_root)
                continue

            base, ext = os.path.splitext(fname)
            ext = ext.lower()

            # 2. TAR.GZ or TGZ archives
            if fname.lower().endswith(('.tar.gz', '.tgz')):
                csv_name = base + '.csv'
                if csv_name not in entries:
                    dest = os.path.join(raw_root, fname)
                    shutil.copy2(src, dest)
                    with tarfile.open(dest, 'r:*') as tar:
                        tar.extractall(path=raw_root)
                    os.remove(dest)
                continue

            # 3. ZIP archives
            if ext == '.zip':
                csv_name = base + '.csv'
                if csv_name not in entries:
                    dest = os.path.join(raw_root, fname)
                    shutil.copy2(src, dest)
                    with zipfile.ZipFile(dest, 'r') as z:
                        z.extractall(path=raw_root)
                    os.remove(dest)
                continue

            # 4. GZIP (.gz) compressed single file
            if ext == '.gz' and not fname.lower().endswith(('.tar.gz', '.tgz')):
                decompressed_name = base  # e.g., file.csv from file.csv.gz
                csv_name = decompressed_name if decompressed_name.lower().endswith('.csv') else None
                # Only process if it would yield a CSV
                if csv_name and csv_name not in entries:
                    src_gz = os.path.join(year_dir, fname)
                    raw_gz = os.path.join(raw_root, fname)
                    # copy gz
                    shutil.copy2(src_gz, raw_gz)
                    # decompress
                    with gzip.open(raw_gz, 'rb') as f_in, open(os.path.join(raw_root, decompressed_name), 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                    os.remove(raw_gz)
                continue

        print(f"Finished processing {year_dir}\n")



def process_csv(src_path, raw_data_dir):
    """
    Copy a CSV file to raw_data_dir, or merge with existing if already present.
    """
    fname = os.path.basename(src_path)
    target_path = os.path.join(raw_data_dir, fname)
    if not os.path.exists(target_path):
        shutil.copy2(src_path, target_path)
    else:
        existing_df = pd.read_csv(target_path)
        new_df = pd.read_csv(src_path)
        combined = pd.concat([existing_df, new_df], ignore_index=True).drop_duplicates()
        combined.to_csv(target_path, index=False)


def process_df(df, fname, raw_data_dir):
    """
    Save a DataFrame to raw_data_dir, or merge with existing if present.
    """
    target_path = os.path.join(raw_data_dir, fname)
    if os.path.exists(target_path):
        existing_df = pd.read_csv(target_path)
        combined = pd.concat([existing_df, df], ignore_index=True).drop_duplicates()
        combined.to_csv(target_path, index=False)
    else:
        df.to_csv(target_path, index=False)


def extract_and_process_compressed(comp_path, csv_file_names, raw_data_dir):
    """
    Handle compressed archive or gz file, extract CSV(s) and process.
    """
    comp_lower = comp_path.lower()
    # ZIP archives
    if comp_lower.endswith('.zip'):
        with zipfile.ZipFile(comp_path) as zf:
            for member in zf.namelist():
                if member.lower().endswith('.csv'):
                    fname = os.path.basename(member)
                    if fname in csv_file_names:
                        continue
                    with zf.open(member) as f_in:
                        df = pd.read_csv(f_in)
                        process_df(df, fname, raw_data_dir)
    # TAR or TAR.GZ / TGZ archives
    elif comp_lower.endswith(('.tar.gz', '.tgz', '.tar')):
        with tarfile.open(comp_path) as tf:
            for member in tf.getmembers():
                if member.isfile() and member.name.lower().endswith('.csv'):
                    fname = os.path.basename(member.name)
                    if fname in csv_file_names:
                        continue
                    fobj = tf.extractfile(member)
                    df = pd.read_csv(fobj)
                    process_df(df, fname, raw_data_dir)
    # Single-file GZIP (e.g., data.csv.gz)
    elif comp_lower.endswith('.gz'):
        fname = os.path.basename(comp_path)[:-3]
        if fname in csv_file_names:
            return
        with gzip.open(comp_path, 'rt') as f_in:
            df = pd.read_csv(f_in)
            process_df(df, fname, raw_data_dir)


def create_raw(repo_root_dir, raw_data_dir):
    os.makedirs(raw_data_dir, exist_ok=True)

    # Only consider these year-named subfolders
    year_dirs = ['2020', '2021', '2022', '2023', '2024']

    for original_folder in os.listdir(repo_root_dir):
        original_path = os.path.join(repo_root_dir, original_folder)
        if not os.path.isdir(original_path):
            continue
        for year in year_dirs:
            subfolder = os.path.join(original_path, year)
            if not os.path.isdir(subfolder):
                continue

            # List files in the year folder
            files = os.listdir(subfolder)
            # Direct CSVs
            csv_files = [f for f in files if f.lower().endswith('.csv')]

            # Process direct CSV files
            for filename in csv_files:
                src_path = os.path.join(subfolder, filename)
                process_csv(src_path, raw_data_dir)

            # Process compressed files
            comp_files = [f for f in files if f.lower().endswith(('.zip', '.tar', '.tgz', '.gz'))]
            for comp in comp_files:
                comp_path = os.path.join(subfolder, comp)
                extract_and_process_compressed(comp_path, set(csv_files), raw_data_dir)

print('merging all csv files together into date-based files')
create_raw(repo_root_dir = REPO_ROOT, raw_data_dir=RAW_ROOT)

print('DONE merging all csv files together into date-based files')


def create_unsampled_memorysave(chunksize=1000000):
    raw_root = RAW_ROOT
    target_root = UNSAMPLED_ROOT

    raw_root = Path(raw_root)
    target_root = Path(target_root)
    target_root.mkdir(parents=True, exist_ok=True)

    # Collect all CSV file paths
    csv_files = sorted(raw_root.glob('*.csv'))
    if not csv_files:
        print(f"No CSV files found in {raw_root}")
        return

    # Determine sensor stream columns from header of first file
    header = pd.read_csv(csv_files[0], nrows=0)
    exclude = {'device_id', 'date', 'time', 'lat', 'lon'}
    streams = [c for c in header.columns if c not in exclude]

    # Metadata store for each device
    device_meta = {}

    # Process each CSV file in chronological order
    for idx, path in enumerate(csv_files):
        if idx %50 ==0:
            print(f"{idx}/{len(csv_files)}. Processing file: {path.name}")
        # Read in chunks
        for chunk in pd.read_csv(path, chunksize=chunksize):
            # Parse and sort by datetime
            chunk['datetime'] = pd.to_datetime(chunk['date'] + ' ' + chunk['time'])
            chunk.sort_values('datetime', inplace=True)

            # Group by device
            for device_id, grp in chunk.groupby('device_id'):
                device_str = str(device_id)
                device_dir = target_root / device_str
                device_dir.mkdir(exist_ok=True)

                # Prepare output DataFrame for this chunk
                out_df = grp[['device_id', 'datetime'] + streams]

                # Write or append to device CSV
                csv_out = device_dir / f"{device_str}.csv"
                if not csv_out.exists():
                    out_df.to_csv(csv_out, index=False)
                else:
                    out_df.to_csv(csv_out, mode='a', header=False, index=False)

                # Capture first lat/lon for metadata
                if device_str not in device_meta and 'lat' in grp.columns and 'lon' in grp.columns:
                    first = grp.iloc[0]
                    device_meta[device_str] = {
                        'latitude': float(first['lat']),
                        'longitude': float(first['lon'])
                    }

    # After processing all chunks, write metadata per device
    for device_str, coords in device_meta.items():
        meta = {
            "type": "taiwan_raw",
            "longitude": coords['longitude'],
            "latitude": coords['latitude'],
            "country": "taiwan",
            "available_streams": [s.lower() for s in streams]
        }
        json_path = target_root / device_str / f"{device_str}.json"
        with open(json_path, 'w') as jf:
            json.dump(meta, jf, indent=2)
        # print(f"Wrote metadata for device {device_str}")



def create_unsampled():
    raw_root = RAW_ROOT
    target_root = UNSAMPLED_ROOT

    # Ensure target root exists
    os.makedirs(target_root, exist_ok=True)

    # Collect all raw CSV file paths
    csv_files = sorted(glob(os.path.join(raw_root, '*.csv')))
    if not csv_files:
        print(f"No CSV files found in {raw_root}")
        return

    # Read and concatenate all CSVs
    print("Loading and concatenating raw CSV files...")
    df_list = []
    for idx, path in enumerate(csv_files):
        if idx %50 ==0:
            print(f"{idx}/{len(csv_files)}).")
        df = pd.read_csv(path)
        df_list.append(df)

    data = pd.concat(df_list, ignore_index=True)
    del df_list, df
    # Parse datetime
    # print("Parsing and merging date/time columns...")
    data['datetime'] = pd.to_datetime(data['date'] + ' ' + data['time'])
    data = data.sort_values('datetime')

    # Identify sensor streams (exclude id, date/time, lat/lon)
    exclude_cols = {'device_id', 'date', 'time', 'lat', 'lon','datetime'}
    streams = [c for c in data.columns if c not in exclude_cols]

    # Process per device
    for device, group in data.groupby('device_id'):
        device_str = str(device)
        device_dir = os.path.join(target_root, device_str)
        os.makedirs(device_dir, exist_ok=True)

        # Write concatenated CSV
        csv_out = os.path.join(device_dir, f"{device_str}.csv")
        out_df = group.copy()
        out_df = out_df.drop(columns=['date', 'time', 'lat', 'lon'])
        # rename datetime column
        out_df = out_df[['device_id', 'datetime'] + [c for c in streams]]
        out_df.to_csv(csv_out, index=False)

        # Determine unique lat/lon (use first observation)
        lat_val = float(group['lat'].iloc[0])
        lon_val = float(group['lon'].iloc[0])

        # Build metadata JSON
        meta = {
            "type": "taiwan_raw",
            "longitude": lon_val,
            "latitude": lat_val,
            "country": "taiwan",
            "available_streams": [s.lower() for s in streams]
        }
        json_out = os.path.join(device_dir, f"{device_str}.json")
        with open(json_out, 'w') as jf:
            json.dump(meta, jf, indent=2)

        # print(f"Processed device {device_str}: {len(group)} records")


def create_sampled():
    src_root = UNSAMPLED_ROOT
    dst_root = SAMPLED_ROOT

    os.makedirs(dst_root, exist_ok=True)
    
    # Iterate over each device folder
    for device_dir in os.listdir(src_root):
        
        src_device_path = os.path.join(src_root, device_dir)
        if device_dir in os.listdir(dst_root):
            continue
        if not os.path.isdir(src_device_path):
            continue

        # Prepare destination folder
        dst_device_path = os.path.join(dst_root, device_dir)
        os.makedirs(dst_device_path, exist_ok=True)


        # Process CSV
        src_csv = os.path.join(src_device_path, f"{device_dir}.csv")
        dst_csv = os.path.join(dst_device_path, f"{device_dir}.csv")
        if not os.path.isfile(src_csv):
            print(f"Warning: CSV file not found for device {device_dir}")
            continue

        # Read original CSV, parse datetime
        df = pd.read_csv(src_csv, parse_dates=['datetime'])
        if not is_datetime64_any_dtype(df['datetime']):
            df['datetime'] = pd.to_datetime(df['datetime'], format='mixed')
        # Identify and normalize PM2.5 column
        pm25_col = None
        for col in df.columns:
            if col.lower().replace('.', '') == 'pm25':
                pm25_col = col
                break
        if pm25_col is None:
            print(f"Warning: No PM2.5 column found in {src_csv}")
            continue
        df = df.rename(columns={pm25_col: 'pm25'})

        # Convert pm25 to numeric, coercing errors to NaN
        df['pm25'] = pd.to_numeric(df['pm25'], errors='coerce')

        # Localize datetime (assume naive Asia/Taipei) and convert to epoch seconds
        df['datetime'] = df['datetime'].dt.tz_localize('Asia/Taipei')

        # Set datetime index and resample hourly on pm25
        df_hourly = (
            df.set_index('datetime')['pm25']
              .resample('h')
              .mean()
            #   .dropna()
              .reset_index()
        )

        # Compute epoch time for each resampled timestamp
        df_hourly['time'] = df_hourly['datetime'].apply(lambda x: int(x.timestamp()))

        # Final output: columns 'time', 'pm25'
        out_df = df_hourly[['time', 'pm25']]


        # Copy JSON metadata
        src_json = os.path.join(src_device_path, f"{device_dir}.json")
        dst_json = os.path.join(dst_device_path, f"{device_dir}.json")
        with open(src_json, 'r') as jf:
            meta = json.load(jf)
        meta['available_streams'] = ['pm25']
        with open(dst_json, 'w') as jf:
            json.dump(meta, jf, indent=2)



        # if os.path.isfile(src_json):
        #     shutil.copy2(src_json, dst_json)
        # else:
        #     print(f"Warning: JSON metadata not found for device {device_dir}")
        # json_out = os.path.join(site_output_dir, f"{site_id}.json")
        out_df.to_csv(dst_csv, index=False)
        # print(f"Processed device {device_dir}: {len(out_df)} hourly records")

        del out_df, meta, df_hourly, df




def valid_year():
    src_root = SAMPLED_ROOT
    dst_root = DEST_ROOT

    os.makedirs(dst_root, exist_ok=True)

    for device in os.listdir(src_root):
        src_dir = os.path.join(src_root, device)
        if not os.path.isdir(src_dir):
            continue

        csv_src = os.path.join(src_dir, f"{device}.csv")
        json_src = os.path.join(src_dir, f"{device}.json")
        if not os.path.isfile(csv_src):
            print(f"Skipping {device}: CSV not found")
            continue

        # Load data
        df = pd.read_csv(csv_src)
        df['datetime'] = pd.to_datetime(df['time'], unit='s', utc=True).dt.tz_convert('Asia/Taipei')
        df['year'] = df['datetime'].dt.year

        # Count valid readings per year
        year_counts = {year: df.loc[df['year'] == year, 'pm25'].count() for year in YEARS}
        passing_years = [y for y, cnt in year_counts.items() if cnt >= THRESHOLD_HOURS]

        # No years pass: skip
        if not passing_years:
            # print(f"Skipping {device}: counts={year_counts} below threshold")
            continue

        dst_dir = os.path.join(dst_root, device)
        if os.path.exists(dst_dir):
            shutil.rmtree(dst_dir)
        os.makedirs(dst_dir)

        # Copy JSON metadata if exists
        if os.path.isfile(json_src):
            shutil.copy2(json_src, os.path.join(dst_dir, f"{device}.json"))

        # Both years pass: copy entire folder unchanged
        if set(passing_years) == set(YEARS):
            shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
            print(f"Copied full data for {device}: counts={year_counts}")
                    
        else:
            # Only one year passes: filter and write CSV
            year = passing_years[0]
            df_filtered = df[df['year'] == year][['time', 'pm25']]
            csv_dst = os.path.join(dst_dir, f"{device}.csv")
            df_filtered.to_csv(csv_dst, index=False)
            # print(f"Filtered data for {device}: kept year {year} with {year_counts[year]} readings")
            del df_filtered
    print("Filtering to data_final complete.")
    del df
    


def final_process():

    for device_id in os.listdir(DEST_ROOT):
        src_dir = os.path.join(DEST_ROOT, device_id)
        if not os.path.isdir(src_dir):
            continue

        csv_path = os.path.join(src_dir, f"{device_id}.csv")
        if not os.path.isfile(csv_path):
            continue

        # --- 1) Load CSV (epoch seconds) and convert to datetime in Taiwan tz
        df = pd.read_csv(csv_path)
        # --- 4) Batch‐wise DBSCAN preprocessing
        df_final = pd.DataFrame()
        for i in range(0, len(df), BATCH_SIZE):
            batch = df.iloc[i:i+BATCH_SIZE]
            df_final = pd.concat([
                df_final,
                run_dbscan_on_df(batch, ['pm25'], dbs_radius=1)
            ], ignore_index=True)
        # break
        # --- 5) Filter by data coverage and copy if ≥60%
        if len(df_final) >= THRESHOLD_HOURS:
            dst_dir = os.path.join(PROCESSED_ROOT, device_id)
            shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
            df_final.to_csv(os.path.join(dst_dir, f"{device_id}.csv"), index=False)
            print(f"Kept {device_id}: {len(df_final)} rows ({len(df_final)/HOURS_PER_YEAR:.1%} coverage)")
        else:
            print(f"Skipped {device_id}: only {len(df_final)/HOURS_PER_YEAR:.1%} coverage")

        del df, df_final
        
# create_unsampled() #use this if you have more than 64 gb of ram, otherwise use memorysave function that is more memory friendly.
create_unsampled_memorysave(chunksize=CHUNKSIZE) 


create_sampled()


valid_year()

final_process()



#### Create tensors for the actual model
SEED = 1999
random.seed(SEED)
np.random.seed(SEED)
TW_ONLY = True
PARAMETERS = ['pm25']
VARIABLES_OF_INTEREST = ['num_of_rows','period','available_streams']
# METADATA_ROOT = f'{OG_ROOT}/metadata/'
FULL_METADATA_PATH = f'{OG_ROOT}/metadata/full_metadata.json'
FULL_GRIDS_PATH = f'{OG_ROOT}/metadata/gridded_5km.json'

create_lcs_only.ROOT = f'{OG_ROOT}/lcs_data_dbscan/'
metadata_creation_taiwan.ROOT = f'{OG_ROOT}/lcs_data_dbscan/'
metadata_creation_taiwan.one_time_full_metadata(output = FULL_METADATA_PATH)
FULL_METADATA = load_json_file(FULL_METADATA_PATH)
metadata_creation_taiwan.create_grid('./utils/taiwan.geojson',FULL_GRIDS_PATH,spacing_km=5)
FULL_GRIDS = load_json_file(FULL_GRIDS_PATH)
metadata_creation_taiwan.group_stations_by_grid(FULL_METADATA, FULL_GRIDS, 5000, True, f'{OG_ROOT}/metadata/stations_within_grids/stations_within_grids_5000.json')
STATIONS_WITHIN_GRIDS = load_json_file(f'{OG_ROOT}/metadata/stations_within_grids/stations_within_grids_5000.json')


lcs_bulk_store = f'{OG_ROOT}/final_dataset/ood_data_bulk' #lcs stations 
grid_coords = FULL_GRIDS['Taiwan']
dum_index =[]
cols_lim=10
std_multiplier = float('inf')
latent_dimension = cols_lim//2
radius_km = 5
used_coords = []
for coords in grid_coords:
    data = metadata_creation_taiwan.find_sensors_in_radius(full_meta = FULL_METADATA, 
                            center_lon = coords[0], 
                            center_lat = coords[1],  
                            radius_km= radius_km, 
                            variable_list = ['pm25'],
                            TW_ONLY=False)
    if len(data['Taiwan'])>cols_lim:
        dum_index.append([coords,data['Taiwan']])
        

unique_coords = metadata_creation_taiwan.filter_intersecting_lists(dum_index,with_coordinates=True)
final_coords = create_lcs_only.filter_unique_coordinates(unique_coords, used_coords,radius_km)
names = []
name_counts = {}
for idx, coords in enumerate(final_coords):
    data = metadata_creation_taiwan.find_sensors_in_radius(full_meta = FULL_METADATA, 
                                    center_lon = coords[0], 
                                    center_lat = coords[1],  
                                    radius_km= radius_km, 
                                    variable_list = ['pm25'],
                                    TW_ONLY=False)
    loaded_data = create_lcs_only.no_alignment_dataloader(data,
        keep_columns = ['time','temp','rh','pm25','pm10'],
        must_columns = ['pm25'],
                regions = 'all',
                remove_empty_df=True)


    # Example usage:
    if loaded_data['Taiwan'] == {}:
        continue
    
    merged_data = create_lcs_only.merge_sensor_dataframes(loaded_data['Taiwan'], discard_specific_ids=True)



    lcs_stations = merged_data.copy()
    lcs_selected = metadata_creation_taiwan.select_best_columns(metadata_creation_taiwan.fill_continuous_timestamps(lcs_stations), limit_columns=cols_lim)
    # drop_cols = [item for item in lcs_stations.columns if 'VAL_PRE' in item]
    full_lcs = lcs_selected.dropna(thresh=(latent_dimension+1))
    full_lcs_notime = full_lcs.drop(columns='time')
    

    # print(loaded_data['Taiwan'])

names = []
name_counts = {}
for idx, coords in enumerate(final_coords):
    data = metadata_creation_taiwan.find_sensors_in_radius(full_meta = FULL_METADATA, 
                                    center_lon = coords[0], 
                                    center_lat = coords[1],  
                                    radius_km= radius_km, 
                                    variable_list = ['pm25'],
                                    TW_ONLY=False)
    loaded_data = create_lcs_only.no_alignment_dataloader(data,
        keep_columns = ['time','temp','rh','pm25','pm10'],
        must_columns = ['pm25'],
                regions = 'all',
                remove_empty_df=True)


    # Example usage:
    if loaded_data['Taiwan'] == {}:
        continue
    merged_data = create_lcs_only.merge_sensor_dataframes(loaded_data['Taiwan'], discard_specific_ids=True)



    lcs_stations = merged_data.copy()
    lcs_selected = metadata_creation_taiwan.select_best_columns(metadata_creation_taiwan.fill_continuous_timestamps(lcs_stations), limit_columns=cols_lim)
    # drop_cols = [item for item in lcs_stations.columns if 'VAL_PRE' in item]
    full_lcs = lcs_selected.dropna(thresh=(latent_dimension+1))
    full_lcs_notime = full_lcs.drop(columns='time')



    total_mean = full_lcs_notime.mean().mean()
    total_std = full_lcs_notime.mean().std()
    spike_thresh = total_mean + std_multiplier*total_std
    full_lcs_filter_notime = metadata_creation_taiwan.mask_extended_zeros(full_lcs_notime.where((full_lcs_notime<spike_thresh), other=pd.NA))

    full_lcs_filter = full_lcs.copy(deep=True)
    full_lcs_filter.iloc[:,1:] = full_lcs_filter_notime.copy()

    if full_lcs_filter.empty:
        print(f'{idx}, {coords} has empty df---------' )
        # empty.append(coords)
        continue
    
    full_lcs_filter = create_lcs_only.filter_half_na_rows(full_lcs_filter).reset_index(drop=True)
    dum_name_holder = None
    while dum_name_holder == None:
        dum_name_holder = create_lcs_only.get_location_name(coords)
   
    loc_name = dum_name_holder.replace(" ", "_").replace("'","").replace('_','')
    original_name = loc_name # Store the original name to use as a key in name_counts
    # Check if the name (or its base form) has been seen before
    if original_name in name_counts:
        # Increment the count for this name
        name_counts[original_name] += 1
        # Append the new count to make the name unique
        loc_name = f"{original_name}{name_counts[original_name]}"
    else:
        # First time seeing this name, initialize its count to 0 (or 1 if you prefer to start at _1)
        # We start at 0 so the first duplicate gets _1, the second _2, etc.
        name_counts[original_name] = 0
        # If it's the first occurrence, the name remains as is, without a suffix
    # Add the (potentially modified) loc_name to your list
    names.append(loc_name)  

    os.makedirs(lcs_bulk_store, exist_ok=True)
    store_path = os.path.join(lcs_bulk_store,f'{loc_name}_{coords[0]}_{coords[1]}_lcs.csv')

    write_csv_file(store_path,full_lcs_filter)
    time.sleep(1)

# gov_data_list = [
#     f'{OG_ROOT}/MOENV_OD_2021.zip',
#     f'{OG_ROOT}/MOENV_OD_2022.zip'
# ]

for gov_data in gov_data_list:
    outer_zip   = Path(gov_data)
    target_dir  = Path(f'{REFERENCE_DATA_ROOT}/raw_data')
    target_dir.mkdir(parents=True, exist_ok=True)
    if gov_data == f'{ROOT}/downloaded_ref/MOENV_OD_2020.zip':
        with zipfile.ZipFile(gov_data, "r") as zf:
            for csv_name in zf.namelist():
                out_path = target_dir / Path(csv_name).name
                temp_extract_path = zf.extract(csv_name, path=target_dir)
                # Ensure it has the exact desired name/path
                shutil.move(temp_extract_path, out_path)
                print(f"✓ {out_path.relative_to(target_dir.parent)}")
    else:
        with zipfile.ZipFile(outer_zip) as z:
            # iterate over every item inside the top-level zip
            for member in z.namelist():
                # we only care about the 12 monthly zip files: EPA_OD_2021XX.zip
                if member.startswith("EPA_OD_20") and member.endswith(".zip"):
                    # read the nested zip into memory
                    nested_bytes = z.read(member)
                    with zipfile.ZipFile(BytesIO(nested_bytes)) as nz:
                        # each nested zip contains just one CSV: EPA_OD_2021XX.csv
                        for csv_name in nz.namelist():
                            if csv_name.endswith(".csv"):
                                out_path = target_dir / Path(csv_name).name
                                with nz.open(csv_name) as src, open(out_path, "wb") as dst:
                                    shutil.copyfileobj(src, dst)
                                print(f"✓ {out_path.relative_to(target_dir.parent)}")



# Configuration

# Columns of interest
cols = [
    'SiteId', 'Latitude', 'Longitude',
    'CO', 'NO', 'NO2', 'NOx', 'O3',
    'PM10', 'PM10_AVG', 'PM2.5', 'PM2.5_AVG',
    'SO2', 'SO2_AVG',
    'WindDirec', 'WindSpeed', 'PublishTime'
]



# Read all CSV files and concatenate
def load_all_data(raw_dir, columns):
    csv_files = glob(os.path.join(raw_dir, '*.csv'))
    dfs = []
    for fp in csv_files:
        df = pd.read_csv(fp, usecols=lambda c: c in columns)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)

# Main processing
def split_by_site(raw_dir, output_dir):
    # Load data
    df = load_all_data(raw_dir, cols)

    # Convert PublishTime to datetime and sort global (optional)
    # Parse PublishTime with inferred datetime format (e.g. "2021/1/1 00:00:00")
    df['PublishTime'] = pd.to_datetime(df['PublishTime'], infer_datetime_format=True, format='mixed')

    # Group by SiteId
    for site_id, group in df.groupby('SiteId'):
        # Sort group's data chronologically
        grp = group.sort_values('PublishTime')

        # Prepare site output directory
        site_dir = os.path.join(output_dir, str(site_id))
        os.makedirs(site_dir, exist_ok=True)

        # Write CSV file
        csv_out = os.path.join(site_dir, f"{site_id}.csv")
        grp.to_csv(csv_out, index=False)

        # Build JSON metadata
        latitude = float(grp['Latitude'].iloc[0])
        longitude = float(grp['Longitude'].iloc[0])

        # Determine available streams
        pollutants = [
            'CO', 'NO', 'NO2', 'NOx', 'O3',
            'PM10', 'PM10_AVG', 'PM2.5', 'PM2.5_AVG',
            'SO2', 'SO2_AVG', 'WindDirec', 'WindSpeed'
        ]
        available = [p for p in pollutants if not grp[p].dropna().empty]

        meta = {
            "type": "taiwan_reference",
            "longitude": longitude,
            "latitude": latitude,
            "country": "taiwan",
            "available_streams": available
        }

        # Write JSON file
        json_out = os.path.join(site_dir, f"{site_id}.json")
        with open(json_out, 'w') as jf:
            json.dump(meta, jf, indent=2)

        print(f"Processed site {site_id}: CSV and JSON written to {site_dir}")




split_by_site(raw_data_dir, output_base_dir)


os.makedirs(unsampled_dir, exist_ok=True)

# Function to process each site's CSV and JSON into unsampled format
def create_unsampled_data(input_base, output_base):
    # Iterate over each site directory in the data_folders
    for site_id in os.listdir(input_base):
        site_input_dir = os.path.join(input_base, site_id)
        if not os.path.isdir(site_input_dir):
            continue

        # Prepare output directory for this site
        site_output_dir = os.path.join(output_base, site_id)
        os.makedirs(site_output_dir, exist_ok=True)

        # Read original CSV (keep PublishTime as-is)
        csv_in = os.path.join(site_input_dir, f"{site_id}.csv")
        df = pd.read_csv(csv_in, parse_dates=['PublishTime'], infer_datetime_format=True)

        # Select and rename columns
        df = df[['PublishTime', 'PM2.5']].rename(columns={'PublishTime': 'time', 'PM2.5': 'pm25'})

        # Write new CSV without epoch conversion
        csv_out = os.path.join(site_output_dir, f"{site_id}.csv")
        df.to_csv(csv_out, index=False)

        # Update JSON metadata: only pm25 stream
        json_in = os.path.join(site_input_dir, f"{site_id}.json")
        with open(json_in, 'r') as jf:
            meta = json.load(jf)

        meta['available_streams'] = ['pm25']

        json_out = os.path.join(site_output_dir, f"{site_id}.json")
        with open(json_out, 'w') as jf:
            json.dump(meta, jf, indent=2)

        print(f"Unsampled data ready for site {site_id} at {site_output_dir}")

create_unsampled_data(data_folders_dir, unsampled_dir)



# Ensure final base directory exists
os.makedirs(data_final_dir, exist_ok=True)

# Function to process each site's unsampled CSV and JSON into final format
def create_final_data(input_base, output_base):
    for site_id in os.listdir(input_base):
        site_input_dir = os.path.join(input_base, site_id)
        if not os.path.isdir(site_input_dir):
            continue

        # Prepare output directory for this site
        site_output_dir = os.path.join(output_base, site_id)
        os.makedirs(site_output_dir, exist_ok=True)

        # Read unsampled CSV
        csv_in = os.path.join(site_input_dir, f"{site_id}.csv")
        df = pd.read_csv(csv_in, parse_dates=['time'], infer_datetime_format=True)

        # Resample by hour, averaging pm25
        df = df.set_index('time')
        df_hourly = df.resample('H').mean().reset_index()

        # Convert time to epoch seconds (Taipei timezone)
        df_hourly['time'] = (
            df_hourly['time']
            .dt.tz_localize('Asia/Taipei')
            .view('int64') // 10**9
        )

        # Write final CSV
        csv_out = os.path.join(site_output_dir, f"{site_id}.csv")
        df_hourly.to_csv(csv_out, index=False)

        # Copy JSON without changes
        json_in = os.path.join(site_input_dir, f"{site_id}.json")
        json_out = os.path.join(site_output_dir, f"{site_id}.json")
        with open(json_in, 'r') as jf:
            meta = json.load(jf)
        with open(json_out, 'w') as jf:
            json.dump(meta, jf, indent=2)

        print(f"Final data ready for site {site_id} at {site_output_dir}")

create_final_data(data_unsampled_dir, data_final_dir)


for device_id in os.listdir(data_final_dir):
    src_dir = os.path.join(data_final_dir, device_id)
    if not os.path.isdir(src_dir):
        continue

    csv_path = os.path.join(src_dir, f"{device_id}.csv")
    if not os.path.isfile(csv_path):
        continue

    # --- 1) Load CSV (epoch seconds) and convert to datetime in Taiwan tz
    df = pd.read_csv(csv_path)
    # df['time'] = pd.to_datetime(df['time'], unit='s', utc=True).dt.tz_convert(TIMEZONE)
    # df = df.set_index('time')

    # # --- 2) Hourly resample (mean) and fill gaps with 'NA'
    # hourly = df.resample('H').mean()
    # hourly['pm25'] = hourly['pm25'].where(~hourly['pm25'].isna(), 'NA')

    # # --- 3) Prepare for DBSCAN: reset index and reconvert time back to epoch UTC
    # hourly = hourly.reset_index()
    # hourly['time'] = hourly['time'].dt.tz_convert('UTC').astype('int64') // 10**9
    # df_hourly = hourly[['time', 'pm25']]

    # --- 4) Batch‐wise DBSCAN preprocessing
    df_final = pd.DataFrame()
    for i in range(0, len(df), BATCH_SIZE):
        batch = df.iloc[i:i+BATCH_SIZE]
        df_final = pd.concat([
            df_final,
            run_dbscan_on_df(batch, ['pm25'], dbs_radius=1)
        ], ignore_index=True)
    # break
    # --- 5) Filter by data coverage and copy if ≥60%
    if len(df_final) >= THRESHOLD_HOURS:
        dst_dir = os.path.join(processed_root, device_id)
        shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
        df_final.to_csv(os.path.join(dst_dir, f"{device_id}.csv"), index=False)
        print(f"Kept {device_id}: {len(df_final)} rows ({len(df_final)/HOURS_PER_YEAR:.1%} coverage)")
    else:
        print(f"Skipped {device_id}: only {len(df_final)/HOURS_PER_YEAR:.1%} coverage")



# Ensure output directory exists
os.makedirs(out_dir, exist_ok=True)

# Haversine distance
def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return 6371 * c  # Earth radius in kilometers

# Load reference station metadata once
def load_ref_stations(ref_base):
    stations = {}
    for site_id in os.listdir(ref_base):
        json_path = os.path.join(ref_base, site_id, f"{site_id}.json")
        if not os.path.isfile(json_path):
            continue
        with open(json_path) as f:
            meta = json.load(f)
        stations[site_id] = (meta['longitude'], meta['latitude'])
    return stations

ref_stations = load_ref_stations(ref_dir)

# Process each bulk file
def prepare_datasets():
    for fname in os.listdir(bulk_dir):
        if not fname.lower().endswith('.csv'):
            continue
        base, _ = os.path.splitext(fname)
        parts = base.split('_')
        if len(parts) < 4 or parts[-1] != 'lcs':
            continue

        # parse OOD location
        lon = float(parts[-3])
        lat = float(parts[-2])

        # find nearby reference stations
        matches = [sid for sid, (rlon, rlat) in ref_stations.items()
                   if haversine(lon, lat, rlon, rlat) <= threshold_km]
        if not matches:
            continue

        # Read OOD (lcs) file
        bulk_path = os.path.join(bulk_dir, fname)
        df_lcs = pd.read_csv(bulk_path)

        # Save lcs file copy
        out_lcs_name = base + '.csv'
        out_lcs_path = os.path.join(out_dir, out_lcs_name)
        df_lcs.to_csv(out_lcs_path, index=False)

        # Compile reference station data
        ref_frames = []
        for site_id in matches:
            ref_csv = os.path.join(ref_dir, site_id, f"{site_id}.csv")
            if not os.path.isfile(ref_csv):
                continue
            df_ref = pd.read_csv(ref_csv)
            df_ref = df_ref[['time', 'pm25']].rename(columns={'pm25': site_id})
            ref_frames.append(df_ref.set_index('time'))

        if not ref_frames:
            continue

        # Merge all reference frames on time index
        # df_refs = pd.concat(ref_frames, axis=1)
        df_refs = reduce(lambda left, right: pd.merge(left, right, on='time', how='outer'), ref_frames)
        df_refs = df_refs.sort_values(by='time').reset_index()
        # df_refs = df_refs.reset_index()


        # Save references file
        out_ref_name = base.replace('lcs', 'ref') + '.csv'
        out_ref_path = os.path.join(out_dir, out_ref_name)
        
        df_refs.to_csv(out_ref_path, index=False)

        print(f"Prepared: {out_lcs_name} and {out_ref_name} (matched stations: {matches})")

prepare_datasets()


if not KEEP_DUMMY:

    paths_to_delete = [RAW_ROOT, UNSAMPLED_ROOT, SAMPLED_ROOT, DEST_ROOT,REFERENCE_DATA_ROOT]


    for path in paths_to_delete:
        if os.path.exists(path):
            try:
                shutil.rmtree(path)  # removes directory and all contents
                print(f"Deleted: {path}")
            except Exception as e:
                print(f"Error deleting {path}: {e}")
        else:
            print(f"Path does not exist: {path}")


end = time.time()
print(f"Completed Taiwan data.\nExecution time: {int((end - start)/60)} minutes")