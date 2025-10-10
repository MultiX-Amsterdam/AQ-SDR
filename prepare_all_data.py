
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


parser = argparse.ArgumentParser(description="Process directory and config arguments.")

parser.add_argument("--eu_data", required=True, help="Path to eu_data, where original data is from")
parser.add_argument("--final_dir", required=True, help="Path to FINAL_DIR")
parser.add_argument("--dummy_holder", default="/tmp/dummy_holder", required=False, help="Path to DUMMY_HOLDER")
parser.add_argument("--keep_dummy", action="store_true", help="action = False. default is that it will delete it")

args = parser.parse_args()

FINAL_DIR = args.final_dir
DUMMY_HOLDER = args.dummy_holder
eu_data = args.eu_data
KEEP_DUMMY = args.keep_dummy

print("FINAL_DIR:", FINAL_DIR)
print("DUMMY_HOLDER:", DUMMY_HOLDER)
print("eu_data:", eu_data)
print("keep_dummy:", KEEP_DUMMY)

print(f'Remove dummy folder is set to: {KEEP_DUMMY}')


required_subdirs = [
    "crowd_stations_root",
    "KNMI",
    "luchtmeetnet_csvs",
    "lucht_root",
    "sencom_hourly"
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

# root = '/home/ssda/sencom_hourly/'


# batch_size = 1440
# totalnumfiles=os.listdir(crowd_stations_root)
# os.makedirs(new_crowd_stations_root, exist_ok=True)
# for idx, station in enumerate(os.listdir(crowd_stations_root)):
#     print(f'{idx}/{len(totalnumfiles)}: now at station {station}')
#     station_path, json_path, csv_path = create_paths(station,crowd_stations_root)
#     metadata = load_json_file(json_path)
#     if metadata['has_data'] == 'False':
#         continue
#     # try:
#     #     df = pd.read_csv(csv_path).iloc[-52596:,:]
#     #     print('loading only 52596')
#     # except:
#     #     df = pd.read_csv(csv_path)
#     #     print('loading all')
    
#     df = pd.read_csv(csv_path)
    

#     metadata_streams = list(df.columns[1:])
#     if metadata_streams != []:
#         df_final = pd.DataFrame()

#         for i in range(0, len(df), batch_size):
#             df_final = pd.concat([df_final,run_dbscan_on_df(df.iloc[i:i+batch_size,:],metadata_streams,dbs_radius=1)])
            

        
#         dum_dict= {}
#         for key in metadata['available_streams']:
#             # print(key)
#             if key in metadata_streams:

#                 dum_dict[key] = metadata['available_streams'][key]
#             else:
#                 continue
#         metadata['available_streams'] = dum_dict


#         dum_dict= {}
#         for key in metadata['sensor']:
#             # print(key)
#             if key in metadata_streams:

#                 dum_dict[key] = metadata['sensor'][key]
#             else:
#                 continue
#         metadata['sensor'] = dum_dict

#         dum_dict= {}
#         for key in metadata['stream_units']:
#             # print(key)
#             if key in metadata_streams:

#                 dum_dict[key] = metadata['stream_units'][key]
#             else:
#                 continue


#         metadata['stream_units'] = dum_dict

#     else:
#         continue
    
#     if len(df_final) < 10:
#         print('less than 10 - skipping station ', station)
#         continue
    
#     df_final = drop_nan_years(df_final)
    

#     if df_final.isnull().values.all() == True:
#         continue
#     # break
#     os.makedirs(os.path.join(new_crowd_stations_root,station), exist_ok=True)
#     metadata['type'] = 'crowd_pre'
#     write_json_file(os.path.join(new_crowd_stations_root,station,f'{station}.json'),metadata)
#     write_csv_file(os.path.join(new_crowd_stations_root,station,f'{station}.csv'), df_final)
#     del df, df_final, metadata
    



print('Starting Sencom')

for idx, filename in enumerate(os.listdir(root_sencom_hourly)):
    if idx % 100 == 0:
        print(f'{idx}/{len(os.listdir(root_sencom_hourly))} Copying sencom data and segregating based on ID.')
        # Check if the file is a CSV
    if filename.endswith('.csv'):
        # Extract the unique identifier (assuming format: YYYY-MM_identifier.csv)
        try:
            identifier = filename.split('_')[1].split('.')[0]
        except IndexError:
            print(f"Skipping file {filename}: Unable to extract identifier")
            continue
        
        # Create destination directory for the identifier if it doesn't exist
        identifier_path = os.path.join(root_sencom_id, identifier)
        os.makedirs(identifier_path, exist_ok=True)
        
        # Full paths for source and destination
        source_file = os.path.join(root_sencom_hourly, filename)
        destination_file = os.path.join(identifier_path, filename)
        # print(source_file,destination_file)
        # # Move the file
        try:

            shutil.copy(source_file, destination_file)
            # shutil.move(source_file, destination_file)
            # print(f"Copied {filename} to {identifier_path}")
        except Exception as e:
            print(f"Error moving {filename}: {e}")
sensor_file_counters = {}

print('Creating the root for sencom')
# Iterate through sensor name folders
for sens_name in os.listdir(root_sencom_id):
    sens_folder_path = os.path.join(root_sencom_id, sens_name)
    
    # Skip if not a directory
    if not os.path.isdir(sens_folder_path):
        continue
    
    # Iterate through CSV files in the sensor folder
    for sens_file in os.listdir(sens_folder_path):
        # Skip non-CSV files
        if not sens_file.endswith('.csv'):
            continue
        
        # Full path to the current CSV file
        sens_file_path = os.path.join(sens_folder_path, sens_file)
        
        try:
            # Read the CSV file
            df = pd.read_csv(sens_file_path, delimiter=';')
            
            # Check if 'sensor_id' column exists
            if 'sensor_id' not in df.columns:
                print(f"Warning: No 'sensor_id' column in {sens_file}")
                continue
            
            # Group by sensor ID
            grouped = df.groupby('sensor_id')
            
            # Process each sensor ID group
            for sensor_id, group in grouped:
                # Convert sensor_id to string to use as directory name
                sensor_id_str = str(sensor_id)
                
                # Create sensor ID directory if it doesn't exist
                sensor_id_dir = os.path.join(sencom_root, sensor_id_str)
                os.makedirs(sensor_id_dir, exist_ok=True)
                
                # Initialize or increment file counter for this sensor ID and device
                key = (sensor_id, sens_name)
                if key not in sensor_file_counters:
                    sensor_file_counters[key] = 0
                else:
                    sensor_file_counters[key] += 1
                
                # Create output filename
                output_filename = f"{sens_name}_{sensor_id}_{sensor_file_counters[key]}.csv"
                output_path = os.path.join(sensor_id_dir, output_filename)
                
                # Save the group to a new CSV
                group.to_csv(output_path, index=False)
                
                # print(f"Created: {output_path}")
        
        except Exception as e:
            print(f"Error processing {sens_file}: {e}")




gdf = gpd.read_file('./utils/NLBLGER_JSON.geojson')
def locate_country(gdf, longitude, latitude):

    point = Point(longitude, latitude)
    
    for index, row in gdf.iterrows():
        if row.geometry.contains(point):
            return row['NAME'] 
    
    return None


def create_paths(station,root):
    return os.path.join(root,station), os.path.join(root,station,f'{station}.json'), os.path.join(root,station,f'{station}.csv')

def write_json_file(file_path, data):
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)

