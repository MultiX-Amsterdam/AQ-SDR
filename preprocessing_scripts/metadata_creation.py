'''
Code with helper function to create tensor dataset.
'''

import os
from shapely.geometry import Point
from utils.geoutils import *
from itertools import combinations
import geopandas as gpd
from pyproj import Transformer
import math
from scipy import stats

import pandas as pd
import warnings





from geopy.distance import geodesic


PARAMETERS = ['pm25']
# val_id = 'VAL_PRE'

# one_time_full_metadata()
# create_grid('./utils/NLBLGER_JSON.geojson','/data/env/gridded_1km.json')
# create_grid('./utils/NLBLGER_JSON.geojson','/data/env/gridded_500m.json', spacing_km =0.5)



ROOT = None




gdf = gpd.read_file('./utils/NLBLGER_JSON.geojson')
def locate_country(gdf, longitude, latitude):

    point = Point(longitude, latitude)
    
    for index, row in gdf.iterrows():
        if row.geometry.contains(point):
            return row['NAME'] 
    
    return None
def load_and_separate_polygons(file_path):
    """
    Load GeoJSON file and separate polygons by country name
    """
    # Read GeoJSON file
    gdf = gpd.read_file(file_path)
    
    # Create separate variables for each country
    countries = {}
    for _, row in gdf.iterrows():
        countries[row['NAME']] = row['geometry']
    
    return countries

def create_grid_points(polygon, spacing_km=1):
    """
    Create a grid of points within a polygon with approximately 1km spacing
    
    Args:
        polygon: Shapely MultiPolygon in EPSG:4326
        spacing_km: Desired spacing in kilometers
    
    Returns:
        List of (lon, lat) tuples representing grid points within the polygon
    """
    # Get bounds of the polygon
    minx, miny, maxx, maxy = polygon.bounds
    
    # Create transformer for converting distances
    # UTM zone calculation (approximate)
    utm_zone = math.floor((((minx + maxx) / 2) + 180) / 6) + 1
    epsg_code = 32600 + utm_zone  # Northern hemisphere
    if miny < 0:
        epsg_code += 100  # Southern hemisphere
    
    # Create transformers
    to_utm = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg_code}", always_xy=True)
    to_wgs84 = Transformer.from_crs(f"EPSG:{epsg_code}", "EPSG:4326", always_xy=True)
    
    # Convert bounds to UTM
    utm_minx, utm_miny = to_utm.transform(minx, miny)
    utm_maxx, utm_maxy = to_utm.transform(maxx, maxy)
    
    # Create grid in UTM coordinates
    spacing = spacing_km * 1000  # Convert to meters
    x_coords = np.arange(utm_minx, utm_maxx, spacing)
    y_coords = np.arange(utm_miny, utm_maxy, spacing)
    
    grid_points = []
    
    # Create grid points and filter those within polygon
    for x in x_coords:
        for y in y_coords:
            # Convert back to WGS84
            lon, lat = to_wgs84.transform(x, y)
            point = Point(lon, lat)
            
            if polygon.contains(point):
                grid_points.append((lon, lat))
    
    return grid_points


def create_grid(input_path, output_path, spacing_km=1):
    country_polygons =  load_and_separate_polygons(input_path)

    grid_points = {}
    for country_name, polygon in country_polygons.items():
        grid_points[country_name] = create_grid_points(polygon, spacing_km)
        
    write_json_file(output_path,grid_points)

    return None



def one_time_full_metadata(output):
    print('Operating root at:', ROOT)
    full_metadata = {}
    for idx, station in enumerate(os.listdir(ROOT)):
        full_metadata[station] = {}
        station_path, json_path, csv_path = create_paths(station,ROOT)
        station_json = load_json_file(json_path)
        
        if not os.path.isfile(csv_path):
            period = (0,0)
            num_of_rows = 0
        else:
            df = pd.read_csv(csv_path)
            period = (int(df['time'].iloc[0]),int(df['time'].iloc[-1]))
            num_of_rows = len(df)
        country = locate_country(gdf,station_json['longitude'],station_json['latitude'])
        if country == None:
            country = 'NA'
        full_metadata[station] = {'name': station,
                                  'longitude': station_json['longitude'],
                                  'latitude': station_json['latitude'],
                                  'type': station_json['type'],
                                  'available_streams': list(station_json['available_streams']),
                                  'path': station_path,
                                  'period':period,
                                  'num_of_rows':num_of_rows,
                                  'country': country,
                                  }

    write_json_file(output,full_metadata)
    return None

# def find_folders_in_polygon(json_path,polygon):
    
#     with open(json_path) as f:
#         data = json.load(f)
        
#     point = Point(data['longitude'], data['latitude'])
#     polygon_shape = shape(polygon)
    
#     if polygon_shape.contains(point):
#         return True
    
#     return False

def create_paths(station,root):
    return os.path.join(root,station), os.path.join(root,station,f'{station}.json'), os.path.join(root,station,f'{station}.csv')

def find_closest_points(lon_orig, lat_orig, threshold, crowd_only = False, return_all_sorted = False, return_period = False):


    sorted_to_origin = {}
    for folder in os.listdir(ROOT):
        folder_path = os.path.join(ROOT,folder)
        csv_path = os.path.join(folder_path, folder+'.csv')
        if not os.path.isfile(csv_path):
            continue
        metadata_path = os.path.join(folder_path,folder+'.json')
        metadata = load_json_file(metadata_path)
        if crowd_only and (metadata['type'] == 'official_val' or metadata['type'] == 'knmi'):
            continue
        
        lon, lat = float(metadata['longitude']), float(metadata['latitude'])


        # if dis_to_orig < DIS_THRESHOLD:
        #     within_threshold[folder] = {'type': metadata['type'],
        #                                 'distance_to_origin': dis_to_orig}
        sorted_to_origin[folder] = {'type': metadata['type'],
                                        'distance_to_origin': haversine(lon_orig,lat_orig,lon,lat),
                                        'variables': list(metadata['available_streams'])}
        
    
    sorted_to_origin =  dict(sorted(sorted_to_origin.items(), key= lambda item: item[1]['distance_to_origin']))
    within_threshold = {k: sorted_to_origin[k] for i, k in enumerate(sorted_to_origin) if (sorted_to_origin[k]['distance_to_origin'] < threshold and sorted_to_origin[k]['distance_to_origin']>0)}
    if return_period:
        for item in within_threshold:
            csv_path = os.path.join(ROOT, item, item+'.csv')     
            within_threshold[item]['time'] = list(pd.read_csv(csv_path)['time'].astype(int))
    if return_all_sorted:
        return sorted_to_origin, within_threshold
    
    return within_threshold


