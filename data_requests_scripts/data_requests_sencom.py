import os
import psutil
import shutil
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

import json
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, shape
from shapely.ops import unary_union
import numpy as np

from dateutil import parser

import zipfile

specify_years = ["2024", "2025"] #specify the years you want. otherwise 

'''

Not updated - feel free to use it but don't rely on it being 100% up to date.

Make sure to keep the paths in mind and change them accordingly 
'''

def unzip_and_remove(zip_path):
    """
    Unzip a file in its current directory and remove the zip file after extraction.
    
    Args:
        zip_path (str): Full path to the zip file
    """
    # Get the directory of the zip file
    extract_dir = os.path.dirname(zip_path)
    
    try:
        # Open and extract the zip file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Remove the zip file after successful extraction
        os.remove(zip_path)
        # print(f"Successfully extracted and deleted: {zip_path}")
    
    except zipfile.BadZipFile:
        print(f"Error: {zip_path} is not a valid zip file.")
    except PermissionError:
        print(f"Permission denied: Could not delete {zip_path}")
    except Exception as e:
        print(f"An error occurred: {e}")


#Make sure to put appropriate headers - i removed mine to avoid doxxing :) you can also remove the headers altogether
headers={}

timeout = 60
target_directory='/home/ssda/new_data/sencom/'

root_link = 'http://archive.sensor.community/csv_per_month/'
response = requests.get(root_link, headers = headers, timeout = timeout)
soup = BeautifulSoup(response.text, 'html.parser')
links = [link.get('href', '') for link in soup.find_all('a')][5:-1]

# the links are available in a .txt file as well
all_links = []
for link in links:
    dir_link = os.path.join(root_link,link)
    response = requests.get(dir_link, headers = headers, timeout = timeout)
    soup = BeautifulSoup(response.text, 'html.parser')
    # nest_links = [nest_link.get('href', '') for nest_link in soup.find_all('a')][5:]
    
    all_links.extend([os.path.join(dir_link, nest_link.get('href', '')) for nest_link in soup.find_all('a')][5:])

# with open('./utils/sencom_links.txt', 'w') as f:
#     for line in all_links:
#         f.write(f"{line}\n")
'''
EXTREMELY IMPORTANT:

THE DATASET IS VERY LARGE, MORE THAN 1 TB, BE AWARE.
'''