# Input and output directories

# Ensure the output root directory exists
os.makedirs(sencom_final_root, exist_ok=True)

# Iterate through sensor ID folders
for sensor_id in os.listdir(sencom_root):
    
    sensor_id_path = os.path.join(sencom_root, sensor_id)
    
    # Skip if not a directory
    if not os.path.isdir(sensor_id_path):
        continue
    
    # List all CSV files for this sensor ID
    csv_files = [f for f in os.listdir(sensor_id_path) if f.endswith('.csv')]
    
    # Skip if no CSV files
    if not csv_files:
        continue
    
    # List to store dataframes
    dataframes = []
    
    # Read and process each CSV file
    for csv_file in csv_files:
        try:
            # Full path to the current CSV file
            csv_path = os.path.join(sensor_id_path, csv_file)
            
            # Read the CSV file
            df = pd.read_csv(csv_path)
            
            # Extract sensor name from the filename (assuming format: sensorname_sensorid_suffix.csv)
            sensor_name = csv_file.split('_')[0]
            
            # Add sensor name column
            df['sensor_name'] = sensor_name
            
            dataframes.append(df)
            del df
        
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")
    
    # Combine all dataframes
    if dataframes:
        combined_df = pd.concat(dataframes, ignore_index=True)
        
        # Sort by timestamp column (assumes timestamp column exists)
        # If your timestamp column has a different name, modify accordingly
        if 'timestamp' in combined_df.columns:
            combined_df = combined_df.sort_values('timestamp')
        
        # Create output directory for this sensor ID in the final root
        output_sensor_dir = os.path.join(sencom_final_root, sensor_id)
        os.makedirs(output_sensor_dir, exist_ok=True)
        
        # Create output filename
        output_filename = f"{sensor_id}.csv"
        output_path = os.path.join(output_sensor_dir, output_filename)
        combined_df = combined_df.rename(columns={'timestamp':'time'})
        # Save the combined CSV
        combined_df.to_csv(output_path, index=False)
        
        # print(f"Combined CSV created: {output_path}")


def convert_to_epoch(filepath):
    """Convert 'time' column from UTC datetime to epoch time for a single CSV file."""
    try:
        # Read the CSV file
        df = pd.read_csv(filepath)
        
        if 'time' not in df.columns:
            print(f"Warning: 'time' column not found in {filepath}")
            return False
        
        # Convert time string to datetime and then to epoch
        df['time'] = pd.to_datetime(df['time'])
        df['time'] = df['time'].apply(lambda x: int(x.timestamp()))
        
        # Save back to the same file
        df.to_csv(filepath, index=False)
        # print(f"Successfully processed {filepath}")
        return True
        
    except Exception as e:
        print(f"Error processing {filepath}: {str(e)}")
        return False

# Get the root directory

# Find all CSV files that match the folder name pattern
csv_files = []
for folder in os.listdir(sencom_final_root):
    folder_path = Path(sencom_final_root) / folder
    if folder_path.is_dir():
        csv_file = folder_path / f"{folder}.csv"
        if csv_file.exists():
            csv_files.append(str(csv_file))

# Use multiprocessing to process files in parallel
with mp.Pool(processes=mp.cpu_count()) as pool:
    results = pool.map(convert_to_epoch, csv_files)

# Print summary
successful = sum(results)
total = len(csv_files)
print(f"\n Preparing complete for Sencom.")


for idx, station in enumerate(os.listdir(sencom_final_root)):
    if idx%100 ==0:
        print(f'Creating metadata. {idx}/{len(os.listdir(sencom_final_root))}')
    station_path, json_path, csv_path = create_paths(station,sencom_final_root)
    df = pd.read_csv(csv_path)
    lon = df['lon'].unique()[0]
    lat =  df['lat'].unique()[0]
    json_data = {
                "type": 'sencom',
                'longitude': lon,
                'latitude': lat,
                'country': locate_country(gdf,lon,lat),
                'iot_id': station,
                'sensor': df['sensor_name'].iloc[0],
                'available_streams':[element for element in df.columns[5:-1]],
                'start_time': int(df['time'].iloc[0]),
                'end_time': int(df['time'].iloc[-1]),
                'datastreams_links': 'https://archive.sensor.community/'
                
    }
    try:
        write_json_file(json_path,json_data)
    except:
        json_data.pop('start_time')
        json_data.pop('end_time')
        write_json_file(json_path,json_data)


    del df

'''
Phase 6 (optional - afterthought) - renaming for uniqueness by adding 'sencom' at start
'''

stations = os.listdir(sencom_final_root)
for station in stations:
    station_path, json_path, csv_path = create_paths(station,sencom_final_root)
    new_station_path = os.path.join(sencom_final_root,f'sencom_{station}')
    new_csv_path = os.path.join(station_path,f'sencom_{station}.csv')
    new_json_path = os.path.join(station_path,f'sencom_{station}.json')
    os.rename(csv_path,new_csv_path)
    os.rename(json_path,new_json_path)
    os.rename(station_path,new_station_path)
    



print(f"Successfully processed {successful} out of {total} files. Starting DBSCAN now.")





batch_size = 1440
YEAR_HOURS = 8760

os.makedirs(sencom_dbscan_root, exist_ok=True)
for station in os.listdir(sencom_final_root):
    # print(f'now at station {station}')
    station_path = os.path.join(sencom_final_root,station)
    csv_path = os.path.join(station_path,f'{station}.csv')
    json_path = os.path.join(station_path,f'{station}.json')
    metadata = load_json_file(json_path)
    # try:
    #     df = pd.read_csv(csv_path).iloc[-52596:,:]
    #     print('loading only 52596')
    # except:
    #     df = pd.read_csv(csv_path)
    #     print('loading all')
    
    df = pd.read_csv(csv_path)
    metadata_streams = [stream for stream in metadata['available_streams']]
    if metadata_streams != []:
        df_final = pd.DataFrame()

        for i in range(0, len(df), batch_size):
            df_final = pd.concat([df_final,run_dbscan_on_df(df.iloc[i:i+batch_size,:],metadata_streams,dbs_radius=1.5)])


    else:
        continue
    
    if df_final.empty == True:
        continue
    df_final = drop_nan_years(df_final)
    if df_final.empty == True:
        continue
    
    os.makedirs(os.path.join(sencom_dbscan_root,f'{station}_PRE'), exist_ok=True)
    metadata['type'] = 'sencom_pre'
    write_json_file(os.path.join(sencom_dbscan_root,f'{station}_PRE',f'{station}_PRE.json'),metadata)
    write_csv_file(os.path.join(sencom_dbscan_root,f'{station}_PRE',f'{station}_PRE.csv'), df_final)
    del df, df_final, metadata





