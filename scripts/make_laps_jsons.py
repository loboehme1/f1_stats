import requests
import time
import json
import os
from helpers import color_driver, id_to_code, code_to_id, normalize_driver_name
from config import API_TIMEOUT, API_RETRY_DELAY, SEASON, ROUNDS, OUTPUT_BASE_DIR

def fetch_lap_info(SEASON, ROUND):

    print(f'Fetch data for round {ROUND+1}')

    offset = 0

    # lap_no -> list of {driver_id, position}
    timing_race: dict[int, list[dict]] = {}

    # circuit_id -> timing_race
    indiv_race_lap_info: dict[str, dict[int, list[dict]]] = {}

    circuit_id = ''

    while True:
        url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/{ROUND+1}/laps/"
        response = requests.get(url, params={"limit": 1000, "offset": offset}, timeout=API_TIMEOUT)
        status = response.status_code

        if status != 200:
            print(f"Status for round {ROUND+1}: {status}")
            break

        data = response.json()["MRData"]
        limit = int(data.get("limit", 0))
        total = int(data.get("total", 0))

        races = data["RaceTable"]["Races"]

        if not races:
            return {}, False

        race = races[0]

        circuit_id = race["Circuit"].get("circuitId")
        laps = race.get("Laps", [])

        # ---- flatten / transform here ----
        for lap in laps:
            lap_no = int(lap["number"])

            # ensure the key exists
            if lap_no not in timing_race:
                timing_race[lap_no] = []

            for timing in lap["Timings"]:
                driver_id = timing.get("driverId")
                position = timing.get("position")
                if position is None:
                    position = 0
                # Use id_to_code which now handles all driver ID formats
                driver_code = id_to_code(driver_id) if driver_id else ""
                prim, sec = color_driver(SEASON, driver_code)
                colors = {'primary': prim, 'secondary': sec}
                # Convert position to number and use driver_code to match race results format
                print(position)
                entry_timing = {"driver_id": driver_code, "position": int(position) if position else 0, "colors": colors}
                timing_race[lap_no].append(entry_timing)

        indiv_race_lap_info[circuit_id] = timing_race
        # -----------------------------------

        offset += limit
        if offset >= total or limit == 0:
            break
        else:
            time.sleep(API_RETRY_DELAY)

    # Transform to array format: [{lap: 1, positions: [...]}, {lap: 2, positions: [...]}, ...]
    json_ready = [
        {"lap": lap_no, "positions": timings}
        for lap_no, timings in sorted(timing_race.items())
    ]

    return json_ready, True

def make_jsons(file_path, json_ready):

    print("Generate jsons")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(json_ready, f, ensure_ascii=False, indent=2)
    print(f'Wrote {file_path}')


def find_round(OUT_DIR, SEASON, ROUNDS):

    for round_no in range(ROUNDS):

        file_path = os.path.join(OUT_DIR, f"laps_json_round{round_no+1}.json")

        data = True

        # if file does not exist -> generate it
        if not os.path.isfile(file_path):
            json_ready, data = fetch_lap_info(SEASON, round_no)
            if data:
                make_jsons(file_path, json_ready)
            else:
                print(f'No data for round {round_no+1}')
            time.sleep(10)
        else:
            print(f'{file_path} already exists')

if __name__ == "__main__":
    # Use settings from config file
    laps_path = os.path.join(OUTPUT_BASE_DIR, str(SEASON), "laps_data")
    os.makedirs(laps_path, exist_ok=True)

    find_round(laps_path, SEASON, ROUNDS)