def has_overlap(times1, times2):
        return bool(set(times1) & set(times2))

def overlapping_in_time(lists_dict):
    overlapping_groups = []
    processed_keys = set()
    
    for key1 in lists_dict:
        # Skip if this key has already been processed
        if key1 in processed_keys:
            continue
            
        # Start a new group with this key
        current_group = {key1}
        times1 = lists_dict[key1]['time']
        
        for key2 in lists_dict:
            if key2 != key1 and key2 not in processed_keys:
                times2 = lists_dict[key2]['time']
                if has_overlap(times1, times2):
                    current_group.add(key2)
                    
        
            # Add all keys in current group to processed set
        if len(current_group) < 2:
            continue
        processed_keys.update(current_group)
        # Add current group to results
        overlapping_groups.append(list(current_group))
    
    return overlapping_groups



def overlap_combinations(lists, overlaps, full_group = False):
    
    combinations_dict = {}

    # Iterate through each group of overlapping labels
    for group_idx, group in enumerate(overlaps):
        combinations_dict[group_idx] = []
        # Generate all possible combinations of 2 or more labels from the group
        r = 2 
        while(r <=  (len(group))):
            # Get all combinations of size r from the group
            if full_group:
                r = len(group)
            label_combinations = combinations(group, r)
            
            for label_combo in label_combinations:
                # Get time lists for all labels in this combination
                time_sets = [set(lists[label]['time']) for label in label_combo]
                
                # Find common times across all labels in this combination
                common_times = list(set.intersection(*time_sets))
                
                # Only include combinations that have overlapping times
                if common_times:
                    combinations_dict[group_idx].append([
                        list(label_combo),  # Convert tuple to list for better readability
                        sorted(common_times)  # Sort times for consistency
                    ])
                
            r+=1

    return combinations_dict





def group_stations_by_grid(full_metadata, full_grids, radius_m = 2000, same_country_limit = True, store_to_json = None):

    result = {}

    # Initialize result dictionary with countries
    for country in full_grids.keys():
        result[country] = {}

    if same_country_limit:
    # Process each country's grid coordinates
        for country, coordinates in full_grids.items():
            print(f'Starting country: {country}')
            # Process each coordinate in the country
            for i, coord in enumerate(coordinates):

                nearby_stations = []
                
                # Check each station in full_metadata
                for station_id, station_data in full_metadata.items():
                    if station_data['country'] != country:
                        continue
                    # Calculate distance between grid coordinate and station
                    distance = haversine(
                        coord[1], coord[0],  # Grid latitude, longitude
                        float(station_data['latitude']), float(station_data['longitude'])  # Station latitude, longitude
                    )
                    
                    # If station is within radius, add to list
                    if distance <= radius_m:
                        nearby_stations.append(station_id)
                
                # Only add to result if there are nearby stations
                if nearby_stations:
                    result[country][i] = [coord,nearby_stations]
    else:
        for country, coordinates in full_grids.items():
            print(f'Starting country: {country}')
        
        # Process each coordinate in the country
            for i, coord in enumerate(coordinates):
                nearby_stations = []
                
                # Check each station in full_metadata
                for station_id, station_data in full_metadata.items():
                    # Calculate distance between grid coordinate and station
                    distance = haversine(
                        coord[1], coord[0],  # Grid latitude, longitude
                        float(station_data['latitude']), float(station_data['longitude'])  # Station latitude, longitude
                    )
                    
                    # If station is within radius, add to list
                    if distance <= radius_m:
                        nearby_stations.append(station_id)
                
                # Only add to result if there are nearby stations
                if nearby_stations:
                    result[country][i] = [coord,nearby_stations]
    
    if store_to_json != None:
        write_json_file(store_to_json, result)
        return None
    return result

def fetch_to_sort(id, param):
    if type(FULL_METADATA[id][param]):
        return FULL_METADATA[id][param]
    else:
        return [FULL_METADATA[id][param]]

def sort_and_keep_val(data, include = [], val_id = 'VAL_PRE'):
    """
    
    Args:
        data (dict): Input dictionary with country data
        include (list): list of items to include in the information within the list, options:
            - 'available_streams': this will include a list of all available data streams in this station [PM1, PM2 ... etc]
            - 'period': this will include the range of time in epoch time [start_time, end_time]
            - 'num_of_rows': this will include the total number of data points (rows) in the csv files 
    Returns:
        dict: Processed dictionary
    """
    processed_data = {}
    
    for country, locations in data.items():
        # Convert to list of tuples for easier processing
        location_list = []
        for idx, (coords, id_list) in locations.items():
            # Check if list contains any string matching NL*_VAL pattern
            has_val = any(
                isinstance(item, str) and
                item.endswith(val_id)
                for item in id_list
            )
            
            if has_val and include != []:
                new_id_list = []
                for id in id_list:
                    id_param = []
                    for param in sorted(include):
                        id_param.append(fetch_to_sort(id,param))
                    new_id_list.append([id,id_param])
                    
                location_list.append((coords, new_id_list))
            elif has_val:
                location_list.append((coords, id_list))
        
        # Sort by list length in descending order
        location_list.sort(key=lambda x: len(x[1]), reverse=True)
        # return location_list
        
        # Create new dictionary with reindexed entries
        if location_list:  # Only process if there are valid entries
            processed_data[country] = {
                i: list(item) 
                for i, item in enumerate(location_list)
            }
    
    return processed_data

