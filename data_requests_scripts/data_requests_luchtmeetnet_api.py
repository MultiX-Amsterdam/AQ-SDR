'''
Code to pull data from luchtmeetnet 'https://api2020.luchtmeetnet.nl/open_api/stations'
Not updated - feel free to use it but don't rely on it being 100% up to date.

define the root:
'''

lucht_root = '/dum/dum/dum/lucht_root/'


station_names = [{'number': 'NL01491', 'location': 'Overschie-A13'},
 {'number': 'NL01497', 'location': 'Rotterdam-Maasvlakte'},
 {'number': 'NL01496', 'location': 'Rotterdam-HvHolland'},
 {'number': 'NL01912', 'location': 'Ridderkerk-Voorweg'},
 {'number': 'NL49557', 'location': 'Wijk aan Zee-Bosweg'},
 {'number': 'NL10248', 'location': 'Nistelrode-Gagelstraat'},
 {'number': 'NL50013', 'location': 'Meerssen- Beekerweg'},
 {'number': 'NL50012', 'location': 'Eijsden-Trichterweg'},
 {'number': 'NL01485', 'location': 'Rotterdam-Hoogvliet'},
 {'number': 'NL01489', 'location': 'Ridderkerk-A16'},
 {'number': 'NL49701', 'location': 'Zaandam-Wagenschotpad'},
 {'number': 'NL10320', 'location': 'Burgh-Haamstede'},
 {'number': 'NL53016', 'location': 'Zevenbergen-Galgenweg'},
 {'number': 'NL10404', 'location': 'Den Haag-Rebecquestraat'},
 {'number': 'NL10445', 'location': 'Den Haag-Amsterdamse Veerkade'},
 {'number': 'NL10246', 'location': 'Fijnaart-Zwingelspaansedijk'},
 {'number': 'NL49002', 'location': 'Amsterdam-Haarlemmerweg'},
 {'number': 'NL49007', 'location': 'Amsterdam-Einsteinweg'},
 {'number': 'NL49014', 'location': 'Amsterdam-Vondelpark'},
 {'number': 'NL49016', 'location': 'Amsterdam-Westerpark'},
 {'number': 'NL49017', 'location': 'Amsterdam-Stadhouderskade'},
 {'number': 'NL49019', 'location': 'Amsterdam-Oude Schans'},
 {'number': 'NL49020', 'location': 'Amsterdam-Jan van Galenstraat'},
 {'number': 'NL49021', 'location': 'Amsterdam -Kantershof'},
 {'number': 'NL53001', 'location': 'Ossendrecht-Burgemeester Voetenstraat'},
 {'number': 'NL49003', 'location': 'Amsterdam-Nieuwendammerdijk'},
 {'number': 'NL53020', 'location': 'Strijensas Buitendijk'},
 {'number': 'NL10301', 'location': 'Zierikzee-Lange Slikweg'},
 {'number': 'NL10938', 'location': 'Groningen-Nijensteinheerd'},
 {'number': 'NL53004', 'location': 'Moerdijk-Julianastraat'},
 {'number': 'NL50002', 'location': 'Geleen-Vouershof '},
 {'number': 'NL50010', 'location': 'Maastricht-A2-Philipsweg'},
 {'number': 'NL01484', 'location': 'Rotterdam-Geulhaven'},
 {'number': 'NL10107', 'location': 'Posterholt-Vlodropperweg'},
 {'number': 'NL10722', 'location': 'Eibergen-Lintveldseweg'},
 {'number': 'NL50007', 'location': 'Maastricht-Hoge_Fronten'},
 {'number': 'NL10929', 'location': 'Valthermond-Noorderdiep'},
 {'number': 'NL10617', 'location': 'Biddinghuizen-Kuilweg'},
 {'number': 'NL10538', 'location': 'Wieringerwerf-Medemblikkerweg'},
 {'number': 'NL10741', 'location': 'Nijmegen-Graafseweg'},
 {'number': 'NL10738', 'location': 'Wekerom-Riemterdijk'},
 {'number': 'NL10138', 'location': 'Heerlen-Jamboreepad'},
 {'number': 'NL10133', 'location': 'Wijnandsrade-Opfergeltstraat'},
 {'number': 'NL10131', 'location': 'Vredepeel-Vredeweg'},
 {'number': 'NL10235', 'location': 'Huijbergen-Vennekenstraat'},
 {'number': 'NL10818', 'location': 'Barsbeek-De Veenen'},
 {'number': 'NL01493', 'location': 'Rotterdam-Statenweg'},
 {'number': 'NL50004', 'location': 'Maastricht-A2-Nassaulaan'},
 {'number': 'NL01494', 'location': 'Schiedam-A.Arienstraat'},
 {'number': 'NL50011', 'location': 'Nederweert-Kuilstraat'},
 {'number': 'NL54010', 'location': 'Arnhem GelreDome'},
 {'number': 'NL54004', 'location': 'Arnhem Velperbroek'},
 {'number': 'NL10230', 'location': 'Biest Houtakker-Biestsestraat'},
 {'number': 'NL10442', 'location': 'Dordrecht-Bamendaweg'},
 {'number': 'NL10236', 'location': 'Eindhoven-Genovevalaan'},
 {'number': 'NL10237', 'location': 'Eindhoven-Noordbrabantlaan'},
 {'number': 'NL10247', 'location': 'Veldhoven-Europalaan'},
 {'number': 'NL10550', 'location': 'Haarlem-Schipholweg'},
 {'number': 'NL49561', 'location': 'Badhoevedorp-Sloterweg'},
 {'number': 'NL49565', 'location': 'Oude Meer-Aalsmeerderdijk'},
 {'number': 'NL10641', 'location': 'Breukelen-A2'},
 {'number': 'NL10807', 'location': 'Hellendoorn-Luttenbergerweg'},
 {'number': 'NL10633', 'location': 'Zegveld-Oude Meije'},
 {'number': 'NL10636', 'location': 'Utrecht-Kardinaal de Jongweg'},
 {'number': 'NL10318', 'location': 'Philippine-Stelleweg'},
 {'number': 'NL10643', 'location': 'Utrecht-Griftpark'},
 {'number': 'NL10437', 'location': 'Westmaas-Groeneweg'},
 {'number': 'NL10241', 'location': 'Breda-Bastenakenstraat'},
 {'number': 'NL49012', 'location': 'Amsterdam-Van Diemenstraat'},
 {'number': 'NL49553', 'location': 'Wijk aan Zee-De Banjaert'},
 {'number': 'NL49572', 'location': 'Velsen-Staalstraat'},
 {'number': 'NL49703', 'location': 'Spaarnwoude-Machineweg'},
 {'number': 'NL49556', 'location': 'De Rijp-Oostdijkje'},
 {'number': 'NL49546', 'location': 'Zaanstad-Hemkade'},
 {'number': 'NL49022', 'location': 'Amsterdam-Ookmeer'},
 {'number': 'NL10446', 'location': 'Den Haag-Bleriotlaan'},
 {'number': 'NL10644', 'location': 'Cabauw-Wielsekade'},
 {'number': 'NL10918', 'location': 'Balk-Trophornsterweg'},
 {'number': 'NL49704', 'location': 'Zaanstad-Hoogtij'},
 {'number': 'NL10418', 'location': 'Rotterdam-Schiedamsevest'},
 {'number': 'NL10937', 'location': 'Groningen-Europaweg'},
 {'number': 'NL10136', 'location': 'Heerlen-Looierstraat'},
 {'number': 'NL10240', 'location': 'Breda-Tilburgseweg'},
 {'number': 'NL10742', 'location': 'Nijmegen-Ruyterstraat'},
 {'number': 'NL10821', 'location': 'Enschede-Winkelshorst'},
 {'number': 'NL49551', 'location': 'IJmuiden-Kanaalstraat'},
 {'number': 'NL49570', 'location': 'Beverwijk-Creutzberglaan'},
 {'number': 'NL49564', 'location': 'Hoofddorp-Hoofdweg'},
 {'number': 'NL49573', 'location': 'Velsen-Reyndersweg'},
 {'number': 'NL10639', 'location': 'Utrecht-Constant Erzeijstraat'},
 {'number': 'NL10444', 'location': 'De Zilk-Vogelaarsdreef'},
 {'number': 'NL53015', 'location': 'Klundert-Kerkweg'},
 {'number': 'NL01487', 'location': 'Rotterdam-Pleinweg'},
 {'number': 'NL01488', 'location': 'Rotterdam-Zwartewaalstraat'},
 {'number': 'NL01495', 'location': 'Maassluis-Kwartellaan'},
 {'number': 'NL10449', 'location': 'Vlaardingen-Riouwlaan'},
 {'number': 'NL10450', 'location': 'Den Haag-Neherkade'},
 {'number': 'NL10934', 'location': 'Kollumerwaard-Hooge Zuidwal'},
 {'number': 'NL49680', 'location': 'Almere-Boomgaardweg'},
 {'number': 'NL01913', 'location': 'Sluiskil-Stroodorpestraat'},
 {'number': 'NL50003', 'location': 'Geleen-Asterstraat'}]


