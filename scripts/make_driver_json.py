import requests
import json
from collections import defaultdict
from itertools import chain
import os
from collections import OrderedDict


####### Make driver json with all drivers ######



# get the basic driver data from results --> this gives us the actual number instead of just the permanent number
    # id, name, team, number, nationality, dob, (assets, colors)
def fetch_driver_data(SEASON):
    url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/last/results/"

    response = requests.get(url)
    results = response.json()['MRData']['RaceTable']['Races'][0].get('Results', [])

    driver_data = {}

    for entry in results:
        driver = entry['Driver']
        constr = entry['Constructor']

        first = driver.get('givenName', '')
        last = driver.get('familyName', '')

        driver_id = driver.get('code', '')
        name = f"{first} {last}"
        team = constr.get('name', 'Unknown')
        number = entry.get('number', driver.get('permanentNumber', '')) # ensures verstappen (or current future wl will get 1 if chosen)
        nationality = driver.get('nationality', '')
        dob = driver.get('dateOfBirth', '')
        assets = {'profile_photo': 'link1'} ### if needed profile pic
        colors = {'primary': '#000000', 'secondary': '#FFFFFF'} ### get from my own data source


        driver_data[driver_id] = {
            'driver_id': driver_id,
            'name': name,
            'team': team,
            'number': number,
            'nationality': nationality,
            'date_of_birth': dob,
            'assets': assets,
            'colors': colors
        }

    return driver_data


# reorganize data and standardize team names
def to_list(data):

    TEAM_FIX = {
    "Haas F1 Team": "Haas", #
    "Alpine F1 Team": "Alpine",
    "RB F1 Team": "Racing Bulls", #
    "Red Bull": "Red Bull", #
    "McLaren": "McLaren", #
    "Aston Martin": "Aston Martin", #
    "Williams": "Williams", #
    "Mercedes": "Mercedes", #
    "Ferrari": "Ferrari", #
    "Sauber": "Sauber" #
    }  
     
    """Accepts dict keyed by driver_id OR an already-made list; returns cleaned list."""
    items = data.values() if isinstance(data, dict) else data
    out = []
    for d in items:
        dd = dict(d)  # shallow copy

        # team normalization
        t = dd.get("team")
        if t in TEAM_FIX:
            dd["team"] = TEAM_FIX[t]

        # number → int when possible
        n = dd.get("number")
        try:
            dd["number"] = int(n)
        except (TypeError, ValueError):
            pass  # leave as-is if not numeric

        out.append(dd)

    # stable order (by driver_id)
    out.sort(key=lambda x: x.get("driver_id", ""))
    return out


# generate the json file
def make_json_all(OUT_DIR, SEASON):
    path = os.path.join(OUT_DIR, f"driver_json_all.json")
    data = fetch_driver_data(SEASON)                 # returns your dict keyed by driver_id
    data = to_list(data)                       # <- convert + clean
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f'Written to {path}')
    return path


###### Individual jsons for drivers ######

# test of driver id exists
def test_driverId(driverId):

    if driverId == '':
        print('DriverId empty, something went wrong')
        return False
        
    return True


# fetch current standings data fro driverStandings
    # position, points, wins
def fetch_standings_indiv(SEASON = 'current', folder = 'public/'):

    standings_indiv = {}

    url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/last/driverStandings/"

    response = requests.get(url)
    data = response.json()

    standings_drivers = data.get("MRData", {}).get("StandingsTable", {}).get("StandingsLists", [])[0].get("DriverStandings", [])

    for driver in standings_drivers:

        driver_info = driver.get('Driver', {})

        driver_id = driver_info.get('code', '')
        test_driverId(driver_id)

        # data to add for standings
        pos = driver.get("position")
        points = driver.get("points")
        wins = driver.get("wins")
        # podiums -> fetched later

        standings_indiv[driver_id] = {'position': pos, 'points': points, 'wins': wins}

    return standings_indiv


# fetch results for each round for each driver from results
    # podium, round, race name, date, points, finish position, starting position, status (dnf, finsih)
def fetch_results_indiv(SEASON, ROUNDS):

    driver_results = defaultdict(list)

    podiums = {}

    for race in range(ROUNDS):

        url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/{race+1}/results/"

        response = requests.get(url)
        results = response.json()['MRData']['RaceTable']['Races']

        if not results:
            print(f'No entry for round {race+1}.')
            continue

        results = results[0]

        #round
        round_no = results.get('round', '')

        #name
        race_name = results.get('raceName', '')

        #date
        date = results.get('date', '')


        races = results.get('Results', [])
        for position in races:

            driver = position.get('Driver', {})
            driver_id = driver.get('code', '')

            if race == 0:
                podiums.setdefault(driver_id, 0)

            #points
            points = position.get('points', '')

            #endpos
            end_pos = position.get('position', '')

            #startpos
            start_pos = position.get('grid', '')

            #status
            status = position.get('status', '')

            if status == 'Lapped':
                status = 'Finished'

            entry = {
                'round': round_no,
                'raceName': race_name,
                'date': date,
                'points': points,
                'endPos': end_pos,
                'startPos': start_pos,
                'status': status
            }

            driver_results[driver_id].append(entry)

            if int(end_pos) <= 3:
                current = podiums[driver_id]
                podiums[driver_id] = current+1

    return driver_results, podiums


# combine data from all fetches (including basic data from json with all drivers)
def combine_data(SEASON, ROUNDS):

    ## run individual processes:

    # basic data from json with all drivers
    drivers_dict = fetch_driver_data(SEASON)

    # stadings data
    standings_dict = fetch_standings_indiv(SEASON, ROUNDS)

    # results data
    results_by_driver, podiums = fetch_results_indiv(SEASON, ROUNDS)

    ## combine all data

    combined = {}
    all_ids = set(chain(drivers_dict.keys(), standings_dict.keys(), results_by_driver.keys(), podiums.keys()))
    for did in sorted(all_ids):
        core = dict(drivers_dict.get(did, {"driver_id": did}))        # keep core info if present
        st   = dict(standings_dict.get(did, {}))                      # copy so we can mutate
        st["podiums"] = podiums.get(did, 0)                           # add podiums (default 0)
        res  = list(results_by_driver.get(did, []))                   # list (may be empty)

        core["standings"] = st
        core["results"]   = res
        combined[did]     = core

    return combined


# normalize driver data
def normalize_driver(d):

    KEY_ORDER = [
    "driver_id","name","team","number","nationality","date_of_birth",
    "assets","colors","standings","results"
    ]

    # sort results by round (numeric) but keep all values as strings as in your data
    results = sorted(d.get("results", []), key=lambda r: int(r.get("round", "0")))
    # rebuild in fixed key order to preserve structure
    od = OrderedDict()
    for k in KEY_ORDER:
        if k == "results":
            od[k] = results
        else:
            od[k] = d.get(k, {})
    return od


# make json for each driver individually
def make_json_indiv(OUT_DIR, SEASON, ROUNDS):
    # your big dict:
    drivers = combine_data(SEASON, ROUNDS)

    os.makedirs(OUT_DIR, exist_ok=True)


    for code, data in drivers.items():
        norm = normalize_driver(data)
        # prefer slug if present, else the code
        path = os.path.join(OUT_DIR, f"driver_json_{code}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(norm, f, ensure_ascii=False, indent=2, sort_keys=False)
        print(f"Wrote {path}")



if __name__ == "__main__":
    season = 2025
    rounds_no = 24
    OUT_DIR = f'data/{season}/driver_data/'
    make_json_all(OUT_DIR, season)
    make_json_indiv(OUT_DIR, season, rounds_no)


