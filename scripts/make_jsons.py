import requests
import json
from collections import defaultdict
from itertools import chain
import os
from collections import OrderedDict, defaultdict


####### Make driver json with all drivers ######

def color_driver(drv_id):
    driver_colors_primary = {
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

    driver_colors_secondary = {
        # McLaren
        "NOR": "#B6BABD", "PIA": "#B6BABD",
        # Red Bull
        "VER": "#B6BABD", "TSU": "#B6BABD",
        # Ferrari
        "LEC": "#B6BABD", "HAM": "#B6BABD",
        # Mercedes
        "RUS": "#B6BABD", "ANT": "#B6BABD",
        # Aston Martin
        "ALO": "#B6BABD", "STR": "#B6BABD",
        # Williams
        "ALB": "#B6BABD", "SAI": "#B6BABD",
        # Alpine
        "GAS": "#B6BABD", "DOO": "#B6BABD",
        "COL": "#B6BABD",
        # Haas
        "OCO": "#B6BABD", "BEA": "#B6BABD",
        # RB (Visa Cash App RB)
        "LAW": "#4B4B4C", "HAD": "#4B4B4C",
        # Stake Sauber
        "BOR": "#B6BABD", "HUL": "#B6BABD"
    }

    primary = driver_colors_primary.get(drv_id) or "#FFFFFF" # default white
    secondary = driver_colors_secondary.get(drv_id) or "#B6BABD" # default light grey

    return primary, secondary

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
        "aston_martin": "#0A7968", 
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


# fetch basic driver data from results --> this gives us the actual number instead of just the permanent number
    # id, name, team, number, nationality, dob, (assets, colors)
def fetch_driver_data(SEASON):

    print("Fetch driver data")

    url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/last/results/"

    response = requests.get(url)
    results = response.json()['MRData']['RaceTable']['Races'][0].get('Results', [])

    driver_info = {}
    driver_info_constr = defaultdict(list)

    for entry in results:
        driver = entry['Driver']

        driver_id = driver.get('code', '')
        name = f"{driver.get('givenName', '')} {driver.get('familyName', '')}"
        nationality = driver.get('nationality', '')
        dob = driver.get('dateOfBirth', '')
        
        # ensures verstappen (or current future wl will get 1 if chosen)
        number = entry.get('number', driver.get('permanentNumber', '')) 
        
        constr = entry['Constructor']
        constr_id = constr.get('constructorId')
        team = constr.get('name', 'Unknown')

        assets = {'profile_photo': 'link1'} ### if needed profile pic
        colors = {'primary': color_driver(driver_id)[0], 'secondary': color_driver(driver_id)[1]}


        driver_info[driver_id] = {
            'driver_id': driver_id,
            'name': name,
            'team': team,
            'number': number,
            'nationality': nationality,
            'date_of_birth': dob,
            'assets': assets,
            'colors': colors
        }

        driver_info_constr[constr_id].append({
            'driver_id': driver_id,
            'name': name,
            'number': number,
        })

    return driver_info, driver_info_constr


def fetch_constr_data(SEASON):

    print("Fetch constructor data")

    url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/last/constructorstandings/"

    response = requests.get(url)
    results = response.json()['MRData']

    constructors = results['StandingsTable']['StandingsLists'][0]['ConstructorStandings']

    constr_info = defaultdict(list)


    for constr in constructors:
        c = constr.get('Constructor')
        constr_id = c.get('constructorId')
        name = c.get('name')
        #drivers --> earlier with results
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


# fetch current standings data fro driverStandings
    # position, points, wins
def fetch_driver_standings(SEASON):

    print("Fetch driver standings")

    driver_standings = {}

    url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/last/driverStandings/"

    response = requests.get(url)
    data = response.json()

    standings_drivers = data.get("MRData", {}).get("StandingsTable", {}).get("StandingsLists", [])[0].get("DriverStandings", [])

    for driver in standings_drivers:

        driver_info = driver.get('Driver', {})
        constr_info = driver.get('Constructors', {})

        driver_id = driver_info.get('code', '')

        # data to add for standings
        pos = driver.get("position")
        points = driver.get("points")
        wins = driver.get("wins")
        # podiums -> fetched later

        entry = {
            'position': int(pos), 
            'points': int(points), 
            'wins': int(wins)
        }

        driver_standings[driver_id] = entry

    return driver_standings


# fetch results for each round for each driver from results
    # podium, round, race name, date, points, finish position, starting position, status (dnf, finsih)
def fetch_results(SEASON, ROUNDS):

    print("Fetch results")

    # store race information
    race_info = defaultdict(list)
    results_info = defaultdict(list)
    fastest_lap_info = defaultdict(list)

    # store results per race for drivers and constructors
    driver_results = defaultdict(list)
    constr_results = defaultdict(list)

    # store podium info for constructors and drivers
    podiums_driver = {}
    podiums_constr = {}

    # go through each race
    for race in range(ROUNDS):

        url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/{race+1}/results/"

        response = requests.get(url)
        results = response.json()['MRData']['RaceTable']['Races']

        # check if race data has been published yet
        if not results:
            print(f'No entry for round {race+1}.')
            continue

        results = results[0]

        # general race info

        round_no = results.get('round', '')
        race_name = results.get('raceName', '')
        race_date = results.get('date', '')
        race_time = results.get('time', '')

        circuit = results.get('Circuit')
        circuit_id = circuit.get('circuitId')
        circuit_name = circuit.get('circuitName')

        race_location = circuit.get('Location')
        race_loaction = race_location.get('locality')
        race_country = race_location.get('country')


        races = results.get('Results', [])

        race_points = defaultdict(int)

        # store results per race per driver
        results_race = []

        # store fastest lap info
        fastest_laps = []
        
        # go through each driver (position) of the race
        for position in races:

            # driver and constr id
            driver = position.get('Driver', {})
            driver_id = driver.get('code', '')
            constr = position.get('Constructor', {})
            constr_id = constr.get('constructorId', '')


            # race data drivers for individual drivers json
            points = int(position.get('points', 0))
            end_pos = position.get('position', '')
            start_pos = position.get('grid', '')
            laps_done = position.get('laps', '')
            status = position.get('status', '')
            if status == 'Lapped':
                status = 'Finished'

            entry_driver = {
                'round': round_no,
                'raceName': race_name,
                'date': race_date,
                'points': int(points),
                'endPos': int(end_pos),
                'startPos': int(start_pos),
                'status': status
            }

            driver_results[driver_id].append(entry_driver)


            # calculate podium data
            if race == 0:
                podiums_driver.setdefault(driver_id, 0)
                podiums_constr.setdefault(constr_id, 0)

            if int(end_pos) <= 3:
                podiums_driver[driver_id] += 1
                podiums_constr[constr_id] += 1

            race_points[constr_id] += points


            # driver data for race json

            driver_number = position.get('number')
            driver_name = f"{driver.get('givenName')} {driver.get('familyName')}"
            driver_dob = driver.get('dateOfBirth')
            driver_nation = driver.get('nationality')

            driver_info = {'driver_id': driver_id, 'name': driver_name, 'number': driver_number, 'dob': driver_dob, 'nationality': driver_nation}

            # constructor info for race json
            constr_name = constr.get('name')
            constr_nation = constr.get('nationality')

            constr_info = {'constr_id': constr_id, 'name': constr_name, 'nationality': constr_nation}

            # fastest lap for race json
            fastest_lap_data = None
            fastest_lap_obj = position.get('FastestLap')

            if fastest_lap_obj:
                rank = fastest_lap_obj.get('rank')
                time = fastest_lap_obj['Time'].get('time')
                # save fastest lap in driver results
                fastest_lap_data = {'rank': rank, 'time': time}
                # save all fastest laps per circuit
                fastest_lap_drivers = {'driver_id': driver_id, 'rank': rank, 'time': time}
                fastest_laps.append(fastest_lap_drivers)

            entry_results = {
                'points': points, 
                'end_pos': end_pos, 
                'start_pos': start_pos, 
                'completed_laps': laps_done, 
                'status': status,
                'fastest_lap': fastest_lap_data,
                'driver': driver_info,
                'constr': constr_info
            }

            results_race.append(entry_results)

        # Append constructor results once per race (after processing all drivers)
        for constr_id, total_points in race_points.items():
            entry_constr = {
                'round': round_no,
                'raceName': race_name,
                'date': race_date,
                'points': total_points,
            }
            constr_results[constr_id].append(entry_constr)

        # get number of laps from number of completed laps from first driver 
        if not results_race:
            print(f'No results for round {race+1}, skipping race data.')
            continue
            
        race_laps = results_race[0].get('completed_laps')

        # Find the fastest lap with rank 1
        fastest_lap_rank1 = None
        for lap in fastest_laps:
            if lap.get('rank') == '1' or lap.get('rank') == 1:
                fastest_lap_rank1 = lap
                break

        entry_race_core = {
            'circuit_id': circuit_id,
            'round': round_no,
            'race_name': race_name,
            'circuit_name': circuit_name,
            'laps': race_laps,
            'country': race_country,
            'city': race_loaction,
            'date': race_date,
            'time': race_time,
            'fastest_lap': fastest_lap_rank1
        }

        # Store results and race info for this circuit
        fastest_lap_info[circuit_id] = fastest_laps
        results_info[circuit_id] = results_race
        race_info[circuit_id] = entry_race_core

    return driver_results, constr_results, podiums_driver, podiums_constr, race_info, results_info, fastest_lap_info


def fetch_quali(SEASON, ROUNDS):

    print("Fetch qualification data")

    quali_results = defaultdict(list)

    for race in range(ROUNDS):

        url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/{race+1}/qualifying/"

        response = requests.get(url)
        data = response.json()['MRData']['RaceTable']['Races']

        if not data:
            print(f'No entry for round {race+1}.')
            continue

        data = data[0]


        qualification = data['QualifyingResults']

        circuit_id = data['Circuit'].get('circuitId')

        result_per_race = []

        for result in qualification:

            quali_pos = result.get('position')

            q1 = result.get('Q1')
            q2 = result.get('Q2')
            q3 = result.get('Q3')

            sectors = {'q1': q1, 'q2': q2, 'q3': q3}

            driver = result.get('Driver')
            driver_number = result.get('number')
            driver_id = driver.get('code')
            driver_name = f"{driver.get('givenName')} {driver.get('familyName')}"
            driver_dob = driver.get('dateOfBirth')
            driver_nation = driver.get('nationality')

            driver_info = {'driver_id': driver_id, 'name': driver_name, 'number': driver_number, 'dob': driver_dob, 'nationality': driver_nation}

            constr = result.get('Constructor')
            constr_id = constr.get('constructorId')
            constr_name = constr.get('name')
            constr_nation = constr.get('nationality')

            constr_info = {'constr_id': constr_id, 'name': constr_name, 'nationality': constr_nation}

            entry_results = { 
                'quali_pos': quali_pos, 
                'sectors': sectors,
                'driver': driver_info,
                'constr': constr_info
            }

            result_per_race.append(entry_results)

        quali_results[circuit_id] = result_per_race


    return quali_results
    


# reorganize data and standardize team names
def normalize_driver(data):
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

    DRIVER_FIX = {
        "Andrea Kimi Antonelli": "Kimi Antonelli",
    }

    items = data.values() if isinstance(data, dict) else data
    keyed = {}
    for d in items:
        dd = dict(d)
        if dd.get("team") in TEAM_FIX:
            dd["team"] = TEAM_FIX[dd["team"]]

        if dd.get("name") in DRIVER_FIX:
            dd["name"] = DRIVER_FIX[dd["name"]]

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

def normalize_constr(data):
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

    DRIVER_FIX = {
        "Andrea Kimi Antonelli": "Kimi Antonelli"
    }

    items = data.values() if isinstance(data, dict) else data
    keyed = {}
    for d in items:
        dd = dict(d)
        if dd.get("name") in TEAM_FIX:
            dd["name"] = TEAM_FIX[dd["name"]]

        for driver in dd.get("drivers"):
            if driver["name"] in DRIVER_FIX:
                driver["name"] = DRIVER_FIX[driver["name"]]

        did = dd.get("constr_id")
        if did:
            keyed[did] = dd
            
    # stable, alphabetic key order
    return dict(sorted(keyed.items(), key=lambda kv: kv[0]))


# combine data for individual jsons and json with all drivers
def combine_data(SEASON, ROUNDS):

    print("Combine data for driver json")

    ## run individual processes:

    #driver data
    driver_info, constr_driver_info = fetch_driver_data(SEASON)

    constr_info = fetch_constr_data(SEASON)

    #data standings
    driver_standings = fetch_driver_standings(SEASON)

    #race results
    driver_results, constr_results, driver_podiums, constr_podiums, race_info, results_info, lap_info = fetch_results(SEASON, ROUNDS)

    # qualification results
    quali_info = fetch_quali(SEASON, ROUNDS)

    ## combine drivers

    print("Combine data for driver json")

    driver_comb_all = {}
    driver_comb_indiv = {}

    all_ids = set(chain(driver_info.keys(), driver_standings.keys()))
    for did in sorted(all_ids):

        driver_core_all = dict(driver_info.get(did, {"driver_id": did}))    # core info all drivers
        driver_core_indiv = dict(driver_info.get(did, {"driver_id": did}))  # core info individual drivers

        st = dict(driver_standings.get(did, {}))                            # driver standings copy
        st["podiums"] = driver_podiums.get(did, 0)                          # add podiums to standings
        driver_core_all["standings"] = st                                   # add standings to all drivers
        driver_core_indiv["standings"] = st                                 # add standings to individual drivers

        res  = list(driver_results.get(did, []))                            # driver results
        driver_core_indiv["results"] = res                                  # add results to individual drivers

        driver_comb_all[did] = driver_core_all                              # save all driver data
        driver_comb_indiv[did] = driver_core_indiv                          # save individual driver data


    driver_comb_norm_all = normalize_driver(driver_comb_all)
    driver_comb_norm_indiv = normalize_driver(driver_comb_indiv)


    #combine constructors

    print("Combine data for constructor json")

    constr_comb_all = {}
    constr_comb_indiv = {}


    all_ids = chain(constr_info.keys())
    for cid in sorted(all_ids):
        constr_core_all = dict(constr_info.get(cid, {"constr_id": cid}))        # core info all constr
        constr_core_indiv = dict(constr_info.get(cid, {"constr_id": cid}))      # core info individual constr

        # add drivers with standings to constructors
        drivers_list = constr_driver_info.get(cid, [])
        drivers_with_standings = []
        for driver in drivers_list:
            driver_copy = dict(driver)  # copy driver dict
            driver_id = driver_copy.get('driver_id', '')
            # add standings to each driver
            driver_standings_data = dict(driver_standings.get(driver_id, {}))
            driver_standings_data["podiums"] = driver_podiums.get(driver_id, 0)
            driver_copy["standings"] = driver_standings_data
            drivers_with_standings.append(driver_copy)
        
        constr_core_all["drivers"] = drivers_with_standings                     # add drivers to all constr
        constr_core_indiv["drivers"] = drivers_with_standings                   # add drivers to individual constr

        constr_core_all["standings"]["podiums"] = constr_podiums.get(cid, 0)    # add podiums to standings
        constr_core_indiv["standings"]["podiums"] = constr_podiums.get(cid, 0)  # add podiums to standings

        res  = list(constr_results.get(cid, []))                                # constr results
        constr_core_indiv["results"] = res                                      # add results to individual constr

        constr_comb_all[cid] = constr_core_all                                  # save all constr data
        constr_comb_indiv[cid] = constr_core_indiv                              # save individual constr data

    constr_comb_norm_all = normalize_constr(constr_comb_all)
    constr_comb_norm_indiv = normalize_constr(constr_comb_indiv)

    # race 

    print("Combine data for race json")

    race_comb_all = {}
    race_comb_indiv = {}

    all_ids = chain(race_info.keys())
    for rid in sorted(all_ids):
        race_core_all = dict(race_info.get(rid, {}))        # core info all races
        race_core_indiv = dict(race_info.get(rid, {}))      # core info individual races

        # Get results and quali data for this circuit
        race_results = results_info.get(rid, [])
        quali_results = quali_info.get(rid, [])
        lap_results = lap_info.get(rid, [])
        
        race_core_indiv['fastest_laps'] = lap_results
        race_core_indiv['race_results'] = race_results
        race_core_indiv['quali_results'] = quali_results
        

        race_comb_all[rid] = race_core_all                                  # save all constr data
        race_comb_indiv[rid] = race_core_indiv                              # save individual constr data

    race_comb_norm_all = race_comb_all
    race_comb_norm_indiv = race_comb_indiv

    return driver_comb_norm_all, driver_comb_norm_indiv, constr_comb_norm_all, constr_comb_norm_indiv, race_comb_norm_all, race_comb_norm_indiv


def make_jsons(OUT_DIR, SEASON, ROUNDS):

    print("Generate jsons")
    
    # Ensure output directories exists
    driver_path = os.path.join(OUT_DIR, "driver_data")
    constr_path = os.path.join(OUT_DIR, "constr_data")
    race_path = os.path.join(OUT_DIR, "race_data")

    os.makedirs(driver_path, exist_ok=True)
    os.makedirs(constr_path, exist_ok=True)
    os.makedirs(race_path, exist_ok=True)
    
    # combined dict results + standings, cleanded number + team
    driver_all, driver_indiv, constr_all, constr_indiv, race_all, race_indiv = combine_data(SEASON, ROUNDS)    
    
    # make driver jsons
    driver_all = list(driver_all.values())
    path = os.path.join(driver_path, f"driver_json_all.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(driver_all, f, indent=2, ensure_ascii=False)
    print(f"Wrote {path}")


    for id, data in driver_indiv.items():
        path = os.path.join(driver_path, f"driver_json_{id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)
        print(f"Wrote {path}")

    # make constr jsons
    constr_all = list(constr_all.values())
    path = os.path.join(constr_path, f"constr_json_all.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(constr_all, f, indent=2, ensure_ascii=False)
    print(f"Wrote {path}")


    for id, data in constr_indiv.items():
        path = os.path.join(constr_path, f"constr_json_{id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)
        print(f"Wrote {path}")

    race_all = list(race_all.values())
    path = os.path.join(race_path, f"race_json_all.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(race_all, f, indent=2, ensure_ascii=False)
    print(f"Wrote {path}")

    for id, data in race_indiv.items():
        path = os.path.join(race_path, f"race_json_{id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)
        print(f"Wrote {path}")



if __name__ == "__main__":
    season = 2025
    rounds_no = 24
    OUT_DIR = f'data/{season}/'
    make_jsons(OUT_DIR, season, rounds_no)


