# Air Quality Sensor Data Repository (AQ-SDR)
If you are using this dataset for the Veli model, make sure to check the other repository for the model code and running at: [Veli](https://github.com/YahiDar/Veli).

Also, please do cite our paper using:

```
@misc{Yahia2025Veli,
      title={Veli: Unsupervised Method and Unified Benchmark for Low-Cost Air Quality Sensor Correction}, 
      author={Yahia Dalbah and Marcel Worring and Yen-Chia Hsu},
      year={2025},
      eprint={2508.02724},
      archivePrefix={arXiv},
      primaryClass={eess.SP},
      url={https://arxiv.org/abs/2508.02724}, 
}
```


This repository holds the code used to pull data, organize, clean, and preprocess from the following sources:

- [KNMI](https://www.daggegevens.knmi.nl/)
- [Samenmeten](https://api-samenmeten.rivm.nl/v1.0/Things)
- [luchtmeetnet, API version](https://api2020.luchtmeetnet.nl/open_api/stations)
- [luchtmeetnet, verified](https://data.rivm.nl/data/luchtmeetnet/)
- [Sensor Community](https://archive.sensor.community/)
- [Location Aware Sensor System - Taiwan](https://lass-net.org/)
- [Ministry of Environment - Taiwan](https://data.moenv.gov.tw/en/)


Luchtmeetnet API is the one available to pull for the public. The verified version is the one verified by the government and reported to the European Union. For the use as a reference data, we highly recommend you use the official verified version.

We also provide a large chunk of the raw data provided through the following link:

# Download
[Download the dataset from figshare](https://uvaauas.figshare.com/articles/dataset/AQ-SDR_Dataset/30177886?file=58130851)

---

At the end of this readme file, you will see a description of the dataset tools and some explanation. Note that you do not need to add anything to the scripts in the folders `data_requests_scripts` and `preprocessing_scripts`, they are made available for you and you are welcome to explore them :)!

The bash script will produce a dataset ready for running through the following directory trees:

EU Data:

```
final_dir_eudata
├── crowd_stations_root_dbscan
├── data
├── KNMI
├── luchtmeetnet_csvs
├── luchtmeetnet_csvs_dbscan
├── lucht_root_dbscan
├── metadata
├── sencom_final_root_dbscan
└── final_dataset
   ├── prepared_lcs_bulk
   └── pre_prepared_datasets_unfiltered


```
Taiwan Data:
```
final_dir_ood
├── downloaded_lcs
├── downloaded_ref
├── lcs_data_dbscan
├── metadata
├── ref_data_dbscan
└── final_dataset
    ├── ood_data_bulk
    └── prepared_ood_datasets

```
For every data source, aside from the final thing used to train/test Veli, the folder is goin to contain data of the following shape:

```
source_name
└── sensor_name_id
    ├── sensor_name_id.csv
    └── sensor_name_id.json

```
The `csv` file contains the actual data with time column as epoch time. The metadata is all stored in the `JSON` file.

# Environment Setup

All packages and dependencies used are available via two options:
- `requirements.txt`
- `pyproject.toml` (Poetry)

This guide assumes you are using a bash-based tool (linux/mac). These are the exact same instructions and packaging files as the ones in the [Veli](https://github.com/YahiDar/Veli) repository.
You can install all necessary packages **EXACTLY** following our work using the following commands:




## 1. Using Python Virtual Environment
We recommend using approach (a) because it is the easiest and fastest. For the highest gaurantee of reproducability, approach (b) is recommended but unnecessary. (c) is untested but easy as well.

### a) With `requirements.txt`
```bash
# Create and activate a virtual environment
python3 -m venv veli
source veli/bin/activate   # On Windows: veli\Scripts\activate
pip install -r requirements.txt
```

### b) With `poetry.toml`
Install poetry if not installed (feel free to create a virtual environment beforehand)
```bash
pip install poetry
```

Create and activate the virtual environment + install deps. Also activate the shell.
```bash
poetry install

source $(poetry env info --path)/bin/activate
```
The source file will automatically start the virtual environment Alternatively, you can do `poetry env list --full-path` and activate the environment in there.

### c) Using Conda

```bash
conda create -n veli python=3.10

conda activate veli

pip install -r requirements.txt
```
## Preprocessing

To abide by the licensing provided by each data source, we provide the raw data through the figshare link posted above. 

Due to the licesning, we cannot publish the processed data. 
These scripts do:
- Reorganize the data
- Resample the data hourly
- Create metadata
- Apply DBSCAN on all files to ensure validity
- Create a complete metadata (available as a solo json file in the `/metadata/` folder)
- Creates the dataloaders required for the Veli model


### Running the Bash Script:

We provide a collection of Python scripts that does all required preprocessing for this dataset. You only need to run the ```run_data_preperation.sh``` shell file to run all these scripts.

The script will take a long time, upwards of 10 hours to prepare ALL the data. you will need at least 32 GB of RAM and a total of 75 GB of storage.

The bash scripts run the two python files `prepare_all_data.py` which prepares the data for the EU region (in-distribution), and `prepare_taiwan_data.py` which prepares the data for the Taiwanese region (out-of-distribution).
The python scripts are modular but I set the variables internally. Feel free to change them and play with them as you wish. I will however not be addressing issues in regards to parameters that I have not supported :)!

It will create a log file in this directory called `run_data_preperation.log`.

These are sample arguments for the python scripts:

### EU data


```bash
python -u prepare_all_data.py  --eu_data "/path/to/eu_data"  --final_dir "/path/to/final/data" --dummy_holder "/path/to/dummy_holder" 
  
```
The path to eu_data should contain the following directories:

```
required_subdirs = [
    "crowd_stations_root",
    "KNMI",
    "luchtmeetnet_csvs",
    "lucht_root",
    "sencom_hourly"
]
```

This will automatically delete the 'dummy_holder' directory after you are done since it is not needed. If you wish to observe the whole process of preprocessing, feel free to activate the argument `--keep_dummy` which will not delete them. NOTE: this requires an additional 100GB of storage.

### Taiwan data
```bash
python -u prepare_taiwan_data.py --operation_root "/path/to/taiwan_raw_downloaded/" --final_root "/path/to/final_dir_ood" 
```
The path to taiwan data should contain the following directories:

```
required_subdirs = [
    "downloaded_ref",
    "downloaded_lcs"
]
```

Similar to EU data. Additionally, you can activiate the argument `--keep_dummy` to keep the dummy folders.

## Dealing with Null/Missing values:

As expected in any IoT based system, there are a lot of missing/null values due to a plethora of reasons (connection issues, misreadings ... etc). The following is a chart of how these data were handled at every case. Training/testing refers to the process in the modeling in our model, [Veli](https://github.com/YahiDar/Veli).

**Definitions**

**LCS: Low-cost sensor**

**Ref: Reference (high cost accurate sensors)**

**Focus variable: PM2.5**



**1- Pulling and data requests**

- Metadata:

Fixed format of json keys, check if they are there, whatever is missing replace with -999 and later replaced with Null
- Sensor streams:

Pull whatever is present.
If the data is not hourly, downsample it by the hour (average)
If all components are empty for this hour, the whole time slot is dropped 
If at least one component is present, keep it and add ‘NaN’ to the rest.

**2- Preprocessing**

* Creating the stream files

- Metadata:
    - Drop any stream that has no geolocation
    - Specific to SamenMeten: If a stream has different geolocations - it was probably moved and redeployed => segment the data into different locations

- Sensor streams:
    - If a reading is outside of predefined ranges (sample below), they are replaced with null
    - To avoid erratic sensor spikes, a very soft DBSCAN is applied (if values suddenly increase or decrease by a large margin too quickly then it is discarded)
    - After all filtering, If more than 35% of year hours (0.35*8760) is missing, the whole year is dropped (data is still available, just not used in the final model)

* Create the model subset

The model subset is only in the Netherlands and Taiwan, and looked at collection of 10 sensors in a 5km radius. The filtering is done as follows:

- Find all locations that have at least 10 sensors that has at least 1 year of LCS data (100 in NL, 50~ in Taiwan)
- Pre-define locations that have also Ref stations that can be used for verifying (7 in NL, 12~ in Taiwan)
- It is possible that a location has more than 10 sensors and 1 year of data, in which case we choose the 10 sensors that have highest alignment in time (basically most amount of data possible per region). Per time sample, there must be at least 5 sensors active. (so maximum allowed is 5 NA’s at any time).
- For reference data, the requirement is at least one available reading (assumption here is that they are all accurate reference stations so one is enough).

The result is 100 files (locations, files are labeled by name) for NL, each has 10 sensors with at least 1 year of data (with at least 65% hourly coverage).


**3- Training**

- Since there are up to 5 sensors per hour that have NA, they are replaced with a mask of an impossible value (changable, but we set it to 0. We experimented with -1, -999 …, had no effect).
- We also have a binary mask accompanying every slice in time, 0 for NA, 1 for present.
- Every slice of time is a tensor [B,2,10] instead of [B,1,10], where B is batch size.

**4- Testing**

- The ‘infer_to_dataframe’ function generates predictions as dataframe. The predictions are generated for every sensor, INCLUDING the NA one. However, these reading are ‘invalid’, so the binary mask is an indicator to discard them. You are welcome to fiddle with them and do analysis on them :)
- The errors are calculated ONLY for the non-NAN values in both the reference and LCS arrays (i.e. only when there are available readings for both). 
- This is an experimental thing, but we also have a fill_hour_rows argument that tells the model to bring back the hours that were dropped because all sensors are NA. This will generate predictions based on its location in time from zero information. Again, we do not claim that this works, but you are welcome to experiment with this.


Ranges of feasibility:
``` 
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
```

## Final result
After runnin the bash script, you will get the a directory with the following tree:

EU Data:

```
final_dir_eudata
├── crowd_stations_root_dbscan
├── data
├── KNMI
├── luchtmeetnet_csvs
├── luchtmeetnet_csvs_dbscan
├── lucht_root_dbscan
├── metadata
├── sencom_final_root_dbscan
└── final_dataset
   ├── prepared_lcs_bulk
   └── pre_prepared_datasets_unfiltered

```
`final_dataset` contains the data that we used in modeling Veli.
`prepared_lcs_bulk` contains the LCS data without reference station data for unsupervised training.
`pre_prepared_datasets_unfiltered` contains files with reference stations used for verification purposes.

OOD Data:

```
final_dir_ood
├── lcs_data_dbscan
├── metadata
├── ref_data_dbscan
└── final_dataset
    ├── ood_data_bulk
    └── prepared_ood_datasets

```
`final_dataset` contains the data that we used in modeling Veli.
`ood_data_bulk` contains the LCS data without reference station data for unsupervised training.
`prepared_ood_datasets` contains files with reference stations used for verification purposes.


## utils

General files to support the main scripts.

## KNMI

Scripts: Data requests `data_requests_knmi.py`.

Pulls the data and reorganizes it in the same file. The data is verified and pulled from reliable weather stations, so no preprocessing is done.


## Samenmeten

Scripts: Data requests `data_requests_samenmeten.py`, Data preprocessing `preprocess_samenmeten.py`, and geo-location fixing `fix_coordinates_samenmeten.py`

The data has 'historical locations' for certain sensors - implying mobility. Sometimes this is a gps error in the decimals, which is disregarded. Other times it is significant (larger than 2km movement), so every station with larger separation like this is split into multiple stations based on the duration it spends there. Any station with multiple (more than 5) movements is disregarded (very few stations, less than 20)

## Luchtmeetnet
There are two variants of these data - the api version and the csv files version. The CSV are confirmed and verified by the publishing entity (Amsterdam Government) and is used to report to the European Union, hence it is the highest level of accuracy available to us.

### API Version

Scripts: Data reorganization ```data_requests_luchtmeetnet_api.py```, Data preprocessing (not implemented yet) `preprocess_luchtmeetnet_api.py`


Pulls the data and reorganizes it in the same file. Slow and incomplete - still have not implemented preprocessing since pulling is not over.

### Verified Version

Scripts: Data reorganization `organize_luchtmeetnet_verified.py`, Data preprocessing `preprocess_luchtmeetnet_verified.py`

You can download the data separately - no script to be provided here.

Reorganizes the data since it comes in an extremely weird format. The data is verified and pulled from reliable weather stations, but there were noticeable error so preprocessing with loose constrainst are implemented.

## Sensor Community (SenCom)

Scripts: Data requests `data_requests_sencom.py`, Data preprocessing `preprocess_sencom.py`

Very large dataset, pulled and limited only to Netherlands, Belgium, and Germany. More than 2 TB of data.


## Out of Distribution data (Taiwan)
All out of distribution data was downloaded from [here](https://history.colife.org.tw/#/).

We provide the identical files in our comprehensive dataset with no code to pull them through any API.

# Licenses
The source code in this repository is under the MIT license. The data itself is **NOT**.

Each data source has a different license. Please make sure you are using the data appropriately as requested by the original provided.

KNMI Data (folder name: /EU_data/KNMI):

The original license is CC BY 4.0

as documented on their webpage: https://www.knmidata.nl/open-data


LuchtMeetNet data (folder names: /EU_data/lucht_root and /EU_data/luchtmeetnet_csvs):

The original license is CC BY-ND 4.0

as documented on their webpage: https://www.luchtmeetnet.nl/informatie/download-data/open-data


RIVM SamenMeten data (folder name: /EU_data/crowd_stations_root):

The original license is

as documented on their webpage:


Sensor.Community data (folder name: /EU_data/sencom_hourly):

The original license is DbCL v1.0

as documented on their webpage: https://sensor.community/nl/


Taiwan Ministry of Environment data (folder name: /out_of_distribution_downloaded/downloaded_ref):

The original license is The Open Government Data License, version 1.0

as documented on their webpage: https://data.gov.tw/license


PM2.5 Open Data Portal - LASS (folder name: /out_of_distribution_downloaded/downloaded_lcs):

The original license is CC BY-NC-SA 4.0

as documented on their webpage: https://pm25.lass-net.org/

# Acknowledgement

We sincerely thank the Dutch government for supporting this research with the starter grant (startersbeurzen). We also thank the organizations and researchers who provide the open data to enable this research, including the Dutch National Institute for Public Health and the Environment (RIVM), the Dutch Royal Netherlands Meteorological Institute (KNMI), Dr. Ling-Jyh Chen in Taiwan Academia Sinica for the AirBox project, the Taiwan Ministry of Environment, the Sensor.Community platform, and the European Environmental Agency (EEA). We also thank the GGD Amsterdam and RIVM for providing information about how air quality sensor stations work in the Netherlands. We also thank the CREATE Lab at the Robotics Institute at Carnegie Mellon University for the technical support in building the air quality dashboard.