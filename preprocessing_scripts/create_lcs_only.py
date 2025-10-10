


from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

import os
import json
import pandas as pd
from shapely.geometry import Point, shape
from utils.geoutils import *
import numpy as np
from itertools import combinations
import geopandas as gpd
import numpy as np
from shapely.geometry import Point, MultiPolygon
from pyproj import Transformer
import math
from scipy import stats
import geopandas as gpd
import numpy as np
from shapely.geometry import Point, MultiPolygon
from pyproj import Transformer
import math

import re
import os
import pandas as pd
import json
import warnings

import geopandas as gpd
from shapely.geometry import Point
import shutil


import seaborn as sns
import matplotlib.pyplot as plt


import math
from geopy.distance import geodesic


PARAMETERS = ['pm25']



NL_ONLY = True
PARAMETERS = ['pm25']
# val_id = 'VAL_PRE'
VARIABLES_OF_INTEREST = ['num_of_rows','period','available_streams']
ROOT = None


def no_alignment_dataloader(searcher_output,
               keep_columns = ['time','temp','rh','pm25','pm10'],
               regions = 'all',
               must_columns = [],
               remove_empty_df = True):

# Input validation
    if not isinstance(searcher_output, dict):
        raise ValueError("searcher_output must be a dictionary")
        
    # Process regions parameter
    if regions == 'all':
        selected_regions = list(searcher_output.keys())
    elif isinstance(regions, str):
        selected_regions = [regions]
    elif isinstance(regions, list):
        selected_regions = regions
    else:
        raise ValueError("regions must be 'all', a string, or a list of strings")

    # Filter out invalid regions and warn user
    valid_regions = [r for r in selected_regions if r in searcher_output]
    if len(valid_regions) < len(selected_regions):
        invalid_regions = set(selected_regions) - set(valid_regions)
        warnings.warn(f"Skipping invalid regions: {invalid_regions}")

    # Initialize result container based on return type
    result = {region: {} for region in valid_regions}

    for region in valid_regions:
        station_ids = searcher_output[region]
        
        for station_id in station_ids:
            # Construct file paths
            station_path = os.path.join(ROOT, station_id)
            csv_path = os.path.join(station_path, f"{station_id}.csv")
            # json_path = os.path.join(station_path, f"{station_id}.json")
            
            # Check if files exist
            if not (os.path.exists(csv_path)):
                warnings.warn(f"Missing files for station {station_id}")
                continue
                
            # Read data
            df = pd.read_csv(csv_path)
            
            # Filter columns if specified
            if keep_columns:
                available_cols = [col for col in keep_columns if col in df.columns]
                if not available_cols:
                    warnings.warn(f"No requested columns found in {station_id}")
                    continue
                df = df[available_cols]
            
            if remove_empty_df:
                if df.empty:
                    continue
            if must_columns != []:
                if not set(must_columns).issubset(df.columns):
                    continue
            result[region][station_id] = df

    return result

def filter_unique_coordinates(unique_coords, used_coords, distance_threshold=5):
    """
    Filter coordinates that are not within the specified distance of any used coordinate.
    
    Parameters:
    - unique_coords: List of [lon, lat] coordinates to filter
    - used_coords: List of [lon, lat] coordinates to compare against
    - distance_threshold: Minimum distance in kilometers (default 5km)
    
    Returns:
    - List of coordinates from unique_coords that are not within the distance threshold
    """

    print(f'ROOT is at: {ROOT}')
    unique_coords_new = []
    
    for coord in unique_coords:
        # Assume the coordinate is safe to add initially
        is_within_threshold = False
        
        # Check against each used coordinate
        for used_coord in used_coords:
            # Calculate distance between the current coordinate and used coordinate
            distance = geodesic(coord[::-1], used_coord[::-1]).kilometers
            
            # If distance is less than threshold, mark as not unique
            if distance <= distance_threshold:
                is_within_threshold = True
                break
        
        # Add to new list only if not within threshold of any used coordinate
        if not is_within_threshold:
            unique_coords_new.append(coord)
    
    return unique_coords_new
def merge_sensor_dataframes(data_dict, discard_specific_ids=False):
    """
    Merge dataframes from a dictionary of sensor dataframes.
    
    Parameters:
    -----------
    data_dict : dict
        Dictionary with sensor IDs as keys and dataframes as values
    discard_specific_ids : bool, optional
        If True, discard dataframes with IDs matching NLXXXXX_PRE or NLXXXXX_VAL_PRE patterns
    
    Returns:
    --------
    pd.DataFrame
        Merged dataframe with time column and pm25 values for each sensor
    """
    # Filter out specific dataframes if discard_specific_ids is True
    if discard_specific_ids:
        # Regex pattern to match NLXXXXX_PRE or NLXXXXX_VAL_PRE
        pattern = re.compile(r'^NL\d{5}_(VAL_)?PRE$')
        filtered_dict = {k: v for k, v in data_dict.items() if not pattern.match(k)}
    else:
        filtered_dict = data_dict
    
    # Prepare a list to store dataframes with time column and pm25 as column
    pm25_dfs = []
    
    for sensor_id, df in filtered_dict.items():
        # Create a new dataframe with time and pm25 columns
        temp_df = df[['time', 'pm25']].copy()
        temp_df = temp_df.rename(columns={'pm25': sensor_id})
        pm25_dfs.append(temp_df)
    
    # Merge all dataframes using outer join
    merged_df = pd.concat(pm25_dfs, axis=0, ignore_index=False)
    
    # Group by time and aggregate columns
    merged_df = merged_df.groupby('time', as_index=False).first()
    
    # Sort by time
    merged_df = merged_df.sort_values('time')
    
    return merged_df

def filter_half_na_rows(df, time_column='time'):

    non_time_columns = [col for col in df.columns if col != time_column]
    
    total_non_time_columns = len(non_time_columns)
    
    na_threshold = math.ceil(total_non_time_columns / 2)
    
    filtered_df = df[df[non_time_columns].isna().sum(axis=1) <= na_threshold].copy()
    
    return filtered_df


def get_location_name(coordinates):
    """
    Get the locality name for given coordinates in the Netherlands.
    
    Args:
        coordinates (list): A list of [longitude, latitude]
    
    Returns:
        str: Name of the locality or nearest administrative area
    """
    # Validate input
    if not isinstance(coordinates, list) or len(coordinates) != 2:
        raise ValueError("Coordinates must be a list of [longitude, latitude]")
    
    lon, lat = coordinates
    
    # Initialize Nominatim geocoder
    geolocator = Nominatim(user_agent="netherlands_location_finder")
    
    try:
        # Reverse geocode the coordinates
        location = geolocator.reverse(f"{lat}, {lon}", language='en')
        
        if location:
            # Extract relevant location information
            address = location.raw.get('address', {})
            
            # Priority order for location names
            location_priorities = [
                address.get('city'),
                address.get('town'),
                address.get('village'),
                address.get('municipality'),
                address.get('county'),
                address.get('state'),
                'Unknown Location'
            ]
            
            # Return the first non-None location name
            for loc in location_priorities:
                if loc:
                    return loc
            
            return 'Unknown Location'
        
        return 'No location found'
    
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f'Geocoding error: {str(e)}')
        return None