import requests
import time
import datetime
import pandas as pd
import os
import json
import math
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import aiohttp
import asyncio
import time
import random
import datetime
from datetime import datetime

session = requests.Session()

retry = Retry(connect=3, backoff_factor =0.5)
adapter = HTTPAdapter(max_retries = retry)
session.mount('http://',adapter)
session.mount('https://', adapter)

page_start = 100
page_final = 500
skipped_pages = {}

MAX_REQS = 300
MAX_TIME_ELAPSED = 300

def health_check(req_nums, time_start):
    req_nums += 1
    span = time.time() - time_start

    if req_nums > 80 and req_nums/span > 3:
        print(f'pausing for {(req_nums-span)+30} seconds to avoid a timeout')
        time.sleep((req_nums-span)+30)
        return 0, time.time()

    if req_nums > 250:
        if (span) > 290:
            print(f'{req_nums} in >290 secs, no need to pause')
        else:
            print(f'pausing for {310-span} seconds to avoid a timeout')
            time.sleep(310-span)
        return 0, time.time()
    else:
        return req_nums, time_start



# def health_check(req_nums, time_start):
#     req_nums += 1
#     time_elapsed = time.time()-time_start

#     if req_nums > 145 and req_nums > time_elapsed:
#         print(f'Calls too fast. {req_nums} calls in {time_elapsed}s - pausing for {20+(req_nums - math.floor(time_elapsed))}s.')
#         time.sleep(20+(req_nums - math.floor(time_elapsed)))
#         return 0, time.time()
#     elif req_nums > 50 and req_nums/time_elapsed > 2:
#         print(f'Calls too fast. {req_nums} calls in {time_elapsed}s - pausing for {20}s.')
#         time.sleep(20)
#         return 0, time.time()
#     else:
#         return req_nums, time_start
    