RANGES = {
    'PM10':(-50,1000),
    'PM2.5':(-50,1000),
    'pm10':(-50,1000),
    'Ox': (-70,500),
    'ZWR': (0,400),
    'PM10':(-50,1000),
    'pres': (900,1300),
    'no2': (0,750),
    'pm10_kal':(-50,1000),
    'BC': (-5,40),
    'pm25':(-50,1000),
    'CO': (-500,20000),
    'NOx':(-50, 2000),
    'NO':(-20,2000),
    'O3':(-30,800),
    'H2S':(-10,40),
    'SO2':(-30,1500),
    'NH3':(-20,1000),
    'NO2':(-200,1000),
    'rh':(-2,105),
    'pm25_kal':(-50,1000),
    'temp':(-50,70)



}


# make_endofhour = True
# YEAR_HOURS = 8760
# def drop_nan_years(df, make_endofhour = False):
#     # Create a copy of the original DataFrame
#     df_copy = df.copy()

#     # Convert the 'time' column to datetime and extract the year
#     df_copy['time2'] = pd.to_datetime(df_copy['time'], unit='s')

#     if make_endofhour:
#         df_copy['time2'] = df_copy['time2'] + pd.Timedelta(hours=1)
#         df_copy['time'] = df_copy['time2'].astype('int64') // 10**9  # back to epoch seconds


#     df_copy['year'] = df_copy['time2'].dt.year

#     # Calculate the percentage of non-NA values for each column in each year
#     percent_non_na = df_copy.groupby('year').apply(lambda x: x.count() / YEAR_HOURS, include_groups=False)

#     # Find the columns where any year has less than 65% non-NA values
#     columns_to_replace = percent_non_na.columns[percent_non_na.lt(0.65).any()]

#     # For these columns, replace the values for the years where it has less than 65% non-NA values with NA
#     for column in columns_to_replace:
#         years_to_replace = percent_non_na.index[percent_non_na[column] < 0.65]
#         df_copy.loc[df_copy['year'].isin(years_to_replace), column] = np.nan

#     # Return the modified DataFrame without the 'time2' and 'year' columns
#     return df_copy.iloc[:,:-2].dropna(how='all',ignore_index = True)



# print('Starting Lucht official csvs')
# batch_size = 1440

# # new_root = '/home/yahia/dummy_stations_test/'
# os.makedirs(new_luchtmeetnet_csvs_root, exist_ok=True)
# for idx, station in enumerate(os.listdir(luchtmeetnet_csvs_root)):
#     if idx%100 ==0:
#         print(f'{idx}/{len(os.listdir(luchtmeetnet_csvs_root))} Creating metadata and processing. ')
#     station_path = os.path.join(luchtmeetnet_csvs_root,station)
#     csv_path = os.path.join(station_path,f'{station}.csv')
#     json_path = os.path.join(station_path,f'{station}.json')
#     metadata = load_json_file(json_path)
#     # try:
#     #     df = pd.read_csv(csv_path).iloc[-52596:,:]
#     #     print('loading only 52596')
#     # except:
#     #     df = pd.read_csv(csv_path)
#     #     print('loading all')
    
#     df = pd.read_csv(csv_path)
#     metadata_streams = [stream for stream in metadata['available_streams']]
#     if metadata_streams != []:
#         df_final = pd.DataFrame()

#         for i in range(0, len(df), batch_size):
#             df_final = pd.concat([df_final,run_dbscan_on_df(df.iloc[i:i+batch_size,:],metadata_streams,dbs_radius=1)])


#         dum_dict= {}
#         for key in metadata['sensor']:
#             # print(key)
#             if key in metadata['available_streams']:

#                 dum_dict[key] = metadata['sensor'][key]
#             else:
#                 continue
#         metadata['sensor'] = dum_dict

#         dum_dict= {}
#         for key in metadata['stream_units']:
#             # print(key)
#             if key in metadata['available_streams']:

#                 dum_dict[key] = metadata['stream_units'][key]
#             else:
#                 continue

#         metadata['stream_units'] = dum_dict

#     else:
#         continue

#     df_final = drop_nan_years(df_final, make_endofhour = make_endofhour)
#     if df_final.empty == True:
#         continue
        
#     os.makedirs(os.path.join(new_luchtmeetnet_csvs_root,f'{station}_PRE'), exist_ok=True)
#     metadata['type'] = 'official_val_pre'
#     write_json_file(os.path.join(new_luchtmeetnet_csvs_root,f'{station}_PRE',f'{station}_PRE.json'),metadata)
#     write_csv_file(os.path.join(new_luchtmeetnet_csvs_root,f'{station}_PRE',f'{station}_PRE.csv'), df_final)
#     del df, df_final, metadata

DOWNLOAD_LUCHTMEETNETCSVS = False
make_endofhour = False
YEAR_HOURS = 8760

# Make sure directories exist
os.makedirs(zip_dir, exist_ok=True)
os.makedirs(extract_dir, exist_ok=True)
if DOWNLOAD_LUCHTMEETNETCSVS:
    # Loop through years
    for year in range(1976, 2025):
        
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





# Variable mapping dictionary