def find_time_range(filtered_stations, 
                    min_start_time=1262304000, 
                    seconds_per_month=2628000, 
                    min_num_stations = 3,
                    val_id = 'VAL_PRE'):

    earliest_start = max(min_start_time, min(station[1][2][0] for station in filtered_stations))
    latest_end = max(station[1][2][1] for station in filtered_stations)

    # 3: Create quantized intervals
    total_interval = latest_end - earliest_start
    N = int(total_interval / seconds_per_month)

    # Calculate step size for intervals
    step = int(total_interval / N if N > 0 else total_interval)

    # Create dictionary with midpoints as keys
    time_dict = {}
    for i in range(N + 1):
        interval_start = earliest_start + (i * step)
        time_dict[interval_start] = []

    # 4: Assign station IDs to appropriate time periods
    for station in filtered_stations:
        station_id = station[0]
        station_start = station[1][2][0]
        station_end = station[1][2][1]
        
        # Check each midpoint
        for midpoint in time_dict.keys():
            # If midpoint falls within station's time period, append station ID
            if station_start <= midpoint <= station_end:
                time_dict[midpoint].append(station_id)


    valid_timestamps = []
    max_timestamp = 0
    max_stations = 0

    # Process each timestamp
    for timestamp, stations in time_dict.items():
        # Add all stations to the total set
        
        # Count valid stations (not starting with 'NL' and ending with '_VAL_PRE')
        valid_count = sum(1 for station in stations 
                            if not (station.endswith(val_id)))
        
        # If we meet the minimum station requirement, add to valid timestamps
        if valid_count >= min_num_stations:
            valid_timestamps.append(timestamp)
            # all_stations.update(stations)
            if len(stations) > max_stations:
                max_timestamp = timestamp 
                max_stations = len(stations)
    if valid_timestamps:
        return [[min(valid_timestamps), max(valid_timestamps)], [max_timestamp, max_stations]]
    else:
        return None   
    # return [[min(valid_timestamps), max(valid_timestamps)], [max_timestamp, max_stations]]

  

def sorted_by_filtered_stations(data_dict, NL_only=False):
    """
    Sort dictionary entries based on number of stations and reindex keys starting from 0.
    This number of stations is the highest number of stations that coincided in a single period of time.
    
    Args:
        data_dict (dict): Input dictionary with country data
        NL_only (bool): If True, keep only Netherlands data
        
    Returns:
        dict: Sorted dictionary with countries and their reindexed station data
    """
    # Create a copy to avoid modifying the original dictionary
    result_dict = {}
    
    # Filter for Netherlands only if specified
    if NL_only:
        if 'Netherlands' in data_dict:
            working_dict = {'Netherlands': data_dict['Netherlands']}
        else:
            return {}
    else:
        working_dict = data_dict.copy()
    
    # Process each country
    for country, stations in working_dict.items():
        # Skip empty country data
        if not stations:
            result_dict[country] = {}
            continue
            
        # Get number of stations for each entry and track original order
        station_data = []
        for key, value in stations.items():
            if value and len(value) > 0:
                # Corrected indexing for num_stations
                num_stations = value[0][1][1]
                # Store tuple of (key, num_stations, original_index)
                station_data.append((key, num_stations, len(station_data)))
        
        # Sort stations by count (descending) and use original index as tiebreaker
        sorted_data = sorted(
            station_data,
            key=lambda x: (x[1], -x[2]),  # Sort by stations first, then by negative index
            reverse=True
        )
        
        # Rebuild the sorted dictionary with new indices starting from 0
        sorted_stations = {}
        for new_index, (old_key, _, _) in enumerate(sorted_data):
            sorted_stations[new_index] = stations[old_key]
            
        result_dict[country] = sorted_stations
    
    return result_dict

def create_time_periods(data_dict, 
                        parameter=PARAMETERS, 
                        min_num_stations = 3, 
                        sort = True, 
                        NL_only = False,
                        val_id = 'VAL_PRE'):
    processed_dict = {}
    parameter = set(parameter)
    for country in data_dict:
        processed_dict[country] = {}
        
        for key, stations_list in data_dict[country].items():
            # Skip if stations_list is empty
            if not stations_list:
                continue
                
            # Extract coordinates
            coordinates = stations_list[0]
            
            # Filter stations that have the parameter
            filtered_stations = []
            
            # Start from index 1 to skip coordinates
            for station in stations_list[1]:
                # Check if station has enough elements (station_id and data list)
                
                if len(station) >= 2 and isinstance(station[1], list):
                    # station_id = station[0]  # This is the station ID string
                    station_data = station[1]
                    if isinstance(station_data[1], int) and station_data[1] < 1:
                        continue
                    # Check if parameters list exists (should be first element in station_data)
                    if len(station_data) >= 1 and isinstance(station_data[0], list):
                        parameters = station_data[0]
                        
                        # Check if parameter exists in the station's parameter list
                        if parameter.issubset(parameters):
                            filtered_stations.append(station)
                if filtered_stations:
                    if any(isinstance(item[0], str) and
                        item[0].endswith(val_id)
                        for item in filtered_stations):
                        
                        time_periods = find_time_range(filtered_stations, min_num_stations = min_num_stations)
                        if time_periods:
                            processed_dict[country][key] = [time_periods, coordinates, filtered_stations]
                    else:
                        continue
    if sort:
        return sorted_by_filtered_stations(processed_dict, NL_only = NL_only)
    else:
        return processed_dict
        # else:
        #     processed_dict[country][key] = []
    

def bring_ids(dict):
    id_only_output = {}
    for country, stations in dict.items():
        id_only_output[country] = [id[0] for id in stations[2]]

    return id_only_output

