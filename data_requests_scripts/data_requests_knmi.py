'''
Code to pull data from knmi 'https://www.daggegevens.knmi.nl/klimatologie/uurgegevens'
Not updated - feel free to use it but don't rely on it being 100% up to date.

Define the root:
'''
ROOT = '/dum/dum/dum'

starting_time = 1970 #this is where epoch time start, you can change it
end_time = 2025

import os
import glob

import json
import csv
import re
from datetime import datetime, timezone
import requests

import pandas as pd

def concat_csvs(path, delete_files=True):

    # Save the combined file
    if path[-1] == '/':
        path = path[:-1]
    stn_name = path.split('/')[-1]
    output_file = os.path.join(path,f'{stn_name}.csv')

    csv_files = glob.glob(os.path.join(path,f'{stn_name}_*.csv'))
    if csv_files == []:
        print('There are no csvs here - skipping')
        return None
    dfs = []

    # Print the files being processed
    for file in sorted(csv_files):
        df = pd.read_csv(file)
        dfs.append(df)

    combined_df = pd.concat(dfs, ignore_index=True)


    combined_df.to_csv(output_file, index=False)
    if delete_files:
        [os.remove(file) for file in csv_files]

def fetch_knmi_hourly_data(stns, ymdh_start, ymdh_end):
    """
    Fetch hourly meteorological data from KNMI
    
    Parameters:
    - stns: Station numbers (as a string)
    - ymdh_start: Start date and time (format: YYYYMMDDHH)
    - ymdh_end: End date and time (format: YYYYMMDDHH)
    
    Returns:
    - Response from KNMI API
    """
    url = 'https://www.daggegevens.knmi.nl/klimatologie/uurgegevens'
    
    payload = {
        'stns': stns,
        'start': ymdh_start,
        'end': ymdh_end,
        'vars': 'DD:FH:FF:FX:T:T10N:TD:SQ:Q:DR:RH:P:VV:N:U:WW:IX:M:R:S:O:Y:'
    }
    
    try:
        # Verify=False is equivalent to --no-check-certificate in wget
        response = requests.post(url, data=payload, verify=False)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching KNMI data: {e}")
        return None
    
def parse_variable_descriptions(metadata_line):
    """
    Parse variable descriptions from the metadata line
    """
    # Remove the initial '# ' and split by '#'
    parts = metadata_line.lstrip('# ').split('#')
    
    # Dictionary to store variable descriptions
    descriptions = {}
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # Use regex to split variable from description
        match = re.match(r'^(\w+)\s*:\s*(.+)$', part)
        if match:
            variable = match.group(1)
            description = match.group(2)
            descriptions[variable] = description
    
    return descriptions

