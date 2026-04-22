import json
import shutil
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.prepared import prep
#source folder
SRC_DIR = Path("/data/env/data3")
#new folder
DST_DIR = Path("/data/env/data4")

#Path that contains geojson that has boundaries. it is in this 
GEOJSON_PATH = Path("../utils/NLBLGER_JSON.geojson")


def load_netherlands_polygon(geojson_path):
    with open(geojson_path, "r") as f:
        gj = json.load(f)
    for feature in gj["features"]:
        props = feature.get("properties", {})
        if props.get("ISO3") == "NLD" or props.get("NAME") == "Netherlands":
            return shape(feature["geometry"])
    raise ValueError("Netherlands feature not found in geojson")


def main():
    nl_polygon = prep(load_netherlands_polygon(GEOJSON_PATH))

    DST_DIR.mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped = 0
    outside = 0

    for folder in sorted(SRC_DIR.iterdir()):
        if not folder.is_dir():
            continue
        json_path = folder / f"{folder.name}.json"
        if not json_path.exists():
            skipped += 1
            continue

        try:
            with open(json_path, "r") as f:
                data = json.load(f)
            lon = float(data["longitude"])
            lat = float(data["latitude"])
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            print(f"skip {folder.name}: {e}")
            skipped += 1
            continue

        if nl_polygon.contains(Point(lon, lat)):
            dst = DST_DIR / folder.name
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(folder, dst)
            copied += 1
            print(f"copied {folder.name} ({lon}, {lat})")
        else:
            outside += 1

    print(f"\ndone. copied={copied} outside={outside} skipped={skipped}")


if __name__ == "__main__":
    main()