def searcher(stations_dict,
         NL_only = True,
         parameters = ['pm25'],
         variables_of_interest = ['num_of_rows','period','available_streams'],
         grid_point_metric = 'peak',
         index_of_peak = 0,
         return_only_ids = False,
         val_id = 'VAL_PRE'):
    
    '''
    grid_point_metric options:
    - None: error - dont do it.
    - peak: the list that has the point in time that has highest amount of stations coniciding
    - longest_range: the list that has the lonset range (range_end - range_start)
    - points_avg: the list that has stations with highest amount of points, on average (validation data not included)
    - poinst_std: the list that has the lowest variance (standard deviation) between points
    
    for peak:
    if you want something other than highest, change the 'index_of_peak' (i.e. 1 will give u 2nd peak, 2 will give u 3rd ... etc)
    '''

    stations_filtered = create_time_periods(sort_and_keep_val(stations_dict,
                                                            include = variables_of_interest,
                                                              val_id = val_id),
                                        parameter=parameters ,
                                        sort = True,
                                        NL_only = NL_only,
                                        val_id = val_id)

    output = {}
    if grid_point_metric == 'peak':
        for country, stations in stations_filtered.items():
            output[country] = stations[index_of_peak]
        
    elif grid_point_metric == 'longest_range':

        for country, stations in stations_filtered.items():
            max_range = 0
            for idx, data in stations.items():
                    dum_range = data[0][0][1] - data[0][0][0]
                    if dum_range > max_range:
                        max_range = dum_range
                        output[country] = data

    elif grid_point_metric == 'points_avg':
        for country, stations in stations_filtered.items():
            highest_average = 0
            for idx, data in stations.items():
                points_array = np.array([station[1][1] for station in data[2] if not station[0].endswith(val_id)])

                mean = np.mean(points_array)
                if mean > highest_average:
                    highest_average = mean
                    output[country] = data

    elif grid_point_metric == 'points_std':
        for country, stations in stations_filtered.items():
            lowest_std = float('inf')
            for idx, data in stations.items():
                points_array = np.array([station[1][1] for station in data[2] if not station[0].endswith(val_id)])

                std_dev = np.std(points_array)
                if std_dev < lowest_std:
                    lowest_std = std_dev
                    output[country] = data
        
    else:
        print('error: please define a metric')
        return None

    if return_only_ids:
        
        return bring_ids(output)

    else:
        return output
    
# drop_na = False


def align_station_times(station_dict,
                        time_decision,
                        remove_empty_df,
                        val_id = 'VAL_PRE'):

    if not station_dict:
        return {}
    
    # Get set of timestamps for each station
    time_sets = []
    if time_decision == 'VAL':

        for station_id, df in station_dict.items():
            if val_id in station_id:
                if 'time' not in df.columns:
                    raise ValueError(f"DataFrame for station {station_id} missing 'time' column")
                time_sets.append(set(df['time'].unique()))
    elif time_decision == 'most':

        for station_id, df in station_dict.items():
            if 'time' not in df.columns:
                raise ValueError(f"DataFrame for station {station_id} missing 'time' column")
            time_sets.append(set(df['time'].unique()))

        time_sets = find_threshold_meeting_intersection(time_sets)


    # Find intersection of all time sets
    common_times = set.intersection(*time_sets)

    if not common_times:
        raise ValueError("No common timestamps found across all stations")

    # Create new dictionary with filtered dataframes
    aligned_dict = {}
    for station_id, df in station_dict.items():
        # Create a copy to avoid modifying original
        aligned_df = df[df['time'].isin(common_times)].copy()
        # Sort by time to ensure consistency
        aligned_df = aligned_df.sort_values('time').reset_index(drop=True)
        if remove_empty_df:
            if aligned_df.empty:
                continue
        aligned_dict[station_id] = aligned_df
    
    return aligned_dict




def align_region_station_times(nested_dict, 
                               time_decision = 'VAL',
                               remove_empty_df = True):
    """
    if the dictionary is regioned 
    """
    aligned_nested = {}
    
    for region, station_dict in nested_dict.items():
        try:
            aligned_nested[region] = align_station_times(station_dict, 
                                                        time_decision = time_decision,
                                                        remove_empty_df = remove_empty_df)
        except ValueError as e:
            warnings.warn(f"Could not align times for region {region}: {str(e)}")
            continue
            
    return aligned_nested


def dataloader(searcher_output,
               keep_columns = ['time','temp','rh','pm25','pm10'],
               regions = 'all',
               align_in_time = True,
               time_decision = 'VAL',
               remove_empty_df = True):
    '''
    Inputs:
        searcher_output (required):
        - The input is the output of the searcher, per country,
        it is a dictionary where the key is region names (e.g. 'Netherlands'), and values is a list of station id as a string (e.g. ['UTR_bu011','UTR_bu008'])
        
        optional parameters:
        - keep_columns: choose parameters (column names) that you want. 
            * default is ['time','temp','rh','pm25','pm10']. input is a list of strings of parameter names (e.g. 'pm25')
            * an empty list will instead not do a check and return all variables
            * if you input a parameter name that is non-existent in the data it will return an empty df
            * This is an (or) operation
        - regions: choose the regions from the dictionary. 
            (default)   'all' => returns a dictionary of dataframes 
                        list of names => returns a dictionary of dataframes that includes a these countries. 
                        if the list has only one string, the output will not be a dictionary and just the singular output.
                        if the list contains a region not in the dictionary, it will skip it and give a warning message.
        - return_multiple_df: return a separate df for every station (as a dictionary)
            (default)   False: return everything as one dataframe. There will be a new column that contains the id of the original station as a string
                        True: return everything as a dictionary of dataframes. The keys will be station name as a string, and the value is the pandas dataframe.
            If there are multiple regions, then this will result in a nested dictionary (e.g.: {'Netherlands':{'station_1': dataframe, 'station_2': dataframe2 ...}})
        - time_decision: how to decide the alignment of time
            (default)   VAL: use the longest time VAL station as the base
                        longest_intersection (unimplemented)
        Output:
            Depending on the options, return either a dataframe or a dictionary of dataframes of the data.
            The data in question is in 'ROOT' folder. the ROOT folder is expected to have folders of station_id's (matching the searcher_output namings)
            Every folder contains two files: a csv file and a json file, their names match their original station example:

    '''
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
            result[region][station_id] = df

    if align_in_time:
        return align_region_station_times(result, 
                                          time_decision = time_decision,
                                          remove_empty_df= remove_empty_df)
    
    return result
        