def get_req(session, url):

    req = session.get(url)

    if req.status_code == 200:
        # print('successfully pulled, ', url)
        return req
    elif req.status_code == 429:
        print('Request limit, pausing for 5 minutes.')
        print('time now:', datetime.now())
        time.sleep(300)
        looper = True
        while(looper):
            time.sleep(300)
            req = session.get(url)
            if req.status_code != 429:
                looper == False
                print('Stopping pause, time now:', datetime.now())
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
    page_data = []
    if 'data' in req.json().keys():
        for values in req.json()['data']:
            page_data.append([values['timestamp_measured'],values['value']])
        return page_data
    else:
        print(f'Skipping {req.json()} because no data.')
        return []
    

component_units = {
    'SO2': 'µg/m3',
    'PM25': 'µg/m3',
    'PM10': 'µg/m3',
    'Ox': 'ppb',
    'O3': 'µg/m3',
    'BC': 'µg/m3',
    'CO': 'µg/m3',
    'H2S': 'µg/m3',
    'NH3': 'µg/m3',
    'NO2': 'µg/m3',
    'NO': 'µg/m3',
    'NOx': 'µg/m3',
    'BTX': 'µg/m3',
    'HC Aerosol': 'µg/m3',
    'HC Regenwater': 'µmol/L',
    'Koolstof aerosol': 'µg/m3',
    'Lindane regenwater': 'µmol/L',
    'PAK Aerosol': 'ng/m3',
    'ZM Aerosol': 'ng/m3',
    'ZM Regenwater': 'µmol/L',
    'ZVOC': 'ng/m3',
    'VOC': 'µg/m3',
    'Kwik Regenwater': 'mm'
}
component_units = {k: v.replace('µ', 'u') for k, v in component_units.items()}