def process_knmi_data(data_string,year=None):
    # Split the data into lines
    lines = data_string.strip().split('\n')
    
    # Extract metadata from the header
    station_number = None
    variable_descriptions = parse_variable_descriptions(data_string)
    # Rest of the function remains similar to previous implementation
    metadata = {
        'variables': variable_descriptions
    }
    
    # Find the station metadata line
    for line in lines:
        if line.startswith('# ') and not line.startswith('# SOURCE:') and not line.startswith('# Comment:'):
            parts = line.split()
            if len(parts) >= 5 and parts[1].isdigit():
                metadata.update({
                    'type': 'knmi',
                    'longitude': float(parts[2]),
                    'latitude': float(parts[3]),
                    'altitude': float(parts[4]),
                    'datastream_link': 'https://www.daggegevens.knmi.nl/klimatologie/uurgegevens',
                    'location': ' '.join(parts[5:]) if len(parts) > 5 else ''
                })
                station_number = parts[1]
                break
    
    if not station_number:
        raise ValueError("Could not find station number in the data")
    
    # Find the data start point using the header line
    data_start = next((i for i, line in enumerate(lines) if line.startswith('# STN,YYYYMMDD')), None)
    data_lines = lines[data_start+1:]
    
    # Prepare output directory
    folder_name = f'KNMI_{station_number}'
    output_dir = os.path.join(f'{ROOT}/KNMI', folder_name)
    os.makedirs(output_dir, exist_ok=True)
    
    # Write metadata JSON with folder name as filename
    metadata_path = os.path.join(output_dir, f'{folder_name}.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Prepare and write CSV with folder name as filename
    if year == None:
        csv_path = os.path.join(output_dir, f'{folder_name}.csv')

    else:
        csv_path = os.path.join(output_dir, f'{folder_name}_{year}.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(['time'] + [component.split(' ')[-1] for component in lines[data_start].split(',')[3:]])
        
        # Process data rows
        for line in data_lines:
            # Strip whitespace and skip empty lines
            line = line.strip()
            if not line:
                continue
            
            parts = [p.strip() for p in line.split(',')]
            
            # Convert date and time to epoch
            date_str = parts[1]
            hour_str = parts[2]
            
            # Remove any extra spaces and ensure correct format
            date_str = date_str.replace(' ', '')
            hour_str = hour_str.replace(' ', '')
            
            # Shift hour: 1-24 to 00-23
            hour = int(hour_str)
            hour = hour - 1 if hour > 0 else 0
            hour_str = f'{hour:02d}'
            
            utc_time = datetime.strptime(f'{date_str} {hour_str}', '%Y%m%d %H').replace(tzinfo=timezone.utc)
            epoch = int(utc_time.timestamp())
            # epoch = int(datetime.strptime(f'{date_str} {hour_str}', '%Y%m%d %H').timestamp())
            
            # Write row without STN, with epoch time
            writer.writerow(
                [epoch] + parts[3:]
            )
    
    print(f"Processed data in {output_dir}")
    return output_dir


stations_list = [209, 210, 215, 225, 235, 240, 242, 248, 249, 251, 257, 258, 260, 265, 267, 269, 270, 273, 275, 277, 278, 279, 280, 283, 285, 286, 290, 308, 310, 311, 312, 313, 315, 316, 319, 323, 324, 330, 331, 340, 343, 344, 348, 350, 356, 370, 375, 377, 380, 391]


for stns in stations_list:
    for i in range((end_time-starting_time)):
        
        ymdh_start = f'{starting_time+i}010100'  
        ymdh_end = f'{starting_time+i}123123'

        data = fetch_knmi_hourly_data(stns, ymdh_start, ymdh_end)

        lines = data.strip().split('\n')
        header_index = next((i for i, line in enumerate(lines) if line.startswith('# STN,YYYYMMDD')), None)

# 2. Check if header was found AND if there is actual data after it
        if header_index is None or lines[header_index+1:] == []:
            # Skip if no header found or if the list is empty after the header
            pass # or continue if this is inside a loop
        else:
            output_dir = process_knmi_data(data, year=starting_time+i)
    
    concat_csvs(output_dir)


'''
Forgot to do it in the original code so here it is separately :)

'''
    
cor_units = {    'FH': 0.1,
    'FF': 0.1,
    'FX': 0.1,
    'T':0.1,
    'T10N': 0.1,
    'TD': 0.1,
    'SQ': 0.1,
    'DR': 0.1,
    'RH': 0.1,
    'P': 0.1
}
base_dir = f'{ROOT}/KNMI/'


# Loop through all folders in the directory
for folder_name in os.listdir(base_dir):
    folder_path = os.path.join(base_dir, folder_name)
    
    # Check if it's a directory
    if os.path.isdir(folder_path):
        # Construct the CSV file path (assuming CSV name matches folder name)
        csv_path = os.path.join(folder_path, f"{folder_name}.csv")
        
        # Check if CSV exists
        if os.path.exists(csv_path):
            # Read the CSV
            df = pd.read_csv(csv_path)
            
            # Correct columns specified in cor_units
            for column, factor in cor_units.items():
                if column in df.columns:
                    # Divide the column by the factor
                    # Use .loc to modify in-place and handle potential non-numeric values
                    df.loc[:, column] = pd.to_numeric(df[column], errors='coerce') * factor
            
            # Save the modified CSV back to the same location
            df.to_csv(csv_path, index=False)
            print(f"Processed {csv_path}")