print('DBSCAN')
batch_size = 1440
# new_root = '/home/yahia/dummy_stations_test/'
os.makedirs(luchtmeetnet_csv_dbscan, exist_ok=True)
for idx, station in enumerate(os.listdir(final_official_station)):
    if idx%100 ==0:
        print(f'{idx}/{len(os.listdir(final_official_station))} Creating metadata and processing. ')
    station_path = os.path.join(final_official_station,station)
    csv_path = os.path.join(station_path,f'{station}.csv')
    json_path = os.path.join(station_path,f'{station}.json')

    metadata = load_json_file(json_path)
    df = pd.read_csv(csv_path)
    df = df.rename(columns=lambda c: variable_mapping.get(c, c))
    

    # --- Normalize metadata list ---
    metadata_streams = [variable_mapping.get(item, item) for item in metadata['available_streams']]



    # metadata_streams = [stream for stream in metadata['available_streams']]
    if metadata_streams != []:
        df_final = pd.DataFrame()

        for i in range(0, len(df), batch_size):
            df_final = pd.concat([df_final,run_dbscan_on_df(df.iloc[i:i+batch_size,:],metadata_streams,dbs_radius=1)])

        # for key in metadata['sensor']:
        #     # print(key)
        #     if key in metadata['available_streams']:

        #         dum_dict[key] = metadata['sensor'][key]
        #     else:
        #         continue
        # metadata['sensor'] = dum_dict

        dum_dict= {}
        for key in metadata['stream_units']:
            # print(key)
            dum_key = variable_mapping.get(key,key)
            if key in metadata['available_streams']:
                

                dum_dict[dum_key] =  metadata['stream_units'][key]
            else:
                continue
        metadata['stream_units'] = dum_dict
        metadata['available_streams'] = metadata_streams
        # metadata['country'] = 'Netherlands'


    else:
        continue
    
    if df_final.empty:
        continue
    df_final = drop_nan_years(df_final, make_endofhour = make_endofhour)
    if df_final.empty == True:
        continue

    df_final['time'] = df_final['time'].astype(int)

    os.makedirs(os.path.join(luchtmeetnet_csv_dbscan,f'{station}_PRE'), exist_ok=True)
    metadata['type'] = 'official_val_pre'
    write_json_file(os.path.join(luchtmeetnet_csv_dbscan,f'{station}_PRE',f'{station}_PRE.json'),metadata)
    write_csv_file(os.path.join(luchtmeetnet_csv_dbscan,f'{station}_PRE',f'{station}_PRE.csv'), df_final)
    
    del df, df_final, metadata


print('Starting Lucht Root')

batch_size = 1440
YEAR_HOURS = 8760




os.makedirs(lucht_root_dbscan, exist_ok=True)
for station in os.listdir(lucht_root):
    if idx%100 ==0:
        print(f'{idx}/{len(os.listdir(lucht_root))} Creating metadata and processing. ')
    station_path = os.path.join(lucht_root,station)
    csv_path = os.path.join(station_path,f'{station}.csv')
    json_path = os.path.join(station_path,f'{station}.json')
    metadata = load_json_file(json_path)
    
    df = pd.read_csv(csv_path)
    metadata_streams = [stream for stream in metadata['available_streams']]
    
    if metadata_streams != []:
        df_final = pd.DataFrame()

        for i in range(0, len(df), batch_size):
            df_final = pd.concat([df_final,run_dbscan_on_df(df.iloc[i:i+batch_size,:],metadata_streams,dbs_radius=1.5)])


    else:
        continue
    
    if df_final.empty == True:
        continue
    df_final = drop_nan_years(df_final)
    if df_final.empty == True:
        continue
    
    os.makedirs(os.path.join(lucht_root_dbscan,f'{station}_PRE'), exist_ok=True)
    metadata['type'] = 'official_unval_pre'
    write_json_file(os.path.join(lucht_root_dbscan,f'{station}_PRE',f'{station}_PRE.json'),metadata)
    write_csv_file(os.path.join(lucht_root_dbscan,f'{station}_PRE',f'{station}_PRE.csv'), df_final)
    del df, df_final, metadata


print('Starting SamenMeten')
YEAR_HOURS = 8760

def create_paths(station, root):
    return os.path.join(root,station), os.path.join(root,station,f'{station}.json'), os.path.join(root,station,f'{station}.csv')

batch_size = 1440
totalnumfiles=os.listdir(crowd_stations_root)
os.makedirs(crowd_stations_dbscan_root, exist_ok=True)
for idx, station in enumerate(os.listdir(crowd_stations_root)):
    if idx % 100==0:
        print(f'{idx}/{len(totalnumfiles)}: now at station {station}')
    station_path, json_path, csv_path = create_paths(station, crowd_stations_root)
    metadata = load_json_file(json_path)
    if metadata['has_data'] == 'False':
        continue
    # try:
    #     df = pd.read_csv(csv_path).iloc[-52596:,:]
    #     print('loading only 52596')
    # except:
    #     df = pd.read_csv(csv_path)
    #     print('loading all')
    
    df = pd.read_csv(csv_path)
    

    metadata_streams = list(df.columns[1:])
    if metadata_streams != []:
        df_final = pd.DataFrame()

        for i in range(0, len(df), batch_size):
            df_final = pd.concat([df_final,run_dbscan_on_df(df.iloc[i:i+batch_size,:],metadata_streams,dbs_radius=1)])
            

        
        dum_dict= {}
        for key in metadata['available_streams']:
            # print(key)
            if key in metadata_streams:

                dum_dict[key] = metadata['available_streams'][key]
            else:
                continue
        metadata['available_streams'] = dum_dict


        dum_dict= {}
        for key in metadata['sensor']:
            # print(key)
            if key in metadata_streams:

                dum_dict[key] = metadata['sensor'][key]
            else:
                continue
        metadata['sensor'] = dum_dict

        dum_dict= {}
        for key in metadata['stream_units']:
            # print(key)
            if key in metadata_streams:

                dum_dict[key] = metadata['stream_units'][key]
            else:
                continue


        metadata['stream_units'] = dum_dict

    else:
        continue
    
    if len(df_final) < 10:
        print('less than 10 - skipping station ', station)
        continue
    
    df_final = drop_nan_years(df_final)
    

    if df_final.isnull().values.all() == True:
        continue
    # break
    os.makedirs(os.path.join(crowd_stations_dbscan_root,station), exist_ok=True)
    metadata['type'] = 'crowd_pre'
    write_json_file(os.path.join(crowd_stations_dbscan_root,station,f'{station}.json'),metadata)
    write_csv_file(os.path.join(crowd_stations_dbscan_root,station,f'{station}.csv'), df_final)
    del df, df_final, metadata
    

shutil.copytree(knmi_root, knmi_dest_dir)



def process_directory(source_root, target_root, variable_mapping):
    # Create target root directory if it doesn't exist
    os.makedirs(target_root, exist_ok=True)
    
    # Walk through the directory structure
    for layer2_path in os.listdir(source_root):
        layer2_full_path = os.path.join(source_root, layer2_path)
        if not os.path.isdir(layer2_full_path):
            continue
            
        # Create corresponding layer2 directory in target
        new_layer2_path = os.path.join(target_root, layer2_path)
        os.makedirs(new_layer2_path, exist_ok=True)
        
        # Process layer3 folders
        for layer3_path in os.listdir(layer2_full_path):
            layer3_full_path = os.path.join(layer2_full_path, layer3_path)
            if not os.path.isdir(layer3_full_path):
                continue
                
            # Create corresponding layer3 directory in target
            new_layer3_path = os.path.join(new_layer2_path, layer3_path)
            os.makedirs(new_layer3_path, exist_ok=True)
            
            # Process JSON file
            json_file = os.path.join(layer3_full_path, f"{os.path.basename(layer3_path)}.json")
            if os.path.exists(json_file):
                process_json_file(json_file, new_layer3_path, variable_mapping)
            
            # Process CSV file
            csv_file = os.path.join(layer3_full_path, f"{os.path.basename(layer3_path)}.csv")
            if os.path.exists(csv_file):
                process_csv_file(csv_file, new_layer3_path, variable_mapping)