failed = []
for link in all_links:
    if not any(year in link for year in specify_years) and specify_years:
        continue
    final_dir = os.path.join(target_directory,link.split('csv_per_month/')[1])

    try:
        response = requests.get(link, headers = headers, timeout = timeout)
    except:
        failed.append(link)
        print(f'failed at: {link}')
        continue
    os.makedirs(os.path.join(target_directory,link.split('csv_per_month/')[1].split('/')[0]), exist_ok=True)
    
    with open(final_dir, 'wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)
    unzip_and_remove(final_dir)
    # print(final_dir)
    
while(failed != []):
    link = failed[0]
    final_dir = os.path.join(target_directory,link.split('csv_per_month/')[1])
    try:
        response = requests.get(link, headers = headers, timeout = timeout)
        os.makedirs(os.path.join(target_directory,link.split('csv_per_month/')[1].split('/')[0]), exist_ok=True)
        
        with open(final_dir, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        unzip_and_remove(final_dir)
        # print(final_dir)
        failed.remove(failed[0])
    except:
        continue
'''
The followin gcode is to process it - a single csv file could be up to 11gb alone so it is goign to be extremely slow
the processing includes removing data poin that are outside of NL, BL, and DE. You can edit this below in the' EU_GEOJSON' portion of the code to keep the EU countries that you are seeking.
This is mainly to reduce data size since 2 TB of data is excessive.

It will be split on multiple sections - make sure to not run it all on one go as it might crash if you do no have sufficient ram (64 GB at least).
'''
        
'''

Phase 1 - Split based on region (choice here is Netherlands, Germany, and Belgium)
'''

# Load the GeoJSON file (ensure this path is correct)
with open('./utils/europe.geojson', 'r') as f:
    EU_GEOJSON = json.load(f)
EU_GEOJSON['features'] = [
    feature for feature in EU_GEOJSON['features'] 
    if feature['properties'].get('NAME') == 'Netherlands' or feature['properties'].get('NAME') == 'Germany' or feature['properties'].get('NAME') == 'Belgium'
]

def load_country_boundaries(eu_geojson):
    """
    Extract country boundaries from the EU_GEOJSON feature collection with a 1000m buffer.
    
    Args:
    eu_geojson (dict): Feature collection containing country geometries
    
    Returns:
    GeoDataFrame with buffered country geometries
    """
    # Filter for specific countries
    target_countries = ['Germany', 'Netherlands', 'Belgium']
    
    # Create a list to store country geometries
    country_features = []
    
    # Extract relevant country features
    for feature in eu_geojson['features']:
        if feature['properties']['NAME'] in target_countries:
            country_features.append(feature)
    
    # Create a new feature collection with filtered countries
    filtered_geojson = {
        'type': 'FeatureCollection',
        'features': country_features
    }
    
    # Convert to GeoDataFrame
    gdf = gpd.GeoDataFrame.from_features(filtered_geojson, crs="EPSG:4326")
    
    # Reproject to a projected CRS that uses meters for accurate buffering
    gdf_projected = gdf.to_crs("EPSG:3857")  # Web Mercator projection
    
    # Buffer the geometries by 1000 meters
    gdf_projected['geometry'] = gdf_projected['geometry'].buffer(1000)
    
    # Reproject back to WGS84
    return gdf_projected.to_crs("EPSG:4326")

def process_csv_files(input_dir, output_dir, eu_geojson):
    """
    Process CSV files in the input directory, filtering for specified countries with border buffer.
    
    Args:
    input_dir (str): Directory containing input CSV files
    output_dir (str): Directory to store filtered CSV files
    eu_geojson (dict): Feature collection of countries
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Load country boundaries with 1000m buffer
    country_boundaries = load_country_boundaries(eu_geojson)
    done_files = os.listdir('/home/ssda/new_data/sencom2')
    # Iterate through all files in the input directory
    for root, _, files in os.walk(input_dir):
        print('now in directory: ' ,root)
        for filename in files:
            if filename in done_files:
                  continue
            
            if filename.lower().endswith('.csv'):
                # Construct full file paths
                input_file_path = os.path.join(root, filename)
                output_file_path = os.path.join(output_dir, filename)
                
                # Process the file
                try:
                    # Read CSV in chunks to manage memory
                    chunk_size = 5000000  # Adjust based on your system's memory
                    chunks_filtered = []
                    
                    for chunk in pd.read_csv(input_file_path, 
                                             sep=';', 
                                             chunksize=chunk_size, 
                                             low_memory=False):
                        # Convert chunk to numeric for lat and lon to handle potential string issues
                        chunk['lat'] = pd.to_numeric(chunk['lat'], errors='coerce')
                        chunk['lon'] = pd.to_numeric(chunk['lon'], errors='coerce')
                        
                        # Drop rows with invalid coordinates
                        chunk = chunk.dropna(subset=['lat', 'lon'])
                        
                        # Create a GeoDataFrame from the chunk
                        geo_chunk = gpd.GeoDataFrame(
                            chunk, 
                            geometry=[Point(xy) for xy in zip(chunk['lon'], chunk['lat'])],
                            crs="EPSG:4326"
                        )
                        
                        # Perform spatial join to filter countries with buffer
                        filtered_chunk = gpd.sjoin(
                            geo_chunk, 
                            country_boundaries, 
                            how='inner', 
                            predicate='within'
                        )
                        
                        # Get original columns, excluding geometry and additional columns
                        original_columns = list(chunk.columns)
                        
                        # Drop the geometry column and any additional columns
                        filtered_chunk = filtered_chunk[original_columns]
                        
                        chunks_filtered.append(filtered_chunk)
                    
                    # Combine filtered chunks
                    if chunks_filtered:
                        result = pd.concat(chunks_filtered, ignore_index=True)
                        
                        # Save filtered data
                        if not result.empty:
                            result.to_csv(output_file_path, sep=';', index=False)
                            print(f"Processed: {filename}")
                            print(f"Rows in filtered file: {len(result)}")
                    
                except Exception as e:
                    print(f"Error processing {filename}: {e}")


input_directory = "/home/ssda/new_data/sencom"
output_directory = "/home/ssda/new_data/sencom2"

process_csv_files(input_directory, output_directory, EU_GEOJSON)


'''

Phase 2 - Aggregate to hourly values
'''

def safe_to_numeric(series):
    try:
        # Convert to string and take first 7 characters
        numeric_str = series.astype(str).str[:7]
        
        # Convert to numeric, coercing errors
        return pd.to_numeric(numeric_str, errors='coerce')
    except:
        return series
    
# def parse_timestamps(df, column):
#     # Try parsing with the primary format first
#     try:
#         return pd.to_datetime(df[column])
#     except ValueError:
#         # If that fails, use a more flexible but slightly slower method only for problematic rows
#         mask = df[column].str.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+?00:00?$')

#         df = df[mask]
#         # Fast path for most rows
#         return pd.to_datetime(df[column])
        

def standardize_timestamps(df):
    # Convert to datetime with flexible parsing, ensuring UTC
    df = pd.to_datetime(df, 
                                 format='mixed', 
                                 utc=True)
    
    # Vectorized string formatting - much faster than apply
    df = df.dt.strftime('%Y-%m-%dT%H:%M:%S')
    
    return df

        
def aggregate_to_hourly(df_path, final_path, return_df = False):

    df = pd.read_csv(df_path, delimiter=';',low_memory=False)
    df['timestamp'] = pd.to_datetime(standardize_timestamps(df['timestamp']))
    na_percentages = df.isna().mean()

# Identify columns to drop# Drop the identified columns
    df = df.drop(columns=na_percentages[na_percentages > 0.7].index).dropna()

    
    
# Create an hourly timestamp column (ceiling to the end of the hour)
    df['hour_timestamp'] = df['timestamp'].dt.ceil('h')

    # Prepare aggregation dictionary
    agg_dict = {}

    # Function to safely convert to numeric, taking first 7 characters
    

    # Determine column types and aggregation methods
    for col in df.columns:
        if col in ['sensor_id', 'timestamp', 'hour_timestamp','sensor_type']:
            continue
        
        try:
            # Attempt numeric conversion
            converted = safe_to_numeric(df[col])
            
            # If conversion successful and numeric
            if pd.api.types.is_numeric_dtype(converted):
                df[col] = converted
                agg_dict[col] = 'mean'
            else:
                # Use mode for non-numeric columns
                agg_dict[col] = lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else x.iloc[0]
        except:
            # Fallback to mode for problematic columns
            agg_dict[col] = lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else x.iloc[0]

    # Add reading count
    agg_dict['sensor_id'] = 'count'

    # Aggregate
    aggregated_df = df.groupby(['sensor_id', 'hour_timestamp']).agg(agg_dict)

    # Rename count column
    aggregated_df = aggregated_df.rename(columns={'sensor_id': 'readings_count'}).drop(columns=['readings_count'])
    

    if 'sensor_type' in aggregated_df.columns:
        aggregated_df = aggregated_df.drop(columns=['sensor_type'])
    # Reset index to make columns accessible
    aggregated_df = aggregated_df.reset_index()
    aggregated_df = aggregated_df.rename(columns={'hour_timestamp': 'timestamp'})
    if return_df:
        return aggregated_df
    else:
        aggregated_df.to_csv(final_path, sep=';', index=False)
        return None
    

large_files=[]
inputs_path = '/home/ssda/new_data/sencom2'
final_path = '/home/ssda/new_data/sencom_hourly'
os.makedirs(final_path,exist_ok=True)
done_files = os.listdir(final_path)

for filename in os.listdir(inputs_path):

    if filename in done_files and os.path.getsize(os.path.join(inputs_path,filename)) > 1000:
        continue
    if 'lock' in filename:
        continue
    if os.path.getsize(os.path.join(inputs_path,filename))/(1000**2) > 7000:
        large_files.append(os.path.join(inputs_path,filename))
        print(f'large file, ignoring {filename}')
        continue    
    print(f'now in file: {filename}')
    csv_path = os.path.join(inputs_path,filename)
    final_csv_path = os.path.join(final_path,filename)
    print(psutil.virtual_memory().available/1024**2,psutil.virtual_memory().used/1024**2)
    
    aggregate_to_hourly(csv_path, final_csv_path, False)
    



'''

Phase 3 - Split based on id 
'''

root = '/home/ssda/new_data/sencom_hourly/'
new_path = '/home/ssda/new_data/sencom_id/'
for filename in os.listdir(root):
        # Check if the file is a CSV
    if filename.endswith('.csv'):
        # Extract the unique identifier (assuming format: YYYY-MM_identifier.csv)
        try:
            identifier = filename.split('_')[1].split('.')[0]
        except IndexError:
            print(f"Skipping file {filename}: Unable to extract identifier")
            continue
        
        # Create destination directory for the identifier if it doesn't exist
        identifier_path = os.path.join(new_path, identifier)
        os.makedirs(identifier_path, exist_ok=True)
        
        # Full paths for source and destination
        source_file = os.path.join(root, filename)
        destination_file = os.path.join(identifier_path, filename)
        print(source_file,destination_file)
        # # Move the file
        try:

            shutil.copy(source_file, destination_file)
            # shutil.move(source_file, destination_file)
            print(f"Moved {filename} to {identifier_path}")
        except Exception as e:
            print(f"Error moving {filename}: {e}")


'''

Phase 4 - create directories based on sensor ids and names
'''


root = '/home/ssda/new_data/sencom_id/'
new_root = '/home/ssda/new_data/sencom_root'

sensor_file_counters = {}

# Iterate through sensor name folders
for sens_name in os.listdir(root):
    sens_folder_path = os.path.join(root, sens_name)
    
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
                sensor_id_dir = os.path.join(new_root, sensor_id_str)
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
                
                print(f"Created: {output_path}")
        
        except Exception as e:
            print(f"Error processing {sens_file}: {e}")



'''

Phase 5 - final splitting and creation of json metadata 
'''


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
input_root = '/home/ssda/new_data/sencom_root'
output_root = '/home/ssda/new_data/sencom_final_root'

# Ensure the output root directory exists
os.makedirs(output_root, exist_ok=True)

# Iterate through sensor ID folders
for sensor_id in os.listdir(input_root):
    
    sensor_id_path = os.path.join(input_root, sensor_id)
    
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
        output_sensor_dir = os.path.join(output_root, sensor_id)
        os.makedirs(output_sensor_dir, exist_ok=True)
        
        # Create output filename
        output_filename = f"{sensor_id}.csv"
        output_path = os.path.join(output_sensor_dir, output_filename)
        combined_df = combined_df.rename(columns={'timestamp':'time'})
        # Save the combined CSV
        combined_df.to_csv(output_path, index=False)
        
        print(f"Combined CSV created: {output_path}")


root = '/home/ssda/new_data/sencom_final_root/'

for station in os.listdir(root):
    print(f'now in station: {station}')
    station_path, json_path, csv_path = create_paths(station,root)
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
                'start_time': df['time'].iloc[0],
                'end_time': df['time'].iloc[-1],
                'datastreams_links': 'https://archive.sensor.community/'
                
    }
    write_json_file(json_path,json_data)

    del df

'''
Phase 6 (optional - afterthought) - renaming for uniqueness by adding 'sencom' at start
'''

stations = os.listdir(root)
for station in stations:
    station_path, json_path, csv_path = create_paths(station,root)
    new_station_path = os.path.join(root,f'sencom_{station}')
    new_csv_path = os.path.join(station_path,f'sencom_{station}.csv')
    new_json_path = os.path.join(station_path,f'sencom_{station}.json')
    os.rename(csv_path,new_csv_path)
    os.rename(json_path,new_json_path)
    os.rename(station_path,new_station_path)
    


'''
do NOT run this code, it is fxied, but i just added it because i made the mistake of forgetting to change 'timestamp' to' time' alone so it matches other data :)
purely for documentation purposes
'''

# import pandas as pd
# import os
# from pathlib import Path
# import multiprocessing as mp
# from functools import partial

# def process_file(filepath):
#     """Process a single CSV file to rename the 'timestamp' column to 'time'."""
#     try:
#         # Read only the header first to check if 'timestamp' exists
#         header = pd.read_csv(filepath, nrows=0)
#         if 'timestamp' not in header.columns:
#             print(f"Warning: 'timestamp' column not found in {filepath}")
#             return False
        
#         # Read the CSV file
#         df = pd.read_csv(filepath)
        
#         # Rename the column
#         df = df.rename(columns={'timestamp': 'time'})
        
#         # Save back to the same file
#         df.to_csv(filepath, index=False)
#         print(f"Successfully processed {filepath}")
#         return True
        
#     except Exception as e:
#         print(f"Error processing {filepath}: {str(e)}")
#         return False

# def main():
#     # Get the root directory
#     root_dir = '/home/ssda/new_data/sencom_final_root'
    
#     # Find all CSV files that match the folder name pattern
#     csv_files = []
#     for folder in os.listdir(root_dir):
#         folder_path = Path(root_dir) / folder
#         if folder_path.is_dir():
#             csv_file = folder_path / f"{folder}.csv"
#             if csv_file.exists():
#                 csv_files.append(str(csv_file))
    
#     # Use multiprocessing to process files in parallel
#     with mp.Pool(processes=mp.cpu_count()) as pool:
#         results = pool.map(process_file, csv_files)
    
#     # Print summary
#     successful = sum(results)
#     total = len(csv_files)
#     print(f"\nProcessing complete!")
#     print(f"Successfully processed {successful} out of {total} files")

# if __name__ == "__main__":
#     main()


# import pandas as pd
# import os
# from pathlib import Path
# import multiprocessing as mp
# from datetime import datetime
# import pytz

# def convert_to_epoch(filepath):
#     """Convert 'time' column from UTC datetime to epoch time for a single CSV file."""
#     try:
#         # Read the CSV file
#         df = pd.read_csv(filepath)
        
#         if 'time' not in df.columns:
#             print(f"Warning: 'time' column not found in {filepath}")
#             return False
        
#         # Convert time string to datetime and then to epoch
#         df['time'] = pd.to_datetime(df['time'])
#         df['time'] = df['time'].apply(lambda x: int(x.timestamp()))
        
#         # Save back to the same file
#         df.to_csv(filepath, index=False)
#         # print(f"Successfully processed {filepath}")
#         return True
        
#     except Exception as e:
#         print(f"Error processing {filepath}: {str(e)}")
#         return False

# def main():
#     # Get the root directory
#     root_dir = '/home/ssda/new_data/sencom_final_root'
    
#     # Find all CSV files that match the folder name pattern
#     csv_files = []
#     for folder in os.listdir(root_dir):
#         folder_path = Path(root_dir) / folder
#         if folder_path.is_dir():
#             csv_file = folder_path / f"{folder}.csv"
#             if csv_file.exists():
#                 csv_files.append(str(csv_file))
    
#     # Use multiprocessing to process files in parallel
#     with mp.Pool(processes=mp.cpu_count()) as pool:
#         results = pool.map(convert_to_epoch, csv_files)
    
#     # Print summary
#     successful = sum(results)
#     total = len(csv_files)
#     print(f"\nProcessing complete!")
#     print(f"Successfully processed {successful} out of {total} files")

# if __name__ == "__main__":
#     main()