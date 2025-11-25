import requests
import json
import os
import time

from collections import defaultdict
from itertools import chain
from datetime import datetime

from helpers import color_driver, color_constr, normalize_driver_name, normalize_constr_name
from config import API_TIMEOUT, API_RETRY_DELAY, SEASON, ROUNDS, SPRINTS, OUTPUT_BASE_DIR, YELLOW, RESET


####### Make driver json with all drivers ######



# fetch basic driver data from results --> this gives us the actual number instead of just the permanent number
    # id, name, team, number, nationality, dob, (assets, colors)
def fetch_driver_data(SEASON):

    print("Fetch driver data")

    url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/last/results/"

    try:
        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()  # Raises HTTPError for 4xx/5xx status codes
        data = response.json()
        
        races = data.get('MRData', {}).get('RaceTable', {}).get('Races', [])
        if not races:
            print(f"{YELLOW}Warning: No race data found for {SEASON}")
            return {}, {}
        
        results = races[0].get('Results', [])
        
    except requests.exceptions.Timeout:
        print(f"{YELLOW}Warning: API request timed out after {API_TIMEOUT} seconds{RESET}")
        return {}, {}
    except requests.exceptions.RequestException as e:
        print(f"{YELLOW}Warning: API request failed: {e}{RESET}")
        return {}, {}
    except (KeyError, IndexError, ValueError) as e:
        print(f"{YELLOW}Warning: Data parsing error: {e}")
        return {}, {}

    driver_info = {}
    driver_info_constr = defaultdict(list)
    
    # Mappings for helpers.py
    id_to_code_map = {}
    code_to_id_map = {}

    for entry in results:
        driver = entry.get('Driver', {})

        code = driver.get('code', '')
        original_driver_id = driver.get('driverId', '')
        
        # Fallback if code is missing (rare, but good for safety)
        if not code and original_driver_id:
            code = original_driver_id.upper()[:3]
            
        driver_id = code # We use code as the main identifier in this project
        
        # Populate mappings
        if original_driver_id and code:
            id_to_code_map[original_driver_id] = code
            code_to_id_map[code] = original_driver_id

        name = f"{driver.get('givenName', '')} {driver.get('familyName', '')}"
        nationality = driver.get('nationality', '')
        dob = driver.get('dateOfBirth', '')
        
        # ensures verstappen (or current future wl will get 1 if chosen)
        number = entry.get('number', driver.get('permanentNumber', '')) 
        
        constr = entry.get('Constructor', {})
        constr_id = constr.get('constructorId')
        team = constr.get('name', 'Unknown')

        assets = {'profile_photo': 'link1'} ### if needed profile pic
        colors = {'primary': color_driver(driver_id, SEASON)[0], 'secondary': color_driver(driver_id, SEASON)[1]}


        driver_info[driver_id] = {
            'driver_id': driver_id,
            'original_driver_id': original_driver_id,
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
        
    # Save mappings to JSON
    mappings = {
        "id_to_code": id_to_code_map,
        "code_to_id": code_to_id_map
    }
    
    mapping_dir = f'{OUTPUT_BASE_DIR}/{SEASON}/'
    os.makedirs(mapping_dir, exist_ok=True)
    mapping_file = os.path.join(mapping_dir, "driver_mappings.json")
    
    try:
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(mappings, f, indent=2)
    except Exception as e:
        print(f"{YELLOW}Warning: Failed to save driver mappings: {e}")

    return driver_info, driver_info_constr


def fetch_constr_data(SEASON):

    print("Fetch constructor data")

    url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/last/constructorstandings/"

    try:
        response = requests.get(url)
        results = response.json()['MRData']
    except Exception as e:
        print(f"{YELLOW}Warning: Failed to fetch constructor data: {e}")
        return {}

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
def fetch_driver_standings(SEASON, driver_info_old, constr_info_old, races_to_go, sprints_to_go):

    print("Fetch driver standings")

    driver_standings = {}

    url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/last/driverStandings/"

    try:
        response = requests.get(url)
        data = response.json()
    except Exception as e:
        print(f"{YELLOW}Warning: Failed to fetch driver standings: {e}")
        return {}

    standings_info = data.get("MRData", {}).get("StandingsTable", {}).get("StandingsLists", [])[0]
    standings_drivers = standings_info.get("DriverStandings", [])

    highest_points = standings_drivers[0].get('points', 0)
    points_to_go = (races_to_go * 25) + (sprints_to_go * 8)
    print(f'{highest_points}, {points_to_go}, {races_to_go}, {sprints_to_go}')

    for driver in standings_drivers:

        driver_info = driver.get('Driver', {})
        constr_info = driver.get('Constructors', {})

        driver_id = driver_info.get('code', '')

        if driver_info_old is not None and driver_id not in driver_info_old:
            original_driver_id = driver_info.get('driverId', '')
            name = driver_info.get('givenName', '') + ' ' + driver_info.get('familyName', '')
            team = constr_info[0].get('name', 'Unknown')
            number = driver_info.get('number', driver_info.get('permanentNumber', ''))
            nationality = driver_info.get('nationality', '')
            dob = driver_info.get('dateOfBirth', '')
            assets = {'profile_photo': 'link1'} ### if needed profile pic
            colors = {'primary': color_driver(driver_id, SEASON)[0], 'secondary': color_driver(driver_id, SEASON)[1]}

            constr_id = constr_info[0].get('constructorId', '')

            driver_info_old[driver_id] = {
                'driver_id': driver_id,
                'original_driver_id': original_driver_id,
                'name': name,
                'team': team,
                'number': number,
                'nationality': nationality,
                'date_of_birth': dob,
                'assets': assets,
                'colors': colors
            }

            constr_info_old[constr_id].append({
                'driver_id': driver_id,
                'name': name,
                'number': number,
            })
            

        # data to add for standings
        pos = driver.get("position")
        points = driver.get("points")
        wins = driver.get("wins")
        # podiums -> fetched later

        # championship contender
        if int(points) + int(points_to_go) >= int(highest_points):
            contender = True
        else:
            contender = False

        entry = {
            'position': int(pos), 
            'points': int(points), 
            'wins': int(wins),
            'contender': contender
        }

        driver_standings[driver_id] = entry

    return driver_standings, driver_info_old, constr_info_old


# fetch results for each round for each driver from results
    # podium, round, race name, date, points, finish position, starting position, status (dnf, finsih)
def fetch_results(SEASON, ROUNDS, last_completed_round):

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
    
    # store DNF/retirement counts for drivers and constructors
    dnf_driver = {}
    dnf_constr = {}
    disqualified_driver = {}
    disqualified_constr = {}

    races_to_go = 0

    # Only fetch the last 3 completed rounds (or fewer if less than 3 races have happened)
    if last_completed_round == 0:
        print("No completed rounds yet, skipping results fetch")
        return driver_results, constr_results, podiums_driver, podiums_constr, dnf_driver, dnf_constr, disqualified_driver, disqualified_constr, race_info, results_info, fastest_lap_info, ROUNDS
    
    start_round = max(1, last_completed_round - 2)  # Fetch last 3 rounds
    print(f"Fetching results for rounds {start_round} to {last_completed_round}")

    # go through the last 3 races to get the results
    for race in range(start_round - 1, last_completed_round):

        url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/{race+1}/results/"

        try:
            response = requests.get(url)
            results = response.json()['MRData']['RaceTable']['Races']
        except Exception as e:
            print(f"{YELLOW}Warning: Failed to fetch results for race {race+1}: {e}")
            continue

        # check if race data has been published yet
        if not results:
            print(f'{YELLOW}Warning: No entry for round {race+1}.')
            races_to_go += 1
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

            try:

                entry_driver = {
                    'round': round_no,
                    'raceName': race_name,
                    'date': race_date,
                    'points': int(points),
                    'endPos': int(end_pos),
                    'startPos': int(start_pos),
                    'status': status
                }

            except:
                entry_driver = {
                    'round': round_no,
                    'raceName': race_name,
                    'date': race_date,
                    'points': points,
                    'endPos': end_pos,
                    'startPos': start_pos,
                    'status': status
                }

            driver_results[driver_id].append(entry_driver)


            # calculate podium data
            podiums_driver.setdefault(driver_id, 0)
            podiums_constr.setdefault(constr_id, 0)

            if int(end_pos) <= 3:
                podiums_driver[driver_id] += 1
                podiums_constr[constr_id] += 1
            
            # Count DNFs (status not Finished or lapped) and disqualified
            # Initialize if not exists
            dnf_driver.setdefault(driver_id, 0)
            dnf_constr.setdefault(constr_id, 0)
            disqualified_driver.setdefault(driver_id, 0)
            disqualified_constr.setdefault(constr_id, 0)
            
            status_lower = status.lower()
            if status_lower not in ['finished', '+1 lap', '+2 laps', '+3 laps', 'disqualified']:
                dnf_driver[driver_id] += 1
                dnf_constr[constr_id] += 1

            if status_lower == 'disqualified':
                disqualified_driver[driver_id] += 1
                disqualified_constr[constr_id] += 1

            race_points[constr_id] += points


            # driver data for race json

            driver_number = position.get('number')
            driver_name = f"{driver.get('givenName')} {driver.get('familyName')}"
            driver_name = normalize_driver_name(driver_name)  # Normalize name
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
            print(f'{YELLOW}Warning: No results for round {race+1}, skipping race data.')
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

    return driver_results, constr_results, podiums_driver, podiums_constr, dnf_driver, dnf_constr, disqualified_driver, disqualified_constr, race_info, results_info, fastest_lap_info, races_to_go


def fetch_quali(SEASON, ROUNDS, last_completed_round):

    print("Fetch qualification data")

    quali_results = defaultdict(list)
    quali_race_info = {}  # Store circuit metadata for races with qualifying data

    time_format = '%M:%S.%f'
    
    # Only fetch the last 3 completed rounds (or fewer if less than 3 races have happened)
    if last_completed_round == 0:
        print("No completed rounds yet, skipping quali fetch")
        return quali_results, quali_race_info
    
    start_round = max(1, last_completed_round - 2)  # Fetch last 3 rounds
    print(f"Fetching qualifying for rounds {start_round} to {last_completed_round}")

    for race in range(start_round - 1, last_completed_round):

        url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/{race+1}/qualifying/"

        response = requests.get(url)
        
        # Handle empty responses for races that haven't happened yet
        try:
            data = response.json()['MRData']['RaceTable']['Races']
        except (requests.exceptions.JSONDecodeError, KeyError):
            print(f'{YELLOW}Warning: No entry for round {race+1}.')
            continue

        if not data:
            print(f'{YELLOW}Warning: No entry for round {race+1}.')
            continue

        data = data[0]

        # Extract circuit metadata
        circuit = data.get('Circuit', {})
        circuit_id = circuit.get('circuitId')
        circuit_name = circuit.get('circuitName')
        
        race_location = circuit.get('Location', {})
        race_country = race_location.get('country')
        race_city = race_location.get('locality')
        
        round_no = data.get('round', '')
        race_name = data.get('raceName', '')
        race_date = data.get('date', '')
        race_time = data.get('time', '')
        
        # Store circuit metadata
        quali_race_info[circuit_id] = {
            'circuit_id': circuit_id,
            'round': round_no,
            'race_name': race_name,
            'circuit_name': circuit_name,
            'country': race_country,
            'city': race_city,
            'date': race_date,
            'time': race_time
        }

        qualification = data['QualifyingResults']

        result_per_race = []

        fastest_q1 = datetime.strptime('59:59.99', time_format)
        fastest_q2 = datetime.strptime('59:59.99', time_format)
        fastest_q3 = datetime.strptime('59:59.99', time_format)


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
            driver_name = normalize_driver_name(driver_name)  # Normalize name
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

            if q1:
                q1_f = datetime.strptime(q1, time_format)
            if q2:
                q2_f = datetime.strptime(q2, time_format)
            if q3:
                q3_f = datetime.strptime(q3, time_format)

            if q1_f < fastest_q1:
                fastest_q1_driver = driver_id
                fastest_q1 = q1_f
            
            if q2_f < fastest_q2:
                fastest_q2_driver = driver_id
                fastest_q2 = q2_f

            if q3_f < fastest_q3:
                fastest_q3_driver = driver_id
                fastest_q3 = q3_f

        fastest_per_q = {
            'q1': {'driver_id': fastest_q1_driver, 'time': fastest_q1.strftime("%M:%S.%f").strip('0')},
            'q2': {'driver_id': fastest_q2_driver, 'time': fastest_q2.strftime("%M:%S.%f").strip('0')},
            'q3': {'driver_id': fastest_q3_driver, 'time': fastest_q3.strftime("%M:%S.%f").strip('0')}
        }

        result_per_race.append(fastest_per_q)

        quali_results[circuit_id] = result_per_race

    return quali_results, quali_race_info
    
def fetch_sprint(SEASON, ROUNDS, sprint_rounds):

    print("Fetch sprint data")

    sprint_dict = defaultdict(list)

    sprints_to_go = 0

    for race in range(ROUNDS):

        url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/{race+1}/sprint/"

        try:
            response = requests.get(url)
            sprints = response.json()['MRData']['RaceTable']['Races']
        except Exception as e:
            print(f"{YELLOW}Warning: Failed to fetch results for race {race+1}: {e}")
            continue

        # check if race data has been published yet
        if not sprints:
            if race+1 in sprint_rounds:
                print(f"{YELLOW}Warning: No entry for round {race+1}.")
                sprints_to_go += 1
            continue

        #sprints = sprints[0]

        for sprint in sprints:

            circuit_id = sprint["Circuit"]["circuitId"]
            round_no = sprint["round"]
            race_name = sprint["raceName"]
            circuit_name = sprint["Circuit"]["circuitName"]
            country = sprint["Circuit"]["Location"]["country"]
            city = sprint["Circuit"]["Location"]["locality"]
            sprint_date = sprint["date"]
            sprint_time = sprint["time"]

            sprint_res = sprint["SprintResults"]

            results = []

            for result in sprint_res:
                points = result["points"]
                end_pos = result["position"]
                start_pos = result["grid"]
                completed_laps = result["laps"]
                status = result["status"]
                #driver_time = result["Time"]["time"]


                driver_info = result["Driver"]
                driver_id = driver_info["driverId"]
                driver_name = f'{driver_info["givenName"]} {driver_info["familyName"]}'
                driver_number = result["number"]
                driver_dob = driver_info["dateOfBirth"]
                driver_nationality = driver_info["nationality"]

                driver = {
                    "driver_id": driver_id,
                    "driver_name": driver_name,
                    "driver_number": driver_number,
                    "driver_dob": driver_dob,
                    "driver_nationality": driver_nationality,
                }
                
                constr = result["Constructor"]
                constructor_id = constr["constructorId"]
                constructor_name = constr["name"]
                constructor_nationality = constr["nationality"]

                constructor = {
                    "constructor_id": constructor_id,
                    "constructor_name": constructor_name,
                    "constructor_nationality": constructor_nationality,
                }

                results.append({
                    "points": points,
                    "end_pos": end_pos,
                    "start_pos": start_pos,
                    "completed_laps": completed_laps,
                    "status": status,
                    #"time": driver_time,
                    "driver": driver,
                    "constructor": constructor,
                })

            laps = results[0].get("completed_laps", 0)

            sprint_dict[circuit_id].append(
                {
                    "circuit_id": circuit_id,
                    "round_no": round_no,
                    "race_name": race_name,
                    "circuit_name": circuit_name,
                    "laps": laps,
                    "country": country,
                    "city": city,
                    "date": sprint_date,
                    "time": sprint_time,
                    "SprintRresults": results,
                }
            )

    return sprint_dict, sprints_to_go


# Now you have one big dict:
# all_laps[(circuit_id, lap_no, driver_id)] -> "1:40.123"

# reorganize data and standardize team names
def normalize_driver(data):
    """Dict keyed by driver_id → driver dict (your desired structure)."""

    items = data.values() if isinstance(data, dict) else data
    keyed = {}
    for d in items:
        dd = dict(d)

        # Normalize team name
        if dd.get("team"):
            dd["team"] = normalize_constr_name(dd["team"])  

        # Normalize driver name
        if dd.get("name"):
            dd["name"] = normalize_driver_name(dd["name"])

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

    items = data.values() if isinstance(data, dict) else data
    keyed = {}
    for d in items:
        dd = dict(d)
        if dd.get("name") in TEAM_FIX:
            dd["name"] = TEAM_FIX[dd["name"]]

        # Normalize driver names in constructor's driver list
        for driver in dd.get("drivers", []):
            if driver.get("name"):
                driver["name"] = normalize_driver_name(driver["name"])

        did = dd.get("constr_id")
        if did:
            keyed[did] = dd
            
    # stable, alphabetic key order
    return dict(sorted(keyed.items(), key=lambda kv: kv[0]))


# Helper function to load existing JSON files
def load_existing_json(file_path):
    """Load existing JSON file if it exists, return None otherwise."""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"{YELLOW}Warning: Could not load {file_path}: {e}")
            return None
    return None


