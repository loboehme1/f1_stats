import requests
import json
from collections import defaultdict
from itertools import chain
import os

def color_constr(constr_id):
    constr_colors = {
        # McLaren
        "mclaren": "#FF8700",
        # Red Bull
        "red_bull": "#00008b",
        # Ferrari
        "ferrari": "#DC0000", 
        # Mercedes
        "mercedes": "#00A19C", 
        # Aston Martin
        "astonmartin": "#0A7968", 
        # Williams
        "williams": "#46b1eb", 
        # Alpine
        "alpine": "#f743e8", 
        # Haas
        "haas": "#f04a4a", 
        # RB (Visa Cash App RB)
        "rb": "#B6BABD", 
        # Stake Sauber
        "sauber": "#09eb24"
    }

    return constr_colors.get(constr_id) or "#FFFFFF"  # default white

def fetch_constr_data(SEASON):
    url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/last/constructorstandings/"

    response = requests.get(url)
    results = response.json()['MRData']

    constructors = results['StandingsTable']['StandingsLists'][0]['ConstructorStandings']

    constr_info = defaultdict(list)


    for constr in constructors:
        c = constr.get('Constructor')
        constr_id = c.get('constructorId')
        name = c.get('name')
        #drivers --> later with results
        nationality = c.get('nationality')
        assets = {'logo_photo': 'logo_link'}
        colors = {'primary': color_constr(constr_id)}
        position = constr.get('position')
        points = constr.get('points')
        wins = constr.get('wins')
        standings = {'position': position, 'points': points, 'wins': wins}
        #podiums --> later with results

        constr_info[constr_id] = {
            'constr_id': constr_id,
            'name': name,
            'nationality': nationality,
            'assets': assets,
            'colors': colors,
            'standings': standings
        }

    return constr_info



def fetch_results_indiv(SEASON, ROUNDS):

    constr_results = defaultdict(list)
    podiums = {}
    drivers = defaultdict(list)          # constr_id -> list of {driver_id, name}
    driver_ids_by_team = defaultdict(set)  # constr_id -> set of driver_ids we've already added

    for race in range(ROUNDS):

        url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/{race+1}/results/"
        response = requests.get(url)
        results = response.json()['MRData']['RaceTable']['Races']

        if not results:
            print(f'No entry for round {race+1}.')
            continue

        results = results[0]

        round_no = results.get('round', '')
        race_name = results.get('raceName', '')
        date = results.get('date', '')

        races = results.get('Results', [])

        # accumulate points per constructor for THIS race
        race_points = defaultdict(int)

        for position in races:
            points = int(position.get('points', 0))
            constr = position.get('Constructor', {})
            constr_id = constr.get('constructorId', '')

            driver_info = position.get('Driver', {})
            driver_id = driver_info.get('code')  # e.g. "NOR"
            driver_name = f"{driver_info.get('givenName')} {driver_info.get('familyName')}"

            # only add driver once per constructor, based on driver_id
            if driver_id and driver_id not in driver_ids_by_team[constr_id]:
                driver = {'driver_id': driver_id, 'name': driver_name}
                drivers[constr_id].append(driver)
                driver_ids_by_team[constr_id].add(driver_id)

            # init podiums dict when we see the constructor
            podiums.setdefault(constr_id, 0)

            if points >= 15:
                podiums[constr_id] += 1

            # add points of drivers
            race_points[constr_id] += points

        # create one entry per constructor with summed points
        for constr_id, total_points in race_points.items():
            entry = {
                'round': round_no,
                'raceName': race_name,
                'date': date,
                'points': total_points,
            }
            constr_results[constr_id].append(entry)

    return constr_results, podiums, drivers


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
        if dd.get("name") in TEAM_FIX:
            dd["name"] = TEAM_FIX[dd["name"]]

        did = dd.get("constr_id")
        if did:
            keyed[did] = dd
            
    # stable, alphabetic key order
    return dict(sorted(keyed.items(), key=lambda kv: kv[0]))



def combine_data(SEASON, ROUNDS):
    ## run individual processes:

    constr_dict = fetch_constr_data(SEASON) # general + standings

    constr_results, podiums, drivers = fetch_results_indiv(SEASON, ROUNDS) # constructor results per race

    ## combine all data

    combined_all = {}
    combined_indiv = {}
    all_ids = chain(constr_dict.keys())
    for cid in sorted(all_ids):
        core_all = dict(constr_dict.get(cid, {"constr_id": cid}))    # keep core info if present
        core_indiv = dict(constr_dict.get(cid, {"constr_id": cid}))

        core_all["drivers"] = drivers.get(cid, 0)
        core_indiv["drivers"] = drivers.get(cid, 0)

        core_all["standings"]["podiums"] = podiums.get(cid, 0)
        core_indiv["standings"]["podiums"] = podiums.get(cid, 0)

        res  = list(constr_results.get(cid, []))                   # list (may be empty)
        core_indiv["results"] = res                                   # add results

        combined_all[cid] = core_all                                  # save in new dict
        combined_indiv[cid] = core_indiv                              # save in new dict

    comb_norm_all = normalized_map(combined_all)
    comb_norm_indiv = normalized_map(combined_indiv)

    return comb_norm_all, comb_norm_indiv


def make_jsons(OUT_DIR, SEASON, ROUNDS):

    os.makedirs(OUT_DIR, exist_ok=True)
        
    comb_all, comb_indiv = combine_data(SEASON, ROUNDS)

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
    OUT_DIR = f'data/{season}/constr_data/'
    make_jsons(OUT_DIR, season, rounds_no)