def process_json_file(json_file, target_dir, variable_mapping):
    # Read existing JSON file
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
    except:
        data = {}
    
    # Create new JSON structure with required keys
    new_data = {
        "type": data.get("type", ""),
        "longitude": data.get("longitude", ""),
        "latitude": data.get("latitude", ""),
        "country": data.get("country", ""),
        "location": data.get("location", ""),
        "available_streams": []
    }
    
    # Process available_streams
    if "available_streams" in data:
        streams = data["available_streams"]
        if isinstance(streams, dict):
            streams = list(streams.keys())
        elif not isinstance(streams, list):
            streams = [streams] if streams else []
            
        # Map stream names using the variable mapping
        new_data["available_streams"] = [
            variable_mapping.get(stream, stream) for stream in streams
        ]
    
    # Save new JSON file
    target_file = os.path.join(target_dir, os.path.basename(json_file))
    with open(target_file, 'w') as f:
        json.dump(new_data, f, indent=4)

def process_csv_file(csv_file, target_dir, variable_mapping):
    try:
        # Read CSV file
        df = pd.read_csv(csv_file)
        
        # Rename columns based on mapping
        new_columns = {}
        for col in df.columns:
            if col in variable_mapping:
                new_columns[col] = variable_mapping[col]
        
        if new_columns:
            df = df.rename(columns=new_columns)

        if 'time' in df.columns:
            # First convert to float to handle any string values, then to int
            df['time'] = df['time'].astype(float).astype(int)
        
        # Save processed CSV file
        target_file = os.path.join(target_dir, os.path.basename(csv_file))
        df.to_csv(target_file, index=False)
    except Exception as e:
        print(f"Error processing CSV file {csv_file}: {str(e)}")





process_directory(source_root, target_root, variable_mapping)
print("Processing completed successfully!")
if not KEEP_DUMMY:
    print(f'Deleting dummy directory: {DUMMY_HOLDER}')
    shutil.rmtree(DUMMY_HOLDER)

# to_remove = ['sencom_final_root','sencom_id','sencom_root','luchtmeetnet_csvs']
to_remove = ['sencom_final_root','sencom_id','sencom_root']

for folder_name in to_remove:
    folder_path = os.path.join(target_root, folder_name)
    if os.path.isdir(folder_path):
        shutil.rmtree(folder_path)
        print(f"Removed directory: {folder_path}")
    else:
        print(f"Directory not found, skipping: {folder_path}")





data_dir = os.path.join(FINAL_DIR, "data")
metadata_dir = os.path.join(FINAL_DIR, "metadata")

# Create data and metadata folders
os.makedirs(data_dir, exist_ok=True)

# Iterate over all subfolders in base_dir
for folder in os.listdir(FINAL_DIR):
    folder_path = os.path.join(FINAL_DIR, folder)

    # Skip "data" and "metadata" (we don’t want recursion)
    if folder in ["data", "metadata", "luchtmeetnet_csvs", "lucht_root_dbscan"]:
        continue

    if os.path.isdir(folder_path):
        # Copy all contents of this folder into data_dir
        for item in os.listdir(folder_path):
            src = os.path.join(folder_path, item)
            dst = os.path.join(data_dir, item)

            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)  # Merge if already exists
            else:
                shutil.copy2(src, dst)

os.makedirs(metadata_dir, exist_ok=True)

print("Data collected in:", data_dir)
print("Metadata folder created:", metadata_dir)







## CREATE FINAL DATA FOLDER FOR PYTORCH



os.makedirs(f'{FINAL_DIR}/metadata/grids',exist_ok=True)
os.makedirs(f'{FINAL_DIR}/metadata/stations_within_grids',exist_ok=True)
os.makedirs(f'{FINAL_DIR}/final_dataset',exist_ok=True)
os.makedirs(LCS_BULK_PATH,exist_ok=True)
os.makedirs(TEST_SET_PATH,exist_ok=True)
metadata_creation.one_time_full_metadata(output = FULL_METADATA_PATH)
metadata_creation.create_grid('./utils/NLBLGER_JSON.geojson',FULL_GRIDS_PATH,spacing_km=5)
FULL_METADATA = load_json_file(FULL_METADATA_PATH)
FULL_GRIDS = load_json_file(FULL_GRIDS_PATH)
metadata_creation.group_stations_by_grid(FULL_METADATA, FULL_GRIDS, 5000, True, STATIONS_WITHIN_GRIDS_PATH)
STATIONS_WITHIN_GRIDS = load_json_file(STATIONS_WITHIN_GRIDS_PATH)


implemented_cities = ['rotterdam', 'utrecht', 'amsterdam', 'groningen', 'hague', 'ijmuiden', 'nijmegen']
premade_datasets_path = TEST_SET_PATH
lcs_bulk_store = LCS_BULK_PATH
# premade_filtered_datasets_path = '/home/yahia/final_dataset/pre_prepared datasets_filtered'


grid_coords = FULL_GRIDS['Netherlands']
dum_index =[]
cols_lim=10
std_multiplier = float('inf')
latent_dimension = 5
used_coords = [[4.347378645577175, 52.064831455904184],
                [6.568574391543857, 53.2151410086018],
                [4.624085111798515, 52.46571257006848],
                [5.85738536473926, 51.84182535853894],
                [4.890337958798472, 52.36888246467895],
                [5.108, 52.082],
                [4.463, 51.921]]
for coords in grid_coords:
    data = metadata_creation.find_sensors_in_radius(full_meta = FULL_METADATA, 
                              center_lon = coords[0], 
                              center_lat = coords[1],  
                              radius_km= 5, 
                              variable_list = ['pm25'])
    if len(data['Netherlands'])>10:
        dum_index.append([coords,data['Netherlands']])

unique_coords = metadata_creation.filter_intersecting_lists(dum_index,with_coordinates=True)
final_coords = create_lcs_only.filter_unique_coordinates(unique_coords, used_coords,5)