# combine data for individual jsons and json with all drivers
def combine_data(SEASON):

    print("Combine data...")

    # get rounds, sprints, sprint rounds, and last completed round:
    rounds, sprints, sprint_rounds, last_completed_round = count_rounds_sprints(SEASON)
    print(f"Total rounds: {rounds}, Sprints: {sprints}, Last completed round: {last_completed_round}")

    ## run individual processes:

    #driver data
    driver_info, constr_driver_info = fetch_driver_data(SEASON)

    constr_info = fetch_constr_data(SEASON)

    #race results
    driver_results, constr_results, driver_podiums, constr_podiums, driver_dnfs, constr_dnfs, driver_disq, constr_disq, race_info, results_info, lap_info, races_to_go = fetch_results(SEASON, rounds, last_completed_round)

    # sprint results
    sprint_info, sprints_to_go = fetch_sprint(SEASON, rounds, sprint_rounds)

    #data standings
    driver_standings, driver_info, constr_driver_info = fetch_driver_standings(SEASON, driver_info, constr_driver_info, races_to_go, sprints_to_go)


    # qualification results (includes circuit metadata for upcoming races)
    quali_info, quali_race_info = fetch_quali(SEASON, rounds, last_completed_round)

    # Merge with existing data if we only fetched partial rounds
    if last_completed_round > 0 and last_completed_round < rounds:
        print(f"Merging new data with existing data...")
        start_round = max(1, last_completed_round - 2)
        fetched_rounds = set(range(start_round, last_completed_round + 1))
        
        # Merge driver results
        driver_dir = f'{OUTPUT_BASE_DIR}/{SEASON}/driver_data/'
        for driver_id in driver_results.keys():
            existing_file = os.path.join(driver_dir, f'driver_json_{driver_id}.json')
            existing_data = load_existing_json(existing_file)
            if existing_data and 'results' in existing_data:
                # Keep results from rounds we didn't fetch
                existing_results = [r for r in existing_data['results'] if int(r.get('round', 0)) not in fetched_rounds]
                # Combine with new results
                driver_results[driver_id] = existing_results + driver_results[driver_id]
                # Sort by round
                driver_results[driver_id].sort(key=lambda x: int(x.get('round', 0)))
        
        # Merge constructor results
        constr_dir = f'{OUTPUT_BASE_DIR}/{SEASON}/constr_data/'
        for constr_id in constr_results.keys():
            existing_file = os.path.join(constr_dir, f'constr_json_{constr_id}.json')
            existing_data = load_existing_json(existing_file)
            if existing_data and 'results' in existing_data:
                # Keep results from rounds we didn't fetch
                existing_results = [r for r in existing_data['results'] if int(r.get('round', 0)) not in fetched_rounds]
                # Combine with new results
                constr_results[constr_id] = existing_results + constr_results[constr_id]
                # Sort by round
                constr_results[constr_id].sort(key=lambda x: int(x.get('round', 0)))
        
        # Recalculate cumulative stats from merged data
        print("Recalculating cumulative stats from merged data...")
        driver_podiums = {}
        constr_podiums = {}
        driver_dnfs = {}
        constr_dnfs = {}
        driver_disq = {}
        constr_disq = {}
        
        for driver_id, results in driver_results.items():
            podiums = sum(1 for r in results if int(r.get('endPos', 999)) <= 3)
            dnfs = sum(1 for r in results if r.get('status', '').lower() not in ['finished', '+1 lap', '+2 laps', '+3 laps', 'disqualified'])
            disqs = sum(1 for r in results if r.get('status', '').lower() == 'disqualified')
            driver_podiums[driver_id] = podiums
            driver_dnfs[driver_id] = dnfs
            driver_disq[driver_id] = disqs
        
        # For constructors and races, we need to load ALL race data and recalculate
        # Load existing race_json_all.json to get all race data
        race_dir = f'{OUTPUT_BASE_DIR}/{SEASON}/race_data/'
        all_races_file = os.path.join(race_dir, 'race_json_all.json')
        existing_all_races = load_existing_json(all_races_file)
        
        if existing_all_races:
            # Build a dict of existing races by circuit_id
            existing_race_dict = {r['circuit_id']: r for r in existing_all_races}
            
            # Merge race_info: keep existing races, update with new data
            for circuit_id in existing_race_dict.keys():
                if circuit_id not in race_info:
                    # This race wasn't fetched, keep the existing core info
                    race_info[circuit_id] = {
                        'circuit_id': existing_race_dict[circuit_id].get('circuit_id'),
                        'round': existing_race_dict[circuit_id].get('round'),
                        'race_name': existing_race_dict[circuit_id].get('race_name'),
                        'circuit_name': existing_race_dict[circuit_id].get('circuit_name'),
                        'laps': existing_race_dict[circuit_id].get('laps'),
                        'country': existing_race_dict[circuit_id].get('country'),
                        'city': existing_race_dict[circuit_id].get('city'),
                        'date': existing_race_dict[circuit_id].get('date'),
                        'time': existing_race_dict[circuit_id].get('time'),
                        'fastest_lap': existing_race_dict[circuit_id].get('fastest_lap')
                    }
                    
                    # Also load the results for this race
                    if circuit_id not in results_info:
                        results_info[circuit_id] = existing_race_dict[circuit_id].get('results', [])
                    
                    # And fastest laps
                    if circuit_id not in lap_info:
                        lap_info[circuit_id] = existing_race_dict[circuit_id].get('fastest_laps', [])
            
            # Now recalculate constructor stats from ALL race results
            for circuit_id in race_info.keys():
                results = results_info.get(circuit_id, [])
                
                for result in results:
                    constr_id = result.get('constr', {}).get('constr_id')
                    if constr_id:
                        constr_podiums.setdefault(constr_id, 0)
                        constr_dnfs.setdefault(constr_id, 0)
                        constr_disq.setdefault(constr_id, 0)
                        
                        end_pos = int(result.get('end_pos', 999))
                        if end_pos <= 3:
                            constr_podiums[constr_id] += 1
                        
                        status = result.get('status', '').lower()
                        if status not in ['finished', '+1 lap', '+2 laps', '+3 laps', 'disqualified']:
                            constr_dnfs[constr_id] += 1
                        if status == 'disqualified':
                            constr_disq[constr_id] += 1
        else:
            # No existing data, just use what we fetched
            for circuit_id, results in results_info.items():
                for result in results:
                    constr_id = result.get('constr', {}).get('constr_id')
                    if constr_id:
                        constr_podiums.setdefault(constr_id, 0)
                        constr_dnfs.setdefault(constr_id, 0)
                        constr_disq.setdefault(constr_id, 0)
                        
                        end_pos = int(result.get('end_pos', 999))
                        if end_pos <= 3:
                            constr_podiums[constr_id] += 1
                        
                        status = result.get('status', '').lower()
                        if status not in ['finished', '+1 lap', '+2 laps', '+3 laps', 'disqualified']:
                            constr_dnfs[constr_id] += 1
                        if status == 'disqualified':
                            constr_disq[constr_id] += 1




    ## combine drivers

    driver_comb_all = {}
    driver_comb_indiv = {}

    all_ids = set(chain(driver_info.keys(), driver_standings.keys()))
    for did in sorted(all_ids):

        driver_core_all = dict(driver_info.get(did, {"driver_id": did}))    # core info all drivers
        driver_core_indiv = dict(driver_info.get(did, {"driver_id": did}))  # core info individual drivers

        st = dict(driver_standings.get(did, {}))                            # driver standings copy
        st["podiums"] = driver_podiums.get(did, 0)                          # add podiums to standings
        st["dnf_count"] = driver_dnfs.get(did, 0)    
        st["disq_count"] = driver_disq.get(did, 0)                       # add DNF count to standings
        driver_core_all["standings"] = st                                   # add standings to all drivers
        driver_core_indiv["standings"] = st                                 # add standings to individual drivers

        res  = list(driver_results.get(did, []))                            # driver results
        driver_core_indiv["results"] = res                                  # add results to individual drivers

        driver_comb_all[did] = driver_core_all                              # save all driver data
        driver_comb_indiv[did] = driver_core_indiv                          # save individual driver data


    driver_comb_norm_all = normalize_driver(driver_comb_all)
    driver_comb_norm_indiv = normalize_driver(driver_comb_indiv)


    #combine constructors

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
        constr_core_all["standings"]["dnf_count"] = constr_dnfs.get(cid, 0)     # add DNF count to standings
        constr_core_all["standings"]["disq_count"] = constr_disq.get(cid, 0)    # add disqualified count to standings
        constr_core_indiv["standings"]["podiums"] = constr_podiums.get(cid, 0)  # add podiums to standings
        constr_core_indiv["standings"]["dnf_count"] = constr_dnfs.get(cid, 0)   # add DNF count to standings
        constr_core_indiv["standings"]["disq_count"] = constr_disq.get(cid, 0)  # add disqualified count to standings

        res  = list(constr_results.get(cid, []))                                # constr results
        constr_core_indiv["results"] = res                                      # add results to individual constr

        constr_comb_all[cid] = constr_core_all                                  # save all constr data
        constr_comb_indiv[cid] = constr_core_indiv                              # save individual constr data

    constr_comb_norm_all = normalize_constr(constr_comb_all)
    constr_comb_norm_indiv = normalize_constr(constr_comb_indiv)

    # race 

    race_comb_all = {}
    race_comb_indiv = {}

    # Include circuits from both race_info and quali_info (for races that haven't happened yet)
    all_ids = set(chain(race_info.keys(), quali_info.keys()))
    for rid in sorted(all_ids):
        # Use race_info if available, otherwise use quali_race_info for upcoming races
        if rid in race_info:
            race_core_all = dict(race_info.get(rid, {}))
            race_core_indiv = dict(race_info.get(rid, {}))
        elif rid in quali_race_info:
            # Race hasn't happened yet, but we have qualifying data
            race_core_all = dict(quali_race_info.get(rid, {}))
            race_core_indiv = dict(quali_race_info.get(rid, {}))
        else:
            # Shouldn't happen, but just in case
            race_core_all = {}
            race_core_indiv = {}

        # Get results and quali data for this circuit
        race_results = results_info.get(rid, [])
        quali_results = quali_info.get(rid, [])
        lap_results = lap_info.get(rid, [])

        if sprint_info not in [None, {}]:
            if sprint_info.get(rid, []) != []:
                sprint_results = sprint_info.get(rid, [])
                sprint = True
            else:
                sprint_results = []
                sprint = False
        else:
            sprint_results = []
            sprint = False
        
        race_core_all['sprint'] = sprint
        
        race_core_indiv['sprint'] = sprint
        race_core_indiv['fastest_laps'] = lap_results
        race_core_indiv['race_results'] = race_results
        race_core_indiv['quali_results'] = quali_results
        race_core_indiv['sprint_results'] = sprint_results
        

        race_comb_all[rid] = race_core_all                                  # save all constr data
        race_comb_indiv[rid] = race_core_indiv                              # save individual constr data

    race_comb_norm_all = race_comb_all
    race_comb_norm_indiv = race_comb_indiv

    return driver_comb_norm_all, driver_comb_norm_indiv, constr_comb_norm_all, constr_comb_norm_indiv, race_comb_norm_all, race_comb_norm_indiv


