import math
import json
import os

import pandas as pd
import psutil

from sklearn.cluster import DBSCAN
import rasterio
DIS_THRESHOLD = 1000 #meters
# DBSCAN_RADIUS = 20
DBSCAN_STD_FACTOR = 1.5
DBSCAN_SAMPLES = 12
R = 6371000.0 # Radius of earth in meters


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
    'FN':(-10,100),
    'BCWB':(-10,100),
    'C10H8':(-5,50),
    'C6H6':(-5,50),
    'C7H8':(-5,50),
    'C8H10':(-5,50),
    'rh':(-2,105),
    'pm25_kal':(-50,1000),
    'temp':(-50,70),
    'P0':(-50,1000),
    'P1':(-50,1000),
    'P2':(-50,1000),
    'humidity':(-1,105),
    'pressure':(90000,130000),
    'temperature':(-50,70)

}


def haversine(lat1, lon1, lat2, lon2):
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    
    distance = R * c # Distance in meters
    return distance


def load_json_file(file_path):
    with open(file_path, 'r') as file:
        json_file = json.load(file)
    return json_file

def write_json_file(file_path, data):
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)


def write_csv_file(file_path, data):
    data.to_csv(file_path, index=False)

# def find_closest_points(lon_orig, lat_orig, official = True, crowd = False, official_val = False):
#     '''
#     search for stations in the root folders that is within a threshold DIS_THRESHOLD
    
#         lon_orig: longitude of origin, EPSG4326, float
#         lat_orig: latitude of origin, EPSG4326, float
#         official: type of desired source, True or False
#         crowd: type of desired source, True or False
#         official_val: use the csv files from official data
#     '''

#     sorted_to_origin = {}
#     for folder in os.listdir(ROOT):
#         folder_path = os.path.join(ROOT,folder)
#         metadata_path = os.path.join(folder_path,folder+'.json')
#         metadata = load_json_file(metadata_path)
#         if crowd == False and metadata['type'] == 'crowd':
#             continue
#         elif official == False and metadata['type'] == 'official_unval':
#             continue
#         elif official_val == False and metadata['type'] == 'official_val':
#             continue
#         lon, lat = float(metadata['longitude']), float(metadata['latitude'])

#         # if dis_to_orig < DIS_THRESHOLD:
#         #     within_threshold[folder] = {'type': metadata['type'],
#         #                                 'distance_to_origin': dis_to_orig}
#         sorted_to_origin[folder] = {'type': metadata['type'],
#                                         'distance_to_origin': haversine(lon_orig,lat_orig,lon,lat)}
#     sorted_to_origin =  dict(sorted(sorted_to_origin.items(), key= lambda item: item[1]['distance_to_origin']))
#     within_threshold = {k: sorted_to_origin[k] for i, k in enumerate(sorted_to_origin) if (sorted_to_origin[k]['distance_to_origin'] < DIS_THRESHOLD and sorted_to_origin[k]['distance_to_origin']>0)}
#     return sorted_to_origin, within_threshold
        

def run_dbscan_on_df(df,
                  streams,
                  dbs_radius = DBSCAN_STD_FACTOR, 
                  min_samples = DBSCAN_SAMPLES):

    df_final = pd.DataFrame()
    # Getting % usage of virtual_memory ( 3rd field)
    # print('RAM memory % used:', psutil.virtual_memory()[2])
    # # Getting usage of virtual_memory in GB ( 4th field)
    # print('RAM Used (GB):', psutil.virtual_memory()[3]/1000000000)
    
    for stream in streams:

 
        df_dum = df[['time',stream]].dropna()
        if stream in RANGES:
            # Get the range of values for the column variable (name)
            min_val, max_val = RANGES[stream]

            # Drop rows where the data is not within the range of values
            df_dum = df_dum[(df_dum[stream] >= min_val) & (df_dum[stream] <= max_val)]

        
        if len(df_dum) <= 1:
            continue
        else:
            try:
                dbscan = DBSCAN(eps=df_dum[stream].std()*dbs_radius, min_samples=min_samples)
                outliers = dbscan.fit_predict(df_dum[[stream]])


                df_dum["outlier"] = outliers == -1
                df_dum = df_dum.loc[~df_dum['outlier']]
            except:
                df_dum = df_dum


            if df_final.empty:
                df_final[['time', stream]] = df_dum[['time',stream]]
            else:
                df_final = pd.merge(df_final, df_dum[['time',stream]], on='time',how='outer')
            del df_dum
                
        
    return df_final

# def find_closest_official(location):
    
#     return official_metadata

# def validity_check(datasource):

#     return validity