for idx, coords in enumerate(final_coords):
    print(idx, coords, '-----')
    data = metadata_creation.find_sensors_in_radius(full_meta = FULL_METADATA, 
                                    center_lon = coords[0], 
                                    center_lat = coords[1],  
                                    radius_km= 5, 
                                    variable_list = ['pm25'])
    loaded_data = create_lcs_only.no_alignment_dataloader(data,
        keep_columns = ['time','temp','rh','pm25','pm10'],
        must_columns = ['pm25'],
                regions = 'all',
                remove_empty_df=True)

    # Example usage:
    merged_data = create_lcs_only.merge_sensor_dataframes(loaded_data['Netherlands'], discard_specific_ids=True)



    lcs_stations = merged_data.copy()
    lcs_selected = metadata_creation.select_best_columns(metadata_creation.fill_continuous_timestamps(lcs_stations), limit_columns=cols_lim)
    # drop_cols = [item for item in lcs_stations.columns if 'VAL_PRE' in item]
    full_lcs = lcs_selected.dropna(thresh=(latent_dimension+1))
    full_lcs_notime = full_lcs.drop(columns='time')



    total_mean = full_lcs_notime.mean().mean()
    total_std = full_lcs_notime.mean().std()
    spike_thresh = total_mean + std_multiplier*total_std
    full_lcs_filter_notime = metadata_creation.mask_extended_zeros(full_lcs_notime.where((full_lcs_notime<spike_thresh), other=pd.NA))

    full_lcs_filter = full_lcs.copy(deep=True)
    full_lcs_filter.iloc[:,1:] = full_lcs_filter_notime.copy()

    if full_lcs_filter.empty:
        print(f'{idx}, {coords} has empty df---------' )
        # empty.append(coords)
        continue
    
    full_lcs_filter = create_lcs_only.filter_half_na_rows(full_lcs_filter).reset_index(drop=True)
    loc_name = create_lcs_only.get_location_name(coords).replace(" ", "_").replace("'","")
    store_path = os.path.join(lcs_bulk_store,f'{loc_name}_{coords[0]}_{coords[1]}_lcs.csv')
    
    write_csv_file(store_path,full_lcs_filter)
    time.sleep(1)



'''
The following part is hard coded - do not change anything please :).
'''



lat_utrecht = 52.082
lon_utrecht = 5.108
utrecht_path_lcs = f'{FINAL_DIR}/final_dataset/pre_prepared_datasets_unfiltered/utrecht_{lon_utrecht}_{lat_utrecht}_lcs.csv'
utrecht_path_reference = f'{FINAL_DIR}/final_dataset/pre_prepared_datasets_unfiltered/utrecht_{lon_utrecht}_{lat_utrecht}_ref.csv'
lat_rotterdam = 51.921
lon_rotterdam = 4.463
rotterdam_path_lcs = f'{FINAL_DIR}/final_dataset/pre_prepared_datasets_unfiltered/rotterdam_{lon_rotterdam}_{lat_rotterdam}_lcs.csv'
rotterdam_path_reference = f'{FINAL_DIR}/final_dataset/pre_prepared_datasets_unfiltered/rotterdam_{lon_rotterdam}_{lat_rotterdam}_ref.csv'
lat_ijmuiden = 52.46571257006848
lon_ijmuiden = 4.624085111798515
ijmuiden_path_lcs = f'{FINAL_DIR}/final_dataset/pre_prepared_datasets_unfiltered/ijmuiden_{lon_ijmuiden}_{lat_ijmuiden}_lcs.csv'
ijmuiden_path_reference = f'{FINAL_DIR}/final_dataset/pre_prepared_datasets_unfiltered/ijmuiden_{lon_ijmuiden}_{lat_ijmuiden}_ref.csv'
lat_hague = 52.064831455904184
lon_hague = 4.347378645577175
hague_path_lcs = f'{FINAL_DIR}/final_dataset/pre_prepared_datasets_unfiltered/hague_{lon_hague}_{lat_hague}_lcs.csv'
hague_path_reference = f'{FINAL_DIR}/final_dataset/pre_prepared_datasets_unfiltered/hague_{lon_hague}_{lat_hague}_ref.csv'
lat_nijmegen = 51.84182535853894
lon_nijmegen = 5.85738536473926
nijmegen_path_lcs = f'{FINAL_DIR}/final_dataset/pre_prepared_datasets_unfiltered/nijmegen_{lon_nijmegen}_{lat_nijmegen}_lcs.csv'
nijmegen_path_reference = f'{FINAL_DIR}/final_dataset/pre_prepared_datasets_unfiltered/nijmegen_{lon_nijmegen}_{lat_nijmegen}_ref.csv'
lat_groningen = 53.2151410086018
lon_groningen = 6.568574391543857
groningen_path_lcs = f'{FINAL_DIR}/final_dataset/pre_prepared_datasets_unfiltered/groningen_{lon_groningen}_{lat_groningen}_lcs.csv'
groningen_path_reference = f'{FINAL_DIR}/final_dataset/pre_prepared_datasets_unfiltered/groningen_{lon_groningen}_{lat_groningen}_ref.csv'
lat_amsterdam= 52.36888246467895
lon_amsterdam = 4.890337958798472
amsterdam_path_lcs = f'{FINAL_DIR}/final_dataset/pre_prepared_datasets_unfiltered/amsterdam_{lon_amsterdam}_{lat_amsterdam}_lcs.csv'
amsterdam_path_reference = f'{FINAL_DIR}/final_dataset/pre_prepared_datasets_unfiltered/amsterdam_{lon_amsterdam}_{lat_amsterdam}_ref.csv'


#AMSTERDAM
data = metadata_creation.find_sensors_in_radius(full_meta = FULL_METADATA,
                              center_lon = lon_amsterdam,
                              center_lat = lat_amsterdam,
                              radius_km= 5,
                              variable_list = ['pm25'])

loaded_data = metadata_creation.dataloader(data,
    keep_columns = ['time','temp','rh','pm25','pm10'],
            regions = 'all',
            align_in_time = True,
            time_decision = 'VAL',
            remove_empty_df=True)

filtered_data = metadata_creation.find_best_time(loaded_data,
                                val_id = val_id)

final_df = metadata_creation.merge_dict(filtered_data,
                variables=metadata_creation.PARAMETERS,
                thresh = 5)

drop_cols_amsterdam = ['HLL_hl_device_217_pm25','HLL_hl_device_099_pm25']



std_multiplier = 100000
latent_dimension = 5
lcs_stations = final_df['Netherlands'][[item for item in final_df['Netherlands'].columns if 'VAL_PRE' not in item]]
reference_stations = final_df['Netherlands'][[col for col in final_df['Netherlands'] if 'VAL_PRE' in col or 'time' in col]]
lcs_selected = metadata_creation.select_best_columns(metadata_creation.fill_continuous_timestamps(lcs_stations), limit_columns=10)
# drop_cols = [item for item in lcs_stations.columns if 'VAL_PRE' in item]
full_lcs = lcs_selected.dropna(thresh=(latent_dimension+1))
full_lcs_notime = full_lcs.drop(columns='time')



total_mean = full_lcs_notime.mean().mean()
total_std = full_lcs_notime.mean().std()
spike_thresh = total_mean + std_multiplier*total_std
full_lcs_filter_notime = metadata_creation.mask_extended_zeros(full_lcs_notime.where((full_lcs_notime<spike_thresh), other=pd.NA), consecutive_limit=480)

