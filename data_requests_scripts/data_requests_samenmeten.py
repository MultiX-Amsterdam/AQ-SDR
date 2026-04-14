'''
Code to pull data from samenmetnet 'https://api-samenmeten.rivm.nl/v1.0/Things'.
Not updated - feel free to use it but don't rely on it being 100% up to date.

Usage:
python data_requests_samenmeten.py
'''

"""
For each sensor, this script create two files: one CSV, and one JSON.
The CSV file contains the data, and the JSON file contains the metadata of the station.
Define the root folder below to pull the data.
"""
root = '/home/ssda/new_data/crowd_stations_root'

"""
The last_checkpoint variable is used to indicate the last station that we pulled data from.
If the script crashes, you can change this variable to the last station that we pulled data from, and then run the script again.
For example, if the script crashes at station with @iot.id 500, you can change the last_checkpoint variable to 500, and then run the script again.
If we start pulling from scratch, this number should be 0.
To be clear, this @iot.id is at the level of https://api-samenmeten.rivm.nl/v1.0/Things and not data stream level.
"""
last_checkpoint = 0

"""
To get the data streams, we need to do the following:
- Go to https://api-samenmeten.rivm.nl/v1.0/Things and get the @iot.id
- We use an example of @iot.id 11756
- Next, we go to @iot.selfLink https://api-samenmeten.rivm.nl/v1.0/Things(11756)
- Next, we go to Datastreams@iot.navigationLink https://api-samenmeten.rivm.nl/v1.0/Things(11756)/Datastreams
- Next, for each data stream, we go to Observations@iot.navigationLink https://api-samenmeten.rivm.nl/v1.0/Datastreams(53610)/Observations
- And finally we arrive at the page with the data
The total_stations variable indicate the latest @iot.id on https://api-samenmeten.rivm.nl/v1.0/Things
"""
total_stations = 11528

"""
The MAX_PULLS variable indicates the number of data points that we pull from each data stream.
A sensor could have multiple data streams.
Each data point means one hour, so if MAX_PULLS is 18000, we are pulling roughly 2 years of data for that data stream.
"""
MAX_PULLS = 18000

"""
The LIMIT_TWO_YEARS is a flag to say that we want to enforce the MAX_PULLS limit.
If LIMIT_TWO_YEARS is set to false, the script will ignore the MAX_PULLS limit and will keep pulling data until there is no more data to pull.
This variable name should really be changed to something like ENFORCE_MAX_PULLS, but I will leave it as is for now.
"""
LIMIT_TWO_YEARS = True

"""
Data pull log:
- The latest time that we pull the data is around March 2026.
"""

"""
To update the data, do the following:
- 1. go to https://api-samenmeten.rivm.nl/v1.0/Things and write down the latest @iot.id
- 2. change the total_stations variable to that @iot.id
- 3. update the data pull log in this file to let the future person know how much data to pull
- 4. based on the last pulled time, change the MAX_PULLS variable to pull the right amount of data
- 5. make sure that LIMIT_TWO_YEARS remains true to avoid pulling everything
- 6. edit the root variable to the directory where you want to save the data
- 7. run the script and wait for it to finish
- 8. after that, run another script `TBD.py` to merge the new data with the old data

For example, if the latest @iot.id is 12000, and the latest time that we pulled data is March 2026, and we want to pull data until June 2026, we should do the following:
- change total_stations to 12000
- change the data pull log to say that we are pulling data until June 2026
- change MAX_PULLS to 3000 (since we are pulling roughly 3 months of data, which is roughly 3000 hours)
"""

import requests
import os
import math
import json
import datetime
import time
from datetime import datetime

import pandas as pd

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

start_time = time.time()

session = requests.Session()

retry = Retry(connect=3, backoff_factor =0.5)
adapter = HTTPAdapter(max_retries = retry)
session.mount('http://',adapter)
session.mount('https://', adapter)

def get_req(session, url):

    req = session.get(url)

    if req.status_code == 200:
        # print('successfully pulled, ', url)
        return req
    elif req.status_code == 429:
        print('Request limit, pausing for 5 minutes.')
        print('time now:', datetime.datetime.now())
        time.sleep(300)
        looper = True
        while(looper):
            time.sleep(300)
            req = session.get(url)
            if req.status_code != 429:
                looper == False
                print('Stopping pause, time now:', datetime.datetime.now())
                break
    elif req.status_code == 404:
        print('error code 404, skipping station', url)
    else:
        print('unkown error status code: ', req.status_code)

    return req


def dump_json(json_data, path):
    with open(path, 'w') as json_file:
        json.dump(json_data, json_file, indent=4)

def dump_csv(csv_data, path):
    csv_data.to_csv(path, index=False)



def get_page(req):
    try:
        nextlink = req.json()['@iot.nextLink']
        if int(nextlink.split('skip=')[1]) > MAX_PULLS and LIMIT_TWO_YEARS:
            nextlink = None
            print('Reached max pulls for 2 years limit')
        else:
            print(nextlink)
    except:
        nextlink = None
    data = []
    for value in req.json()['value']:
        data.append([value['phenomenonTime'],value['result']])
    return data, nextlink


