"""API fetching functions for F1 data."""

import requests
import json
import os
import time
from collections import defaultdict
from datetime import datetime

from helpers import color_driver, color_constr, normalize_driver_name, normalize_constr_name
from config import API_TIMEOUT, API_RETRY_DELAY, OUTPUT_BASE_DIR, YELLOW, RESET


def fetch_driver_data(SEASON):

    print("Fetch driver data")

    url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/last/results/"

    try:
        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()  # Raises HTTPError for 4xx/5xx status codes
        data = response.json()
        
        races = data.get('MRData', {}).get('RaceTable', {}).get('Races', [])
        if not races:
            print(f"{YELLOW}Warning: No race data found for {SEASON}{RESET}")
            return {}, {}
        
        results = races[0].get('Results', [])
        
    except requests.exceptions.Timeout:
        print(f"{YELLOW}Warning: API request timed out after {API_TIMEOUT} seconds{RESET}")
        return {}, {}
    except requests.exceptions.RequestException as e:
        print(f"{YELLOW}Warning: API request failed: {e}{RESET}")
        return {}, {}
    except (KeyError, IndexError, ValueError) as e:
        print(f"{YELLOW}Warning: Data parsing error: {e}{RESET}")
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
        print(f"{YELLOW}Warning: Failed to save driver mappings: {e}{RESET}")

    return driver_info, driver_info_constr



def fetch_constr_data(SEASON):

    print("Fetch constructor data")

    url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/last/constructorstandings/"

    try:
        response = requests.get(url)
        results = response.json()['MRData']
    except Exception as e:
        print(f"{YELLOW}Warning: Failed to fetch constructor data: {e}{RESET}")
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



def fetch_driver_standings(SEASON, driver_info_old, constr_info_old, races_to_go, sprints_to_go):

    print("Fetch driver standings")

    driver_standings = {}

    url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/last/driverStandings/"

    try:
        response = requests.get(url)
        data = response.json()
    except Exception as e:
        print(f"{YELLOW}Warning: Failed to fetch driver standings: {e}{RESET}")
        return {}, driver_info_old, constr_info_old

    standings_info = data.get("MRData", {}).get("StandingsTable", {}).get("StandingsLists", [])

    if not standings_info:
        print(f"{YELLOW}Warning: No standings data found for season {SEASON}{RESET}")
        return {}, driver_info_old, constr_info_old
    
    standings_drivers = standings_info[0].get("DriverStandings", [])

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


def fetch_driver_standings_progression(SEASON, last_completed_round):

    print("Fetch driver standings progression")

    driver_standings_progression = defaultdict(list)

    if last_completed_round == 0:
        print("No completed rounds yet, skipping results fetch")
        return driver_standings_progression
    
    start_round = max(1, last_completed_round - 2)  # Fetch last 3 rounds
    print(f"Fetching results for rounds {start_round} to {last_completed_round}")
    
    for race in range(start_round - 1, last_completed_round):

        url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/{race+1}/driverStandings/"

        try:
            response = requests.get(url)
            data = response.json()
        except Exception as e:
            print(f"{YELLOW}Warning: Failed to fetch driver standings: {e}{RESET}")
            return driver_standings_progression

        standings_info = data.get("MRData", {}).get("StandingsTable", {}).get("StandingsLists", [])

        if not standings_info:
            print(f"{YELLOW}Warning: No standings data found for round {race+1} in season {SEASON}{RESET}")
            continue
        
        standings_drivers = standings_info[0].get("DriverStandings", [])


        for driver in standings_drivers:

            driver_info = driver.get('Driver', {})
            constr_info = driver.get('Constructors', {})

            driver_id = driver_info.get('code', '')
            driver_name = driver_info.get('givenName', '') + ' ' + driver_info.get('familyName', '')
            driver_color = driver_info.get('color', '')
            round_no = race + 1
            driver_position = driver.get('position', 0)
            driver_points = driver.get('points', 0)

            driver_standings_progression[driver_id].append({
                "round": round_no,
                "points": driver_points,
                "position": driver_position
            })

        time.sleep(1)
            
    return driver_standings_progression


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
            print(f"{YELLOW}Warning: Failed to fetch results for race {race+1}: {e}{RESET}")
            continue

        # check if race data has been published yet
        if not results:
            print(f'{YELLOW}Warning: No entry for round {race+1}.{RESET}')
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
                lap_time = fastest_lap_obj['Time'].get('time')
                # save fastest lap in driver results
                fastest_lap_data = {'rank': rank, 'time': lap_time}
                # save all fastest laps per circuit
                fastest_lap_drivers = {'driver_id': driver_id, 'rank': rank, 'time': lap_time}
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
            print(f'{YELLOW}Warning: No results for round {race+1}, skipping race data.{RESET}')
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

        time.sleep(1)

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
            print(f'{YELLOW}Warning: No entry for round {race+1}.{RESET}')
            continue

        if not data:
            print(f'{YELLOW}Warning: No entry for round {race+1}.{RESET}')
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

        time.sleep(1)

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
            print(f"{YELLOW}Warning: Failed to fetch results for race {race+1}: {e}{RESET}")
            continue

        # check if race data has been published yet
        if not sprints:
            if race+1 in sprint_rounds:
                print(f"{YELLOW}Warning: No entry for round {race+1}.{RESET}")
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

        time.sleep(1)

    return sprint_dict, sprints_to_go
