'''
This file contains extra code that is a one time use, not necessary


'''
######################

'''
Combine everything in one main root folder, and make sure all names are similar (e.g. capitlization)
define the root:
'''


source_root = '/dum/dum/preprocessed_root'
target_root = '/dum/dum/final_root'



import os
import json
import shutil
import pandas as pd
from pathlib import Path

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

# Variable mapping dictionary
variable_mapping = {
    'PM10': 'pm10',
    'P1': 'pm10',
    'P2': 'pm25',
    'PM2.5': 'pm25',
    'NO2': 'no2',
    'NO': 'no2',
    'humidity': 'rh',
    'U': 'rh',
    'temperature': 'temp',
    'T': 'temp'
}

# Process the directory structure
process_directory(source_root, target_root, variable_mapping)
print("Processing completed successfully!")

#############################