full_start_time = time.time()
skipped_stations =[]
req_nums = 0
time_start = time.time()
for station in station_names:
    station_name = station['number']
    station_dir = os.path.join(lucht_root,station_name)
    json_path = os.path.join(station_dir, f'{station_name}.json')
    csv_path = os.path.join(station_dir, f'{station_name}.csv')

    os.makedirs(station_dir, exist_ok=True)

    station_url = f'https://api2020.luchtmeetnet.nl/open_api/stations/{station_name}'
    station_req = get_req(session,station_url)
    print(f'pulling station info: {station_url}')
    req_nums, time_start = health_check(req_nums, time_start)
    if station_req.status_code != 200:
        skipped_stations.append(station)
        print(f'Skipping station {station_name}')
        continue
    else:
        json_data = {
        "type": 'official_unval',
        'longitude': station_req.json()['data']['geometry']['coordinates'][0],
        'latitude': station_req.json()['data']['geometry']['coordinates'][1],
        'organisation': station_req.json()['data']['organisation'],
        'location': station_req.json()['data']['location'],
        'year_start': station_req.json()['data']['year_start'],
        'municipality': station_req.json()['data']['municipality'],
        'locality_type': station_req.json()['data']['type'],
        'datastreams_links': f'https://api2020.luchtmeetnet.nl/open_api/stations/{station["number"]}'
}
        components = station_req.json()['data']['components']
        json_data['stream_units']={}
        for component in components:
            if component in component_units:
                json_data['stream_units'][component] = component_units[component]
            elif 'C6' or 'C7' or 'C8' in component:
                json_data['stream_units'][component] = 'ug/m3'
            else:
                json_data['stream_units'][component] = 'null' 
        data_check = get_req(session,f'https://api2020.luchtmeetnet.nl/open_api/stations/{station_name}/measurements')
        print(f'Verifying availability of data in: https://api2020.luchtmeetnet.nl/open_api/stations/{station_name}/measurements')        
        req_nums, time_start = health_check(req_nums, time_start)
        try:
            if data_check.json()['data'] == []:
                json_data['has_data'] = 'False'
            else:
                json_data['has_data'] = 'True'
        except:
            print(f'{station_name} response error code, could not verified if theres data, skipping to next station')
            skipped_stations.append(station)
            continue
        total_data = pd.DataFrame() 
        for component in components:
            total_component_data = []
            page = 1
            component_url = f'https://api2020.luchtmeetnet.nl/open_api/stations/{station_name}/measurements?formula={component}&page={page}'  
            page_req = get_req(session,component_url)             
            req_nums, time_start = health_check(req_nums, time_start)
            req_check = 0
            lastpage = 900
            if page_req.status_code != 200:
                while(page_req.status_code != 200):
                    page_req = get_req(session,component_url)             
                    req_nums, time_start = health_check(req_nums, time_start)
                    req_check += 1
                    if req_check == 20:
                        break
                    time.sleep(10)
            if page_req.status_code == 200:
                if page_req.json()['pagination']['last_page'] < lastpage:
                    lastpage = page_req.json()['pagination']['last_page']
            if lastpage == 0:
                continue
            print(f'last page for this component is: {lastpage}')
            while(page != lastpage):
                component_url = f'https://api2020.luchtmeetnet.nl/open_api/stations/{station_name}/measurements?formula={component}&page={page}'  
                page_req = get_req(session,component_url)             
                req_nums, time_start = health_check(req_nums, time_start)
                print(f'pulling from: {component_url}')
                if page_req.status_code != 200:
                    page_req = get_req(session,component_url)
                    req_nums, time_start = health_check(req_nums, time_start) 
                if page_req.status_code !=200: 
                    print(f'Skipping page {page} in station {station_name} in component {component}')
                    page+=1
                    continue
                if page == page_req.json()['pagination']['last_page']:
                    lastpage = True
                else:
                    page+=1
                total_component_data.extend(get_page(page_req))
                del page_req
            if total_data.empty:
                total_data[['time',component]] = total_component_data
                total_data['time'] = pd.to_datetime(total_data['time']).apply(lambda x: int(x.timestamp()))
                total_data = total_data.drop_duplicates(subset='time',keep='first')
                #api is in gmt?
            else:
                dum_component_data = pd.DataFrame(total_component_data, columns=['time',component])
                dum_component_data['time'] = pd.to_datetime(dum_component_data['time']).apply(lambda x: int(x.timestamp()))        
                dum_component_data = dum_component_data.drop_duplicates(subset='time',keep='first')
                total_data = pd.merge(total_data, dum_component_data, on='time',how='outer')
                del dum_component_data
            del total_component_data

        if total_data.empty:
            json_data['has_data'] = 'False'
        else:
            dump_csv(total_data,csv_path)
            json_data['has_data'] = 'True'
        
        print(f'Total time so far: {math.floor((time.time() - full_start_time)/60)} m {(time.time() - full_start_time)%60} s')
        json_data['available_streams'] = list(total_data.columns[1:])
        dump_json(json_data, json_path)

        del data_check,total_data, json_data

            
     
            
    