def find_best_time(loaded_data,
                   minimum_hours = 8760 ,
                   year_splits = 4,
                   return_full_dict = True,
                   val_id = 'VAL_PRE'):
    max_time_point = {region: None for region in loaded_data}
    for region, stations in loaded_data.items():
        min_time = min(datfra['time'].min() for datfra in stations.values())
        max_time = max(datfra['time'].max() for datfra in stations.values())
        tot_range = max_time - min_time / minimum_hours
        if tot_range < 1:
            print('less than a year of data')
        time_array = np.array(range(min_time, max_time, int((minimum_hours*3600)/year_splits)))
        
        result = {int(t): [] for t in time_array}
        
        # Iterate through each station
        for station_name, df in stations.items():
            # Get min and max time for this station
            min_time = df['time'].min()
            max_time = df['time'].max()
            
            # Check each time point
            for time_point in time_array:
                # If time point falls within station's time range
                if min_time <= time_point <= max_time:
                    result[int(time_point)].append(station_name)
        
        # Filter out keys that don't have any station containing 'val_id'
        max_stations_count = 0
        point = None
        
        for time_point, stations in result.items():
            # Check if any station name contains 'val_id'
            if any(val_id in station for station in stations):
                if len(stations) > max_stations_count:
                    max_stations_count = len(stations)
                    point = time_point
        max_time_point[region] = point

    if return_full_dict:
        filtered_data = {}
    
        for region, stations in loaded_data.items():
            if region not in max_time_point:
                continue
                
            target_time = max_time_point[region]
            filtered_stations = {}
            
            for station_name, df in stations.items():
                # Get the time range for the current station
                min_time = df['time'].min()
                max_time = df['time'].max()
                
                # Check if the target time falls within the range (inclusive)
                if min_time <= target_time <= max_time:
                    filtered_stations[station_name] = df
            
            # Only add the region if it has any matching stations
            if filtered_stations:
                filtered_data[region] = filtered_stations
        return filtered_data

            
    return max_time_point
    
def merge_dict(filtered_data, 
               variables = PARAMETERS, 
               thresh = 0.5):
    
    '''
    thresh: Threshold options.
    - string: 'any' and 'all'. following pandas dropna documentation (DataFrame.dropna(how={'any','all'}))
    - integer: minimum number of required stations to be included (DataFrame.dropna(thresh=))
    - float: a fraction of total columns (minus time column), rounded down
    '''
    merged_regions = {}
    
    for region, stations in filtered_data.items():
        # Collect all station dataframes
        station_dfs = []
        
        for station_id, df in stations.items():
            # Filter variables if specified
            if variables:
                cols_to_keep = ['time'] + [f'{station_id}_{var}' for var in variables]
                df_copy = df[['time'] + variables].copy()
                
                # Rename columns to include station_id
                df_copy.columns = ['time'] + [f'{station_id}_{var}' for var in variables]
            else:
                # If no variables specified, keep all columns
                cols_to_keep = list(df.columns)
                df_copy = df.copy()
                df_copy.columns = ['time'] + [f'{station_id}_{col}' for col in df.columns[1:]]
            
            station_dfs.append(df_copy)
        
        # Merge all station dataframes for the region
        merged_df = station_dfs[0]
        for df in station_dfs[1:]:
            merged_df = pd.merge(merged_df, df, on='time', how='outer')
        
        # # Sort by time and reset index
        merged_df = merged_df.sort_values('time').reset_index(drop=True)

        if thresh is not None:
            if isinstance(thresh,str):
                merged_df = merged_df.dropna(how = thresh)
            elif isinstance(thresh,float):
                merged_df = merged_df.dropna(thresh =  int((len(merged_df.columns)-1) * thresh))
            elif isinstance(thresh, int):
                merged_df = merged_df.dropna(thresh = thresh)
            else:
                print('Invalid thresh value, not dropping any NAs')
        
        merged_regions[region] = merged_df

    return merged_regions




def merge_dict(filtered_data, 
               variables = PARAMETERS, 
               thresh = 0.5):
    
    '''
    Note: this function assumes YOU are keepin track of what PARAMETERS you are working with - if you put in a parameter that possibly doesn't exist in some of the dataframes, it will crash.
    To fix this issue - trace back and include your parameter of interest in all the previous methods/function to ensure its inclusion. The default is always pm25. 
    thresh: Threshold options.
    - string: 'any' and 'all'. following pandas dropna documentation (DataFrame.dropna(how={'any','all'}))
    - integer: minimum number of required stations to be included (DataFrame.dropna(thresh=))
    - float: a fraction of total columns (minus time column), rounded down
    '''
    merged_regions = {}
    
    for region, stations in filtered_data.items():
        # Collect all station dataframes
        station_dfs = []
        
        for station_id, df in stations.items():
            # Filter variables if specified
            if variables:
                df_copy = df[['time'] + variables].copy()
                
                # Rename columns to include station_id
                df_copy.columns = ['time'] + [f'{station_id}_{var}' for var in variables]
            else:
                # If no variables specified, keep all columns
                df_copy = df.copy()
                df_copy.columns = ['time'] + [f'{station_id}_{col}' for col in df.columns[1:]]
            
            station_dfs.append(df_copy)
        
        # Merge all station dataframes for the region
        merged_df = station_dfs[0]
        for df in station_dfs[1:]:
            merged_df = pd.merge(merged_df, df, on='time', how='outer')
        
        # # Sort by time and reset index
        merged_df = merged_df.sort_values('time').reset_index(drop=True)

        if thresh is not None:
            if isinstance(thresh,str):
                merged_df = merged_df.dropna(how = thresh)
            elif isinstance(thresh,float):
                merged_df = merged_df.dropna(thresh =  int((len(merged_df.columns)-1) * thresh))
            elif isinstance(thresh, int):
                merged_df = merged_df.dropna(thresh = thresh)
            else:
                print('Invalid thresh value, not dropping any NAs')
        
        merged_regions[region] = merged_df

    return merged_regions



