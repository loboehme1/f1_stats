import requests
import json
from collections import defaultdict
from itertools import chain
import os
from collections import OrderedDict


####### Make driver json with all drivers ######

def color_driver(drv_id):
    driver_colors = {
        # McLaren
        "NOR": "#FF8700", "PIA": "#FF8700",
        # Red Bull
        "VER": "#00008b", "TSU": "#00008b",
        # Ferrari
        "LEC": "#DC0000", "HAM": "#DC0000",
        # Mercedes
        "RUS": "#00A19C", "ANT": "#00A19C",
        # Aston Martin
        "ALO": "#0A7968", "STR": "#0A7968",
        # Williams
        "ALB": "#46b1eb", "SAI": "#46b1eb",
        # Alpine
        "GAS": "#f743e8", "DOO": "#f743e8",
        "COL": "#f743e8",
        # Haas
        "OCO": "#f04a4a", "BEA": "#f04a4a",
        # RB (Visa Cash App RB)
        "LAW": "#B6BABD", "HAD": "#B6BABD",
        # Stake Sauber
        "BOR": "#09eb24", "HUL": "#09eb24"
    }

    return driver_colors.get(drv_id) or "#FFFFFF"  # default white


# fetch basic driver data from results --> this gives us the actual number instead of just the permanent number
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
        colors = {'primary': color_driver(driver_id)}


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


# fetch current standings data fro driverStandings
    # position, points, wins
def fetch_standings(SEASON = 'current'):

    standings = {}

    url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/last/driverStandings/"

    response = requests.get(url)
    data = response.json()

    standings_drivers = data.get("MRData", {}).get("StandingsTable", {}).get("StandingsLists", [])[0].get("DriverStandings", [])

    for driver in standings_drivers:

        driver_info = driver.get('Driver', {})

        driver_id = driver_info.get('code', '')

        # data to add for standings
        pos = driver.get("position")
        points = driver.get("points")
        wins = driver.get("wins")
        # podiums -> fetched later

        standings[driver_id] = {'position': int(pos), 'points': int(points), 'wins': int(wins)}

    return standings


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
                'points': int(points),
                'endPos': int(end_pos),
                'startPos': int(start_pos),
                'status': status
            }

            driver_results[driver_id].append(entry)

            if int(end_pos) <= 3:
                current = podiums[driver_id]
                podiums[driver_id] = current+1

    return driver_results, podiums


# reorganize data and standardize team names
def normalized_map(data):
    """Dict keyed by driver_id → driver dict (your desired structure)."""

    TEAM_FIX = {
    "Haas F1 Team": "Haas",
    "Alpine F1 Team": "Alpine",
    "RB F1 Team": "Racing Bulls",
    "Red Bull": "Red Bull",
    "McLaren": "McLaren",
    "Aston Martin": "Aston Martin",
    "Williams": "Williams",
    "Mercedes": "Mercedes",
    "Ferrari": "Ferrari",
    "Sauber": "Sauber",
    }

    items = data.values() if isinstance(data, dict) else data
    keyed = {}
    for d in items:
        dd = dict(d)
        if dd.get("team") in TEAM_FIX:
            dd["team"] = TEAM_FIX[dd["team"]]
        n = dd.get("number")
        try:
            dd["number"] = int(n)
        except (TypeError, ValueError):
            pass
        did = dd.get("driver_id")
        if did:
            keyed[did] = dd
            
    # stable, alphabetic key order
    return dict(sorted(keyed.items(), key=lambda kv: kv[0]))


# combine data for individual jsons and json with all drivers
def combine_data(SEASON, ROUNDS):

    ## run individual processes:

    #driver data
    drivers_dict = fetch_driver_data(SEASON)

    #data standings
    standings_dict = fetch_standings(SEASON)

    #results
    results_by_driver, podiums = fetch_results_indiv(SEASON, ROUNDS)

    ## combine all data

    combined_all = {}
    combined_indiv = {}
    all_ids = set(chain(drivers_dict.keys(), standings_dict.keys()))
    for did in sorted(all_ids):
        core_all = dict(drivers_dict.get(did, {"driver_id": did}))    # keep core info if present
        core_indiv = dict(drivers_dict.get(did, {"driver_id": did}))

        st   = dict(standings_dict.get(did, {}))                      # copy so we can mutate
        st["podiums"] = podiums.get(did, 0)                           # add podiums (default 0)
        core_all["standings"] = st                                    # add standings
        core_indiv["standings"] = st                                  # add standings

        res  = list(results_by_driver.get(did, []))                   # list (may be empty)
        core_indiv["results"] = res                                   # add results

        combined_all[did] = core_all                                  # save in new dict
        combined_indiv[did] = core_indiv                              # save in new dict

    comb_norm_all = normalized_map(combined_all)
    comb_norm_indiv = normalized_map(combined_indiv)

    return comb_norm_all, comb_norm_indiv


def make_jsons(OUT_DIR, SEASON, ROUNDS):
    # Ensure output directory exists
    os.makedirs(OUT_DIR, exist_ok=True)
    
    comb_all, comb_indiv = combine_data(SEASON, ROUNDS)    # combined dict results + standings, cleanded number + team
    
    comb_all = list(comb_all.values())
    path = os.path.join(OUT_DIR, f"driver_json_all.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(comb_all, f, indent=2, ensure_ascii=False)
    print(f"Wrote {path}")


    for code, data in comb_indiv.items():
        path = os.path.join(OUT_DIR, f"driver_json_{code}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)
        print(f"Wrote {path}")



if __name__ == "__main__":
    season = 2025
    rounds_no = 24
    OUT_DIR = f'data/{season}/driver_data/'
    make_jsons(OUT_DIR, season, rounds_no)