for iot_id in range(last_checkpoint,total_stations+1):
    things_url = f'https://api-samenmeten.rivm.nl/v1.0/Things({iot_id})'
    things_req = get_req(session,things_url)


    if things_req.status_code != 200:
        print('error in iot_id: ', iot_id,' skipping to next')
        continue
    else:
        print('Starting with station iot_id: ', iot_id)
        data_sources = {}



    things_req_parsed = things_req.json()
    station_name = things_req_parsed['name']
    datastreams_link = things_req_parsed['Datastreams@iot.navigationLink']
    locations_link = things_req_parsed['Locations@iot.navigationLink']

    station_dir = os.path.join(root,station_name)
    os.makedirs(station_dir, exist_ok=True)

    locations_req = get_req(session, locations_link)



    if locations_req.status_code != 200:
        print('error in location of iot_id: ', iot_id,' skipping to next')
        lon, lat = -999,-999
    else:
        try:
            lon, lat = locations_req.json()['value'][0]['location']['coordinates']
        except:
            lon, lat = -999, -999

    json_data = {
                "type": 'crowd',
                'longitude': lon,
                'latitude': lat,
                'iot_id': things_req_parsed['@iot.id'],
                'properties': things_req_parsed['properties'],
                'datastreams_links': datastreams_link
    }

    json_data['available_streams']={}
    json_data['stream_units']={}
    json_data['sensor']={}


    # if lon == -999 and lat == -999:
    #     json_data['has_stream'] = 'False'
    #     json_data['has_data'] = 'False'
    #     dump_json(json_data, json_path)
    #     # continue
    # else:
    #     print('valid station')

    datastreams_req = get_req(session, datastreams_link)

    if datastreams_req.status_code != 200:
        print('error in datastreams req of iot_id: ', iot_id,' skipping to next')
        json_data['has_stream'] = 'False'
        json_data['has_data'] = 'False'
        dump_json(json_data, json_path)



    for stream in datastreams_req.json()['value']:
        json_data['available_streams'][stream['name'].rsplit('-')[-1]] = stream['@iot.id']
        json_data['stream_units'][stream['name'].rsplit('-')[-1]] = stream['unitOfMeasurement']['symbol']
        data_sources[stream['name'].rsplit('-')[-1]] = stream['Observations@iot.navigationLink']
    for sensor in json_data['available_streams']:
        try:
            json_data['sensor'][sensor] = get_req(session,f"https://api-samenmeten.rivm.nl/v1.0/Datastreams({json_data['available_streams'][sensor]})/Sensor").json()['name']
        except:
            json_data['sensor'][sensor] = 'null'

    if data_sources == {}:
        json_data['has_stream'] = 'False'
        json_data['has_data'] = 'False'
    else:
        json_data['has_stream'] = 'True'



    total_data = pd.DataFrame()
    for source in data_sources:
        source_req = get_req(session,data_sources[source])
        if source_req.status_code != 200:
            print('datastream available, data source observations not available in station iot id: ', iot_id)
        else:
            if source_req.json()['value'] == []:
                print('datastream available, no data present in station iot id: ', iot_id)
                continue
            else:
                print(f'id:{iot_id} data source {source} is avialable')
                nextlink = data_sources[source]
                source_data = []
                while(nextlink):
                    req_counter = 0
                    req = get_req(session,nextlink)
                    if req.status_code != 200:
                        if req_counter >20:
                            nextlink = None
                        else:
                            req_counter +=1
                            continue
                    time.sleep(0.5)
                    data, nextlink = get_page(req)
                    source_data.extend(data)
                if total_data.empty:
                    total_data[['time',source]] = source_data
                    total_data['time'] = pd.to_datetime(total_data['time']).apply(lambda x: int(x.timestamp()))
                    total_data = total_data.drop_duplicates(subset='time',keep='first')
                    #THIS IS NOT GMT TIME, NEED TO READJUST
                else:
                    dum_source_data = pd.DataFrame(source_data, columns=['time',source])
                    dum_source_data['time'] = pd.to_datetime(dum_source_data['time']).apply(lambda x: int(x.timestamp()))
                    dum_source_data = dum_source_data.drop_duplicates(subset='time',keep='first')
                    total_data = pd.merge(total_data, dum_source_data, on='time',how='outer')
                    del dum_source_data
                del source_data

    if total_data.empty:
        json_data['has_data'] = 'False'
    else:
        json_data['has_data'] = 'True'
        csv_path = os.path.join(station_dir, f'{station_name}.csv')
        dump_csv(total_data, csv_path)

    json_path = os.path.join(station_dir, f'{station_name}.json')
    dump_json(json_data, json_path)
    print(f'Total time so far: {math.floor((time.time() - start_time)/60)} m {(time.time() - start_time)%60} s')


    del things_req, data_sources, things_req_parsed,station_name, datastreams_link, locations_link,
    station_dir,locations_req, lon, lat, json_data, json_path, datastreams_req, total_data
