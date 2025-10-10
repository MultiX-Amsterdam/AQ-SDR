'''
This code fix the coordinates for the data pulled from sensors that have more than one geolocation due to movement/reinstalling.
No need to run it.
define roots:
'''

ROOT = '/dum/dum/crowd_stations_root'
OLD_ROOT = ROOT
NEW_ROOT = '/dum/dum/crowd_stations_root_fixed_nldebe'

import json
from shapely.geometry import Point, shape, Polygon, MultiPolygon
from shapely.ops import unary_union
from pyproj import Geod
from itertools import combinations
import numpy as np 
from scipy.spatial.distance import squareform
import os
import json
import pandas as pd
import numpy as np 
import pandas as pd
import matplotlib.pyplot as plt
import datetime

from statsmodels.tsa.seasonal import STL
from sklearn.neighbors import LocalOutlierFactor
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN

import json

import shutil
import math
import datetime
import calendar


def convert_to_epoch(reduced_locations):
    # Create a new dictionary to store the converted data
    converted_locations = {}
    
    for station, location_data in reduced_locations.items():
        # Create a list to store converted location data
        converted_station_data = []
        
        for item in location_data:
            # Extract timestamps and coordinates
            timestamps = item[0]
            coords = item[1]
            
            # Convert timestamps to epoch time
            epoch_timestamps = []
            for timestamp in timestamps:
                # Parse the UTC timestamp
                dt = datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
                
                # Convert to epoch time (seconds since 1970-01-01)
                epoch_time = calendar.timegm(dt.timetuple()) + dt.microsecond / 1e6
                
                epoch_timestamps.append(epoch_time)
            
            # Add the converted data to the new list
            converted_station_data.append([epoch_timestamps, coords])
        
        # Add the converted station data to the new dictionary
        converted_locations[station] = converted_station_data
    
    return converted_locations

R = 6371000.0
def haversine(lat1, lon1, lat2, lon2, int_out=False):
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    
    
    distance = R * c # Distance in meters

    if int_out:
        return int(distance)
    else:
        return distance
def reduce_list(lst):
    # Create a dictionary to store the average coordinates for each unique geolocation
    geo_dict = {}

    # Iterate over each element in the input list
    for element in lst:
        # Extract the geolocation and convert it to a tuple
        lon, lat = element[1]

        # Check if the latitude and longitude values are within the specified ranges
        if not (50 <= lat <= 54 and 3 <= lon <= 8):
            # If not, check if they are reversed
            if 50 <= lon <= 54 and 3 <= lat <= 8:
                # If they are reversed, swap them
                lon, lat = lat, lon
            else:
                # If they are not reversed, discard the element
                continue

        # Round the coordinates to one decimal place
        geo = (round(lon, 1), round(lat, 1))

        # If the geolocation is already in the dictionary, append the element to the list
        if geo in geo_dict:
            geo_dict[geo].append((element[0], lon, lat))
        # Otherwise, create a new list for the geolocation
        else:
            geo_dict[geo] = [(element[0], lon, lat)]

    # Create a new list to store the reduced list
    reduced_list = []

    # Iterate over each list of elements in the dictionary
    for elements in geo_dict.values():
        # Extract the timestamps, longitudes, and latitudes
        timestamps = [element[0] for element in elements]
        lons = [element[1] for element in elements]
        lats = [element[2] for element in elements]

        # Calculate the average coordinates
        avg_lon = sum(lons) / len(lons)
        avg_lat = sum(lats) / len(lats)

        # Add the reduced element to the new list
        reduced_list.append([timestamps, (avg_lon, avg_lat)])

    return reduced_list

def average_coordinates(coordinate_list):
    if not coordinate_list:
        raise ValueError("Input list is empty")
    
    try:
        coordinates = [coord for _, coord in coordinate_list]
        
        avg_longitude = sum(coord[0] for coord in coordinates) / len(coordinates)
        
        avg_latitude = sum(coord[1] for coord in coordinates) / len(coordinates)
        
        return (avg_longitude, avg_latitude)
    
    except (TypeError, ValueError) as e:
        print(f"Error processing coordinates: {e}")
        return None