def select_best_columns(df, limit_columns=6, include_anyway='VAL_PRE', exclude_cols=['time']):
    """
    Select columns with least NaN values using a sliding window approach.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Input dataframe
    limit_columns : int
        Desired number of columns in final output (excluding include_anyway column)
    include_anyway : str
        Column name that must be included in final result, e.g. val_id
    exclude_cols : list
        Columns to exclude from the analysis
    
    Returns:
    --------
    pandas.DataFrame
        Dataframe with selected columns, time column leftmost if present
    """
    # Create a copy to avoid modifying original
    work_df = df.copy()
    
    # Remove excluded columns from analysis
    for col in exclude_cols:
        if col in work_df.columns:
            work_df = work_df.drop(columns=[col])
    
    # Store original column names
    original_columns = work_df.columns.tolist()
    
    # Initialize set to store selected columns
    selected_columns = set()
    
    # Calculate initial window size
    current_window_size = len(work_df.columns)
    
    while current_window_size > limit_columns and len(selected_columns) < limit_columns:
        min_na_count = float('inf')
        best_columns = []
        
        # Slide window across columns
        for i in range(len(original_columns) - current_window_size + 1):
            window_columns = original_columns[i:i + current_window_size]
            
            # Skip if we've already selected some of these columns
            if any(col in selected_columns for col in window_columns):
                continue
                
            # Count total NaN values in current window
            na_count = work_df[window_columns].isna().sum().sum()
            
            # Update best columns if we found a better window
            if na_count < min_na_count:
                min_na_count = na_count
                best_columns = window_columns
        
        # Add best columns to selected set
        selected_columns.update(best_columns)
        
        # Reduce window size for next iteration
        current_window_size -= 1
    
    # Ensure we have exactly limit_columns number of columns (excluding include_anyway)
    if len(selected_columns) > limit_columns:
        # Calculate NA counts for all selected columns
        na_counts = work_df[list(selected_columns)].isna().sum()
        # Keep only the best limit_columns columns
        selected_columns = set(na_counts.nsmallest(limit_columns).index)
    
    # Add include_anyway column separately (not counting towards limit_columns)
    if include_anyway in df.columns and include_anyway not in selected_columns:
        selected_columns.add(include_anyway)
    
    # Prepare final column order
    final_columns = []
    
    # Add time column first if it exists
    if 'time' in df.columns:
        final_columns.append('time')
    
    # Add selected columns
    selected_list = list(selected_columns)
    
    # Sort selected columns to ensure consistent order
    # Put include_anyway first among selected columns if it exists
    if include_anyway in selected_list:
        selected_list.remove(include_anyway)
        final_columns.append(include_anyway)
    
    # Add remaining selected columns
    final_columns.extend(selected_list)
    
    # Return dataframe with selected columns in proper order
    return df[final_columns]


def filter_out_bad_columns(df):
    '''
    must include a way to remove columns if they managed to skip all preprocessing.
    '''
    return df


def fill_continuous_timestamps(df, time_column='time', time_step=3600):

    # Ensure the time column is sorted
    df_sorted = df.sort_values(by=time_column).reset_index(drop=True)
    
    # Get the start and end times from the original DataFrame
    start_time = df_sorted[time_column].min()
    end_time = df_sorted[time_column].max()
    
    # Create a complete range of timestamps
    full_timestamp_range = pd.DataFrame({
        time_column: range(int(start_time), int(end_time) + time_step, time_step)
    })
    
    # Merge the full timestamp range with the original DataFrame
    # This will preserve original data and add NaN for missing timestamps
    filled_df = full_timestamp_range.merge(
        df_sorted, 
        on=time_column, 
        how='left'
    )
    
    return filled_df

# Example usage
# sample_filled = fill_continuous_timestamps(sample)

def sample_data(final_df,num_rows = 720, thresh=1.0):
    while(True):
        start_idx = np.random.randint(0, len(final_df) - num_rows + 1)
        end_idx = start_idx + num_rows
        returned = final_df.iloc[start_idx:end_idx,:]
        if len(returned.dropna()) >= len(returned)*thresh:
            break
    

    return final_df.iloc[start_idx:end_idx,:]