full_lcs_filter = full_lcs.copy(deep=True)
full_lcs_filter.iloc[:,1:] = full_lcs_filter_notime.copy()
write_csv_file(amsterdam_path_lcs,full_lcs_filter)
write_csv_file(amsterdam_path_reference, reference_stations)


#GRONINGEN


data = metadata_creation.find_sensors_in_radius(full_meta = FULL_METADATA, 
                              center_lon = lon_groningen, 
                              center_lat = lat_groningen,  
                              radius_km= 5, 
                              variable_list = ['pm25'])
loaded_data = metadata_creation.dataloader(data,
    keep_columns = ['time','temp','rh','pm25','pm10'],
            regions = 'all',
            align_in_time = True,
            time_decision = 'VAL',
            remove_empty_df=True)

filtered_data = metadata_creation.find_best_time(loaded_data,
                                val_id = val_id)

final_df = metadata_creation.merge_dict(filtered_data,
                variables=metadata_creation.PARAMETERS,
                thresh = 5)

drop_cols_groningen = ['LTD_11395_pm25','LTD_39034_pm25']


std_multiplier = 100000000000
latent_dimension = 5
lcs_stations = final_df['Netherlands'][[item for item in final_df['Netherlands'].columns if 'VAL_PRE' not in item]]
reference_stations = final_df['Netherlands'][[col for col in final_df['Netherlands'] if 'VAL_PRE' in col or 'time' in col]]
lcs_selected = metadata_creation.select_best_columns(metadata_creation.fill_continuous_timestamps(lcs_stations), limit_columns=10)
# drop_cols = [item for item in lcs_stations.columns if 'AL_PRE' in item]
full_lcs = lcs_selected.dropna(thresh=(latent_dimension+1))
full_lcs_notime = full_lcs.drop(columns='time')



total_mean = full_lcs_notime.mean().mean()
total_std = full_lcs_notime.mean().std()
spike_thresh = total_mean + std_multiplier*total_std
full_lcs_filter_notime = metadata_creation.mask_extended_zeros(full_lcs_notime.where((full_lcs_notime<spike_thresh), other=pd.NA), consecutive_limit=480)

full_lcs_filter = full_lcs.copy(deep=True)
full_lcs_filter.iloc[:,1:] = full_lcs_filter_notime.copy()


write_csv_file(groningen_path_lcs,full_lcs_filter)
write_csv_file(groningen_path_reference, reference_stations)


#NIJMEGEN



data = metadata_creation.find_sensors_in_radius(full_meta = FULL_METADATA, 
                              center_lon = lon_nijmegen, 
                              center_lat = lat_nijmegen,  
                              radius_km= 5, 
                              variable_list = ['pm25'])
loaded_data = metadata_creation.dataloader(data,
    keep_columns = ['time','temp','rh','pm25','pm10'],
            regions = 'all',
            align_in_time = True,
            time_decision = 'VAL',
            remove_empty_df=True)

filtered_data = metadata_creation.find_best_time(loaded_data,
                                val_id = val_id)

final_df = metadata_creation.merge_dict(filtered_data,
                variables=metadata_creation.PARAMETERS,
                thresh = 5)
drop_cols_nijmegen = ['GRC_1305167546908780_pm25','OHN_ro-1018_pm25']


std_multiplier = 100000000
latent_dimension = 5
lcs_stations = final_df['Netherlands'][[item for item in final_df['Netherlands'].columns if 'VAL_PRE' not in item]]
reference_stations = final_df['Netherlands'][[col for col in final_df['Netherlands'] if 'VAL_PRE' in col or 'time' in col]]
lcs_selected = metadata_creation.select_best_columns(metadata_creation.fill_continuous_timestamps(lcs_stations), limit_columns=10)
full_lcs_notime = full_lcs.drop(columns='time')



total_mean = full_lcs_notime.mean().mean()
total_std = full_lcs_notime.mean().std()
spike_thresh = total_mean + std_multiplier*total_std
full_lcs_filter_notime = metadata_creation.mask_extended_zeros(full_lcs_notime.where((full_lcs_notime<spike_thresh), other=pd.NA), consecutive_limit=480)

full_lcs_filter = full_lcs.copy(deep=True)
full_lcs_filter.iloc[:,1:] = full_lcs_filter_notime.copy()

write_csv_file(nijmegen_path_lcs,full_lcs_filter)
write_csv_file(nijmegen_path_reference, reference_stations)


#HAGUE



data = metadata_creation.find_sensors_in_radius(full_meta = FULL_METADATA, 
                              center_lon = lon_hague, 
                              center_lat = lat_hague,  
                              radius_km= 5, 
                              variable_list = ['pm25'])
loaded_data = metadata_creation.dataloader(data,
    keep_columns = ['time','temp','rh','pm25','pm10'],
            regions = 'all',
            align_in_time = True,
            time_decision = 'VAL',
            remove_empty_df=True)

filtered_data = metadata_creation.find_best_time(loaded_data,
                                val_id = val_id)

final_df = metadata_creation.merge_dict(filtered_data,
                variables=metadata_creation.PARAMETERS,
                thresh = 5)

drop_cols_hague = ['NBI_SB945_pm25','NBI_SB954_pm25']


std_multiplier = 100000
latent_dimension = 5
lcs_stations = final_df['Netherlands'][[item for item in final_df['Netherlands'].columns if 'VAL_PRE' not in item]]
reference_stations = final_df['Netherlands'][[col for col in final_df['Netherlands'] if 'VAL_PRE' in col or 'time' in col]]
lcs_selected = metadata_creation.select_best_columns(metadata_creation.fill_continuous_timestamps(lcs_stations), limit_columns=10)
# drop_cols = [item for item in lcs_stations.columns if 'VAL_PRE' in item]
full_lcs = lcs_selected.dropna(thresh=(latent_dimension+1))
full_lcs_notime = full_lcs.drop(columns='time')



total_mean = full_lcs_notime.mean().mean()
total_std = full_lcs_notime.mean().std()
spike_thresh = total_mean + std_multiplier*total_std
full_lcs_filter_notime = metadata_creation.mask_extended_zeros(full_lcs_notime.where((full_lcs_notime<spike_thresh), other=pd.NA), consecutive_limit=480)

full_lcs_filter = full_lcs.copy(deep=True)
full_lcs_filter.iloc[:,1:] = full_lcs_filter_notime.copy()

write_csv_file(hague_path_lcs,full_lcs_filter)
write_csv_file(hague_path_reference, reference_stations)


#IJMUIDEN



data = metadata_creation.find_sensors_in_radius(full_meta = FULL_METADATA, 
                              center_lon = lon_ijmuiden, 
                              center_lat = lat_ijmuiden,  
                              radius_km= 5, 
                              variable_list = ['pm25'])