def create_paths(station,root):
    return os.path.join(root,station), os.path.join(root,station,f'{station}.json'), os.path.join(root,station,f'{station}.csv')
    
def load_json_file(file_path):
    with open(file_path, 'r') as file:
        json_file = json.load(file)
    return json_file

def write_json_file(file_path, data):
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)

def delete_station(station_path):
    try:
        # Check if the path exists
        if os.path.exists(station_path):
            # Remove the entire directory and all its contents
            shutil.rmtree(station_path)
            print(f"Successfully deleted directory: {station_path}")
        else:
            print(f"Directory does not exist: {station_path}")
    except PermissionError:
        print(f"Permission denied: Unable to delete {station_path}")
    except Exception as e:
        print(f"Error deleting directory {station_path}: {str(e)}")

def write_csv_file(file_path, data):
    data.to_csv(file_path, index=False)

def split_dataframe(df, lst):
    split_dataframes = {}
    
    masks = []
    times = []
    geolocation = []
    for idx, item in enumerate(lst):
        # print(idx,lst[idx][0][0])
        if idx == 0:
            masks.append(df['time'] <= lst[idx+1][0][0])
            times.append(lst[idx][0][0])
            geolocation.append(lst[idx][1])
        elif idx < (len(lst) -1):
            masks.append(df['time'].between(lst[idx][0][0], lst[idx+1][0][0], inclusive = 'neither'))
            times.append(lst[idx][0][0])
            geolocation.append(lst[idx][1])
        else:
            masks.append(df['time'] >= lst[idx][0][0])
            times.append(lst[idx][0][0])
            geolocation.append(lst[idx][1])



    for idx, mask in enumerate(masks):
        # print(mask, times[idx], geolocation[idx])
        if df[mask].empty:
            continue
        else:
            split_dataframes[geolocation[idx]] = df[mask].copy().reset_index(drop = True)


    return split_dataframes

def copy_file(path, newpath):
    try:
        # Copy the file
        shutil.copy2(path, newpath)
    except FileNotFoundError:
        print(f"Source file not found: {path}")
    except PermissionError:
        print(f"Permission denied when copying file")
    except Exception as e:
        print(f"Error copying file: {str(e)}")



def find_nearest_boundary_point(point, geometries):
    """
    Find the nearest point on the boundary of a MultiPolygon or Polygon
    
    :param point: Point to find nearest boundary to
    :param geometries: Shapely MultiPolygon or Polygon
    :return: Nearest point on the boundary
    """
    min_distance = float('inf')
    nearest_point = None
    
    # Handle both MultiPolygon and Polygon cases
    if isinstance(geometries, MultiPolygon):
        polygons = geometries.geoms
    elif isinstance(geometries, Polygon):
        polygons = [geometries]
    else:
        polygons = list(geometries.geoms)
    
    for poly in polygons:
        # Get the exterior boundary of the polygon
        exterior = poly.exterior
        
        # Project the point onto the exterior ring
        proj_dist = exterior.project(point)
        closest_point = exterior.interpolate(proj_dist)
        
        # Calculate distance between the original point and the closest point
        current_distance = point.distance(closest_point)
        
        if current_distance < min_distance:
            min_distance = current_distance
            nearest_point = closest_point
    
    return nearest_point

def check_in_eu(lon, lat, proximity_threshold=1000):
    """
    Check if a point is either inside the EU polygon or within a specified proximity.
    
    :param lon: Longitude of the point (in EPSG:4327)
    :param lat: Latitude of the point (in EPSG:4327)
    :param proximity_threshold: Proximity threshold in meters (default 1000m)
    :return: Boolean indicating if point is in or near EU
    """
    # Create the point
    point = Point(lon, lat)
    
    # Combine all EU polygons into a single multipolygon
    eu_polygons = unary_union([shape(feature['geometry']) for feature in EU_GEOJSON['features']])
    
    # First check: Is the point directly contained in any EU polygon?
    if eu_polygons.contains(point):
        return True
    
    # Create a geodesic calculator
    geod = Geod(ellps="WGS84")
    
    # Find the nearest point on the EU polygon boundary
    nearest_boundary_point = find_nearest_boundary_point(point, eu_polygons)
    
    if nearest_boundary_point is None:
        return False
    
    # Calculate geodesic distance between the point and the nearest boundary point
    _, _, distance = geod.inv(point.x, point.y, nearest_boundary_point.x, nearest_boundary_point.y)
    # print(distance)
    # Check if the distance is within the proximity threshold
    return distance <= proximity_threshold