def advanced_nan_imputation(df, max_nan_ratio=0.2):
    """
    Impute NaN values in a DataFrame using advanced statistical methods.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Input DataFrame with NaN values to impute
    method : str, optional (default='statistical')
        Imputation method:
        - 'statistical': Uses mean and standard deviation for imputation
        - 'linear_interpolation': Uses linear interpolation for time series
        - 'forward_fill': Propagates last known value forward
    max_nan_ratio : float, optional (default=0.1)
        Maximum allowed ratio of NaN values in a column for imputation
    
    Returns:
    --------
    pandas.DataFrame
        DataFrame with NaN values imputed
    """
    # Create a copy of the DataFrame to avoid modifying the original
    imputed_df = df.copy()
    
    def statistical_imputation(series):
        """
        Impute NaN values using a statistically constrained approach.
        
        1. Calculates column mean and standard deviation
        2. Uses truncated normal distribution to generate replacement values
        3. Ensures imputed values are statistically similar to existing data
        """
        # Check NaN ratio
        nan_ratio = series.isna().mean()
        
        if nan_ratio > max_nan_ratio:
            print(f"Warning: NaN ratio ({nan_ratio:.2%}) exceeds threshold. Skipping imputation.")
            return series
        
        # Compute descriptive statistics
        valid_data = series.dropna()
        mean = valid_data.mean()
        std = valid_data.std()
        
        # Find NaN indices
        nan_indices = series.index[series.isna()]
        
        # Generate replacement values using truncated normal distribution
        replacements = stats.truncnorm.rvs(
            a=(valid_data.min() - mean) / std,  # Lower bound
            b=(valid_data.max() - mean) / std,  # Upper bound
            loc=mean,   # Center of distribution
            scale=std,  # Spread of distribution
            size=len(nan_indices)
        )
        
        # Replace NaN values
        imputed_series = series.copy()
        imputed_series.loc[nan_indices] = replacements
        
        return imputed_series
    
    # Apply imputation to each column
    for column in imputed_df.select_dtypes(include=[np.number]).columns:
        imputed_df[column] = statistical_imputation(imputed_df[column])
    
    return imputed_df
def mask_extended_zeros(df, threshold=0.5, consecutive_limit=96):
    """
    Process sensor data to identify and replace extended periods of near-zero or NaN values.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame containing sensor data columns
    threshold : float, default=0.5
        Values with absolute magnitude below this threshold will be considered "zero"
    consecutive_limit : int, default=96
        Number of consecutive "zero" values that trigger replacement with NaN
        
    Returns:
    --------
    pandas.DataFrame
        A copy of the input DataFrame with extended near-zero periods replaced by NaN
    """
    # Create a copy of the DataFrame to avoid modifying the original
    result_df = df.copy()
    
    # Process each column
    for column in df.columns:
        # Create mask: 1 for values below threshold or NaN, 0 otherwise
        mask = ((df[column].abs() < threshold) | df[column].isna()).astype(int)
        
        # Find runs of consecutive 1s
        # First, identify where the mask changes
        change_points = mask.diff().fillna(0).ne(0)
        
        # Assign run IDs
        run_id = change_points.cumsum()
        
        # Count consecutive 1s in each run
        run_lengths = mask.groupby(run_id).transform('count') * mask
        
        # Identify positions where run length exceeds the limit and mask is 1
        extended_zeros = (run_lengths >= consecutive_limit) & (mask == 1)
        
        # Replace the identified positions with NaN in the result DataFrame
        result_df.loc[extended_zeros, column] = np.nan
    
    return result_df

# parameters = ['pm25']
# BASE_STATIONS_WITH_GRIDS_PATH = ''
# STATIONS_FILTERED = create_time_periods(sort_and_keep_val(STATIONS_WITHIN_GRIDS,
#                                                           include = variables_of_interest),
#                                         parameter=PARAMETERS ,
#                                         sort = True,
#                                         NL_only = NL_only)
import numpy as np
from collections import Counter
from typing import List, Set

def find_threshold_meeting_intersection(time_sets: List[Set[int]], min_sets: int = 5, initial_factor: float = 2.0, 
                                        factor_decrement: float = 0.5, min_factor: float = -2.0) -> List[Set[int]]:
    """
    Find intersections of time sets that meet a threshold condition.
    
    Args:
        time_sets: List of sets, where each set contains epoch timestamps
        min_sets: Minimum number of sets that should contribute to an intersection
        initial_factor: Starting factor for threshold calculation
        factor_decrement: Amount to reduce factor by in each iteration
        min_factor: Minimum value for factor before giving up
        
    Returns:
        List of sets meeting the criteria, or empty list if none found
    """
    # 1. Calculate average and standard deviation of set lengths
    set_lengths = [len(s) for s in time_sets]
    avg_length = np.mean(set_lengths)
    std_dev = np.std(set_lengths)
    
    print(f"Average set length: {avg_length}")
    print(f"Standard deviation: {std_dev}")
    
    # Get all unique timestamps across all sets
    all_timestamps = set()
    for time_set in time_sets:
        all_timestamps.update(time_set)
    
    # Count occurrences of each timestamp
    timestamp_counter = Counter()
    for time_set in time_sets:
        for timestamp in time_set:
            timestamp_counter[timestamp] += 1
    
    # Keep only timestamps that appear in at least min_sets
    valid_timestamps = {ts: count for ts, count in timestamp_counter.items() 
                        if count >= min_sets}
    
    if not valid_timestamps:
        print(f"No timestamps appear in at least {min_sets} sets")
        return []
    
    # Group timestamps by their occurrence count
    timestamps_by_count = {}
    for ts, count in valid_timestamps.items():
        if count not in timestamps_by_count:
            timestamps_by_count[count] = set()
        timestamps_by_count[count] = timestamps_by_count[count].union({ts})
    
    # 2-5. Adjust factor and find intersections meeting the threshold
    factor = initial_factor
    while factor >= min_factor:
        threshold = avg_length + (std_dev * factor)
        print(f"Current factor: {factor}, Threshold: {threshold}")
        
        # Try to find intersections starting from the highest count
        for count in sorted(timestamps_by_count.keys(), reverse=True):
            if count < min_sets:
                continue
                
            current_intersection = timestamps_by_count[count]
            if len(current_intersection) >= threshold:
                # Success - we found an intersection meeting our criteria
                return [current_intersection]
        
        # Reduce factor and try again
        factor -= factor_decrement
    
    # If we get here, no intersection met our criteria
    print("No intersection meeting the criteria was found")
    return []