loaded_data = metadata_creation.dataloader(data,
    keep_columns = ['time','temp','rh','pm25','pm10'],
            regions = 'all',
            align_in_time = True,
            time_decision = 'VAL',
            remove_empty_df=True)

filtered_data = metadata_creation.find_best_time(loaded_data,
                                val_id = val_id)

final_df = metadata_creation.merge_dict(filtered_data,
                variables=metadata_creation.PARAMETERS,
                thresh = 5)

drop_cols_ijmuiden = ['GEOMOBILEMX0_GEOMOBILEMX1_HLL_hl_device_237_pm25','HLL_hl_device_024_pm25']


std_multiplier = 100000
latent_dimension = 5
lcs_stations = final_df['Netherlands'][[item for item in final_df['Netherlands'].columns if 'VAL_PRE' not in item]]
reference_stations = final_df['Netherlands'][[col for col in final_df['Netherlands'] if 'VAL_PRE' in col or 'time' in col]]
lcs_selected = metadata_creation.select_best_columns(metadata_creation.fill_continuous_timestamps(lcs_stations), limit_columns=10)
# drop_cols = [item for item in lcs_stations.columns if 'VAL_PRE' in item]
full_lcs = lcs_selected.dropna(thresh=(latent_dimension+1))
full_lcs_notime = full_lcs.drop(columns='time')



total_mean = full_lcs_notime.mean().mean()
total_std = full_lcs_notime.mean().std()
spike_thresh = total_mean + std_multiplier*total_std
full_lcs_filter_notime = metadata_creation.mask_extended_zeros(full_lcs_notime.where((full_lcs_notime<spike_thresh), other=pd.NA), consecutive_limit=480)

full_lcs_filter = full_lcs.copy(deep=True)
full_lcs_filter.iloc[:,1:] = full_lcs_filter_notime.copy()


write_csv_file(ijmuiden_path_lcs,full_lcs_filter)
write_csv_file(ijmuiden_path_reference, reference_stations)

#ROTTERDAM



data = metadata_creation.find_sensors_in_radius(full_meta = FULL_METADATA, 
                              center_lon = lon_rotterdam, 
                              center_lat = lat_rotterdam,  
                              radius_km= 5, 
                              variable_list = ['pm25'])
loaded_data = metadata_creation.dataloader(data,
    keep_columns = ['time','temp','rh','pm25','pm10'],
            regions = 'all',
            align_in_time = True,
            time_decision = 'VAL',
            remove_empty_df=True)

filtered_data = metadata_creation.find_best_time(loaded_data,
                                val_id = val_id)

final_df = metadata_creation.merge_dict(filtered_data,
                variables=metadata_creation.PARAMETERS,
                thresh = 5)

drop_cols_rotterdam = [ 'LTD_39641_pm25','SSK_LD013_pm25','SSK_LD007_pm25','SSK_LD017_pm25']


std_multiplier = 100000
latent_dimension = 5
lcs_stations = final_df['Netherlands'][[item for item in final_df['Netherlands'].columns if 'VAL_PRE' not in item]]
reference_stations = final_df['Netherlands'][[col for col in final_df['Netherlands'] if 'VAL_PRE' in col or 'time' in col]]
lcs_selected = metadata_creation.select_best_columns(metadata_creation.fill_continuous_timestamps(lcs_stations), limit_columns=10)
# drop_cols = [item for item in lcs_stations.columns if 'VAL_PRE' in item]
full_lcs = lcs_selected.dropna(thresh=(latent_dimension+1))
full_lcs_notime = full_lcs.drop(columns='time')



total_mean = full_lcs_notime.mean().mean()
total_std = full_lcs_notime.mean().std()
spike_thresh = total_mean + std_multiplier*total_std
full_lcs_filter_notime = metadata_creation.mask_extended_zeros(full_lcs_notime.where((full_lcs_notime<spike_thresh), other=pd.NA), consecutive_limit=480)

full_lcs_filter = full_lcs.copy(deep=True)
full_lcs_filter.iloc[:,1:] = full_lcs_filter_notime.copy()


write_csv_file(rotterdam_path_lcs,full_lcs_filter)
write_csv_file(rotterdam_path_reference, reference_stations)

#UTRECHT




data = metadata_creation.find_sensors_in_radius(full_meta = FULL_METADATA, 
                              center_lon = lon_utrecht, 
                              center_lat = lat_utrecht,  
                              radius_km= 5, 
                              variable_list = ['pm25'])
loaded_data = metadata_creation.dataloader(data,
    keep_columns = ['time','temp','rh','pm25','pm10'],
            regions = 'all',
            align_in_time = True,
            time_decision = 'VAL',
            remove_empty_df=True)

filtered_data = metadata_creation.find_best_time(loaded_data,
                                val_id = val_id)

final_df = metadata_creation.merge_dict(filtered_data,
                variables=metadata_creation.PARAMETERS,
                thresh = 5)


#choosing a collection of bad sensors.
cols_to_keep = ['time',
                'LTD_8901_pm25',
                'LTD_11636_pm25',
                'UTR_bu006_pm25',
                'AMF_pm012_pm25',
                'LTD_34716_pm25',
                'LTD_6874_pm25',
                'LTD_34054_pm25',
                'NBI_352753090556927_pm25',
                'USP_pu519_pm25',
                'LTD_10414_pm25']


std_multiplier = 100000
latent_dimension = 5
lcs_stations = final_df['Netherlands'][[item for item in final_df['Netherlands'].columns if 'VAL_PRE' not in item]]
reference_stations = final_df['Netherlands'][[col for col in final_df['Netherlands'] if 'VAL_PRE' in col or 'time' in col]]
lcs_selected = lcs_stations[cols_to_keep]
# lcs_selected = metadata_creation.select_best_columns(metadata_creation.fill_continuous_timestamps(lcs_stations), limit_columns=16)
# drop_cols = [item for item in lcs_stations.columns if 'VAL_PRE' in item]
full_lcs = lcs_selected.dropna(thresh=(latent_dimension+1))

# full_lcs = lcs_selected.dropna(thresh=(latent_dimension+1))
full_lcs_notime = full_lcs.drop(columns='time')



total_mean = full_lcs_notime.mean().mean()
total_std = full_lcs_notime.mean().std()
spike_thresh = total_mean + std_multiplier*total_std
full_lcs_filter_notime = metadata_creation.mask_extended_zeros(full_lcs_notime.where((full_lcs_notime<spike_thresh), other=pd.NA), consecutive_limit=480)

full_lcs_filter = full_lcs.copy(deep=True)
full_lcs_filter.iloc[:,1:] = full_lcs_filter_notime.copy()

write_csv_file(utrecht_path_lcs,full_lcs_filter)
write_csv_file(utrecht_path_reference, reference_stations)


end = time.time()
print(f"Completed EU data.\nExecution time: {int((end - start)/60)} minutes")