# Load the GeoJSON file (ensure this path is correct)
with open('./utils/europe.geojson', 'r') as f:
    EU_GEOJSON = json.load(f)


total_folders = 0
mobile_folders =0
all_eu = False
if not all_eu:
    EU_GEOJSON['features'] = [
    feature for feature in EU_GEOJSON['features'] 
    if feature['properties'].get('NAME') == 'Netherlands' or feature['properties'].get('NAME') == 'Germany' or feature['properties'].get('NAME') == 'Belgium'
]
for idx,station in enumerate(os.listdir(OLD_ROOT)):

    # print(f'starting station id: {idx},{station}')
    station_path, json_path, csv_path = create_paths(station,OLD_ROOT)
    metadata = load_json_file(json_path)
    st_id = str(metadata['iot_id'])
    
    if st_id in non_significant:
        metadata['longitude'], metadata['latitude'] = average_coordinates(reduced_locations[st_id])
        if not check_in_eu(metadata['longitude'], metadata['latitude']):
                continue
        new_station_path = os.path.join(NEW_ROOT,station)
        new_json_path = os.path.join(NEW_ROOT,station,f'{station}.json')
        new_csv_path = os.path.join(NEW_ROOT,station,f'{station}.csv')
        os.makedirs(new_station_path, exist_ok=True)
        total_folders +=1
        write_json_file(new_json_path,metadata)
        copy_file(csv_path, new_csv_path)
        # print(f'replacing with average for {station}')
        # break
    # elif st_id in only_one:
    #     new_json_path = os.path.join(NEW_ROOT,station,f'{station}.json')
    #     new_csv_path = os.path.join(NEW_ROOT,station,f'{station}.csv')
    #     copy_file(json_path,new_json_path)
    #     copy_file(csv_path, new_csv_path)
    #     print(f'only one')
    #     continue
    elif st_id in many_changes:
        # delete_station(station_path)
        print(f'deleting {station}')
        continue
    elif st_id in significant:
        df = pd.read_csv(csv_path)
        split_frames = split_dataframe(df, reduced_locations_epoch[st_id])
        # print(f'creating multiple dataframes for {station}')
        for idx, frame in enumerate(split_frames):
            metadata['longitude'], metadata['latitude'] = frame
            if not check_in_eu(metadata['longitude'], metadata['latitude']):
                continue
                            
            new_station_path, new_json_path, new_csv_path = (os.path.join(NEW_ROOT,f'GEOMOBILEMX{idx}_{station}'),
                                                            os.path.join(NEW_ROOT,f'GEOMOBILEMX{idx}_{station}',f'GEOMOBILEMX{idx}_{station}.json'),
                                                            os.path.join(NEW_ROOT,f'GEOMOBILEMX{idx}_{station}',f'GEOMOBILEMX{idx}_{station}.csv'))
            
            os.makedirs(new_station_path, exist_ok=True)
            total_folders +=1
            mobile_folders +=1
            write_csv_file(new_csv_path,split_frames[frame])
            write_json_file(new_json_path,metadata)
            print(f'created new file: {new_station_path}')
            
        
        # delete_station(station_path)
    else:
        # print(f'no changes required')
        if not check_in_eu(metadata['longitude'], metadata['latitude']):
            continue
        new_station_path = os.path.join(NEW_ROOT,station)
        os.makedirs(new_station_path, exist_ok=True)
        total_folders +=1
        new_json_path = os.path.join(NEW_ROOT,station,f'{station}.json')
        new_csv_path = os.path.join(NEW_ROOT,station,f'{station}.csv')
        copy_file(json_path,new_json_path)
        copy_file(csv_path, new_csv_path)


    
        