def make_jsons(OUT_DIR, SEASON):

    print("Generate jsons...")
    
    # Ensure output directories exists
    driver_path = os.path.join(OUT_DIR, "driver_data")
    constr_path = os.path.join(OUT_DIR, "constr_data")
    race_path = os.path.join(OUT_DIR, "race_data")

    os.makedirs(driver_path, exist_ok=True)
    os.makedirs(constr_path, exist_ok=True)
    os.makedirs(race_path, exist_ok=True)
    
    # combined dict results + standings, cleanded number + team
    driver_all, driver_indiv, constr_all, constr_indiv, race_all, race_indiv = combine_data(SEASON)    
    
    # make driver jsons
    driver_all = list(driver_all.values())
    path = os.path.join(driver_path, f"driver_json_all.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(driver_all, f, indent=2, ensure_ascii=False)


    for id, data in driver_indiv.items():
        path = os.path.join(driver_path, f"driver_json_{id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)

    # make constr jsons
    constr_all = list(constr_all.values())
    path = os.path.join(constr_path, f"constr_json_all.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(constr_all, f, indent=2, ensure_ascii=False)


    for id, data in constr_indiv.items():
        path = os.path.join(constr_path, f"constr_json_{id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)

    race_all = list(race_all.values())
    path = os.path.join(race_path, f"race_json_all.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(race_all, f, indent=2, ensure_ascii=False)

    for id, data in race_indiv.items():
        path = os.path.join(race_path, f"race_json_{id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)
        print(f"Wrote {path}")


# count rounds and sprint weekends
def count_rounds_sprints(SEASON):

    limit = 1000

    url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/races/"
    response = requests.get(url, params={"limit": limit, "offset": 0})
    status = response.status_code

    data = response.json()['MRData']

    total = data['total']
    if int(total) > limit:
        print(f"{YELLOW}Warning: Total api json lines is greater than {limit}.{RESET}")

    races = data['RaceTable']['Races']

    count_sprints = 0
    count_races = 0
    sprint_rounds = []
    last_completed_round = 0
    
    # Get current date for comparison
    current_date = datetime.now().date()

    for race in races:
        count_races += 1

        sprint = race.get('Sprint')
        if sprint != None:
            count_sprints += 1
            sprint_rounds.append(count_races)
        
        # Check if this race has happened based on qualifying date
        # Use qualifying date as it happens before the race
        quali_date_str = race.get('Qualifying', {}).get('date')
        if quali_date_str:
            try:
                quali_date = datetime.strptime(quali_date_str, '%Y-%m-%d').date()
                # If qualifying has happened, this round is completed
                if quali_date <= current_date:
                    last_completed_round = count_races
            except ValueError:
                # If date parsing fails, skip this race
                pass

    return count_races, count_sprints, sprint_rounds, last_completed_round


if __name__ == "__main__":
    # Use settings from config file
    OUT_DIR = f'{OUTPUT_BASE_DIR}/{SEASON}/'
    make_jsons(OUT_DIR, SEASON)