def find_sensors_in_radius(full_meta, 
                           center_lon, 
                           center_lat, 
                           radius_km, 
                           variable_list, 
                           NL_ONLY = True,
                           return_as_dict = True):
    """
    Find sensors within a specified radius that have the requested variables.
    
    Parameters:
    -----------
    full_meta : dict
        Dictionary where keys are sensor IDs and values are metadata dictionaries.
    center_lon : float
        Longitude of the center point in EPSG:4326 (WGS84).
    center_lat : float
        Latitude of the center point in EPSG:4326 (WGS84).
    radius_km : float
        Search radius in kilometers.
    variable_list : list
        List of variables that sensors must have.
    NL_ONLY : bool
        search only for sensors in the netherlands
    return_as_dict : bool
        return as dictionary: {'Netherlands': [list]}
        no checks are implemented, be careful when using other countries.

    
    Returns:
    --------
    list
        List of sensor IDs that are within the radius and have all the requested variables.
    """
    matching_sensors = []
    
    # Earth radius in kilometers
    earth_radius = 6371.0
    
    for sensor_id, metadata in full_meta.items():
        if NL_ONLY:
            if metadata['country'] != 'Netherlands':
                continue
        # Skip sensors that don't have location data
        if 'longitude' not in metadata or 'latitude' not in metadata:
            continue
            
        # Skip sensors that don't have the requested variables
        if 'available_streams' not in metadata:
            continue
            
        # Check if all requested variables are available for this sensor
        if not all(var in metadata['available_streams'] for var in variable_list):
            continue
        
        # Calculate distance using Haversine formula
        lon1, lat1 = center_lon, center_lat
        lon2, lat2 = float(metadata['longitude']), float(metadata['latitude'])

        # Convert to radians
        lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        
        distance = earth_radius * c # Distance in meters

        # Check if within radius
        if distance <= radius_km:
            matching_sensors.append(sensor_id)
    
    if return_as_dict:
        return {'Netherlands': matching_sensors}
    return matching_sensors


def filter_intersecting_lists(in_list, with_coordinates = False):

    if with_coordinates:
        dum_index = [dum[1] for dum in in_list]
    else:
        dum_index = in_list
    # Create a dictionary to track which IDs appear in which lists
    id_to_lists = {}
    for i, id_list in enumerate(dum_index):
        for id_val in id_list:
            if id_val not in id_to_lists:
                id_to_lists[id_val] = []
            id_to_lists[id_val].append(i)
    
    # Track which lists have been processed and which are included in result
    processed = set()
    result = []
    
    # Process each list
    for i, id_list in enumerate(dum_index):
        if i in processed:
            continue
            
        # Check if this list shares IDs with others
        related_lists = set()
        for id_val in id_list:
            for list_idx in id_to_lists[id_val]:
                related_lists.add(list_idx)
        
        # If no shared IDs, add this list to result
        if len(related_lists) == 1:  # Only contains itself
            if with_coordinates:
                result.append(in_list[i][0])
            else:
                result.append(id_list)                
            processed.add(i)
        else:
            # Find the longest list among related lists
            longest_idx = max(related_lists, key=lambda idx: len(dum_index[idx]))

            if with_coordinates:
                result.append(in_list[i][0])
            else:
                result.append(dum_index[longest_idx])
            # Mark all related lists as processed
            processed.update(related_lists)
    
    return result

def filter_locations(thresholded, km_range = 3):
    """
    Filter a list of [coordinates, items] pairs by:
    1. Sorting by number of items (descending)
    2. Removing locations that are within 3km of another location that has more items
    
    Args:
        thresholded: List of [[coord1, coord2], [item1, item2, ...]] where coords are floats
                    in EPSG4326 format and items are strings
    
    Returns:
        List of filtered locations following the specified criteria
    """
    # Sort by number of items in descending order
    sorted_locations = sorted(thresholded, key=lambda x: len(x[1]), reverse=True)
    
    # Initialize list to track which locations to keep
    keep = [True] * len(sorted_locations)
    
    # Start from the bottom of the list (least number of items)
    for i in range(len(sorted_locations) - 1, -1, -1):
        # Skip if already marked for removal
        if not keep[i]:
            continue
        
        current_coords = sorted_locations[i][0]
        
        # Check all locations above this one (those with more items)
        for j in range(i - 1, -1, -1):
            if not keep[j]:
                continue
                
            other_coords = sorted_locations[j][0]
            
            # Calculate distance in kilometers
            distance = geodesic(
                (current_coords[0], current_coords[1]), 
                (other_coords[0], other_coords[1])
            ).kilometers
            
            # If within 3km of a location with more items, mark for removal
            if distance <= km_range:
                keep[i] = False
                break
    
    # Filter and return only the locations to keep
    filtered_locations = [sorted_locations[i] for i in range(len(sorted_locations)) if keep[i]]
    return filtered_locations


def select_columns_by_presence(df: pd.DataFrame, n: int, time_column: str = 'time') -> pd.DataFrame:
    """
    Selects a combination of `n` columns (excluding `time_column`) that maximizes the number of rows
    where at least `n//2` of these columns are non-NA.

    Parameters:
    - df: Input DataFrame with a time column and other data columns.
    - n: Number of data columns to select (excluding the time column).
    - time_column: Name of the time column to keep in the result.

    Returns:
    - A new DataFrame containing the time column and the best `n` columns.
    """
    # List of candidate data columns
    non_time_cols = [col for col in df.columns if col != time_column]
    if n > len(non_time_cols):
        raise ValueError(f"n={n} is greater than available columns={len(non_time_cols)}")

    best_cols = None
    best_count = -1
    # Define the threshold for a row to count as "present": at least floor(n/2) non-NA
    min_non_na = n // 2

    # Evaluate each combination of n columns
    for combo in combinations(non_time_cols, n):
        # Count rows where at least `min_non_na` columns are non-NA
        present_count = (df[list(combo)].notna().sum(axis=1) >= min_non_na).sum()
        if present_count > best_count:
            best_count = present_count
            best_cols = combo

    # Build the resulting DataFrame
    result_cols = [time_column] + list(best_cols)
    return df[result_cols].copy()


NL_ONLY = True
PARAMETERS = ['pm25']
# val_id = 'VAL_PRE'
VARIABLES_OF_INTEREST = ['num_of_rows','period','available_streams']


