import os
import shutil
import pandas as pd


'''

Merge new station data into the existing data3 directory.

Run this after you have downloaded new data

Usage:
  python data_requests_scripts/merge_data.py

  - Update SRC and DST paths below if your directories differ.
  - Consider backing up DST before running, as CSV files in DST will be overwritten in case 3.


This script merges air quality station data from a source directory (SRC: /home/ssda/new_data/)
into a destination directory (DST: /data/env/data3/).
Both directories contain station folders (e.g. AM_pm010/), each holding a CSV and JSON file
named after the station (e.g. AM_pm010.csv, AM_pm010.json). The CSV files contain a 'time'
column in epoch format.


expected tree directory for the source:
/home/ssda/new_data/
                    NL104314/
                            NL104314.csv
                            NL104314.json
                    AMF531531/
                            AMF531531.csv
                            AMF531531.json
                    some_new_station/
                            some_new_station.csv
                            some_new_station.json
                    .
                    .
                    .

(some_new_station is not a gaurantee, it depends on whether you pulled it or not)


expected tree directory for the destination:
/home/ssda/data3/
                    NL104314/
                            NL104314.csv
                            NL104314.json
                    AMF531531/
                            AMF531531.csv
                            AMF531531.json
                    .
                    .
                    .


The script handles three cases:
  1. Station exists only in SRC        -> entire folder is copied to DST.
  2. Station exists in both, but DST
     folder has no CSV file            -> CSV (and JSON if missing) are copied into DST.
  3. Station exists in both with CSVs  -> rows from SRC with time > max time in DST are
                                          appended. New columns from SRC are also added
                                          (with NA for existing rows). The merged result
                                          overwrites the DST CSV.

'''

SRC = "/home/ssda/new_data/"
DST = "/data/env/data3/"

src_stations = {d for d in os.listdir(SRC) if os.path.isdir(os.path.join(SRC, d))}
dst_stations = {d for d in os.listdir(DST) if os.path.isdir(os.path.join(DST, d))}

for station in sorted(src_stations):
    src_dir = os.path.join(SRC, station)
    dst_dir = os.path.join(DST, station)

    # Case 1: station only in new_data -> copy entire folder
    if station not in dst_stations:
        print(f"[COPY NEW] {station}")
        shutil.copytree(src_dir, dst_dir)
        continue

    src_csv = os.path.join(src_dir, f"{station}.csv")
    dst_csv = os.path.join(dst_dir, f"{station}.csv")

    # Case 2: station exists in both but data3 has no csv -> copy csv (and json if present)
    if not os.path.exists(dst_csv):
        if os.path.exists(src_csv):
            print(f"[COPY CSV] {station}")
            shutil.copy2(src_csv, dst_csv)
            # Also copy json if it exists in source but not in dest
            src_json = os.path.join(src_dir, f"{station}.json")
            dst_json = os.path.join(dst_dir, f"{station}.json")
            if os.path.exists(src_json) and not os.path.exists(dst_json):
                shutil.copy2(src_json, dst_json)
        continue

    # Case 3: both have csv -> append new rows by time column
    if os.path.exists(src_csv):
        print(f"[MERGE]    {station}", end="")
        df_dst = pd.read_csv(dst_csv)
        df_src = pd.read_csv(src_csv)

        # Find the time column (could be 'time', 'epoch', etc.)
        time_col = 'time'
        if time_col not in df_dst.columns:
            # Fallback: use first column
            print(f'[ERROR] time column not present in {station}')
            continue

        max_time = df_dst[time_col].max()
        new_rows = df_src[df_src[time_col] > max_time]

        # Handle new columns from src that don't exist in dst
        new_cols = [c for c in df_src.columns if c not in df_dst.columns]
        if new_cols:
            for c in new_cols:
                df_dst[c] = pd.NA
            # Also need those columns in new_rows (they already have them from df_src)

        merged = pd.concat([df_dst, new_rows], ignore_index=True)
        merged.to_csv(dst_csv, index=False)
        print(f" -> added {len(new_rows)} rows, {len(new_cols)} new columns")

print("Done.")
