"""Builder for race JSON files."""

import json
import os
from itertools import chain

from config import OUTPUT_BASE_DIR
from fetchers.utils import load_existing_json


def merge_race_data(race_info, results_info, lap_info, quali_info, SEASON, last_completed_round, rounds):
    """Merge newly fetched race data with existing data."""
    if last_completed_round == 0:
        return race_info, results_info, lap_info, quali_info
    
    print(f"Merging race data with existing data...")
    
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
            
            # Load detailed race data from individual race JSON files
            if circuit_id not in results_info or circuit_id not in lap_info or circuit_id not in quali_info:
                individual_race_file = os.path.join(race_dir, f'race_json_{circuit_id}.json')
                existing_race_data = load_existing_json(individual_race_file)
                
                if existing_race_data:
                    # Load race results if not already fetched
                    if circuit_id not in results_info:
                        results_info[circuit_id] = existing_race_data.get('race_results', [])
                    
                    # Load fastest laps if not already fetched
                    if circuit_id not in lap_info:
                        lap_info[circuit_id] = existing_race_data.get('fastest_laps', [])
                    
                    # Load qualifying results if not already fetched
                    if circuit_id not in quali_info:
                        quali_info[circuit_id] = existing_race_data.get('quali_results', [])
    
    return race_info, results_info, lap_info, quali_info


def recalculate_constructor_stats(race_info, results_info):
    """Recalculate constructor stats from all race results."""
    constr_podiums = {}
    constr_dnfs = {}
    constr_disq = {}
    
    # Recalculate constructor stats from ALL race results
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
    
    return constr_podiums, constr_dnfs, constr_disq


def build_race_data(race_info, quali_info, quali_race_info, results_info, lap_info, sprint_info):
    """Combine all race data into final structure."""
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
        

        race_comb_all[rid] = race_core_all
        race_comb_indiv[rid] = race_core_indiv

    return race_comb_all, race_comb_indiv


def write_race_jsons(OUT_DIR, race_all, race_indiv):
    """Write race JSON files."""
    race_path = os.path.join(OUT_DIR, "race_data")
    os.makedirs(race_path, exist_ok=True)
    
    # Write race_json_all.json
    race_all_list = list(race_all.values())
    path = os.path.join(race_path, f"race_json_all.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(race_all_list, f, indent=2, ensure_ascii=False)

    # Write individual race JSONs
    for circuit_id, data in race_indiv.items():
        path = os.path.join(race_path, f"race_json_{circuit_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)


def build_and_write(OUT_DIR, SEASON, race_info, quali_info, quali_race_info, 
                    results_info, lap_info, sprint_info, last_completed_round, rounds):
    """Main entry point: merge, build, and write race JSONs."""
    # Merge with existing data if needed
    race_info, results_info, lap_info, quali_info = merge_race_data(
        race_info, results_info, lap_info, quali_info, SEASON, last_completed_round, rounds
    )
    
    # Recalculate constructor stats from merged race data
    constr_podiums, constr_dnfs, constr_disq = None, None, None
    if last_completed_round > 0 and last_completed_round < rounds:
        constr_podiums, constr_dnfs, constr_disq = recalculate_constructor_stats(race_info, results_info)
    
    # Build final data structures
    race_all, race_indiv = build_race_data(
        race_info, quali_info, quali_race_info, results_info, lap_info, sprint_info
    )
    
    # Write to files
    write_race_jsons(OUT_DIR, race_all, race_indiv)
    
    return race_all, race_indiv, constr_podiums, constr_dnfs, constr_disq
