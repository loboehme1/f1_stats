"""Builder for driver JSON files."""

import json
import os
from collections import defaultdict
from itertools import chain

from helpers import normalize_driver_name, normalize_constr_name
from config import OUTPUT_BASE_DIR
from fetchers.utils import load_existing_json


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
            dd[" name"] = normalize_driver_name(dd["name"])

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


def merge_driver_results(driver_results, SEASON, last_completed_round, rounds):
    """Merge newly fetched driver results with existing data."""
    if last_completed_round == 0:
        return driver_results
    
    print(f"Merging driver data with existing data...")
    start_round = max(1, last_completed_round - 2)
    fetched_rounds = set(range(start_round, last_completed_round + 1))
    
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
    
    return driver_results


def recalculate_driver_stats(driver_results):
    """Recalculate cumulative driver stats from merged results."""
    driver_podiums = {}
    driver_dnfs = {}
    driver_disq = {}
    
    for driver_id, results in driver_results.items():
        podiums = sum(1 for r in results if int(r.get('endPos', 999)) <= 3)
        dnfs = sum(1 for r in results if r.get('status', '').lower() not in ['finished', '+1 lap', '+2 laps', '+3 laps', 'disqualified'])
        disqs = sum(1 for r in results if r.get('status', '').lower() == 'disqualified')
        driver_podiums[driver_id] = podiums
        driver_dnfs[driver_id] = dnfs
        driver_disq[driver_id] = disqs
    
    return driver_podiums, driver_dnfs, driver_disq


def build_driver_data(driver_info, driver_standings, driver_results, driver_podiums, driver_dnfs, driver_disq):
    """Combine all driver data into final structure."""
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
    
    return driver_comb_norm_all, driver_comb_norm_indiv


def write_driver_jsons(OUT_DIR, driver_all, driver_indiv):
    """Write driver JSON files."""
    driver_path = os.path.join(OUT_DIR, "driver_data")
    os.makedirs(driver_path, exist_ok=True)
    
    # Write driver_json_all.json
    driver_all_list = list(driver_all.values())
    path = os.path.join(driver_path, f"driver_json_all.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(driver_all_list, f, indent=2, ensure_ascii=False)

    # Write individual driver JSONs
    for driver_id, data in driver_indiv.items():
        path = os.path.join(driver_path, f"driver_json_{driver_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)


def build_and_write(OUT_DIR, SEASON, driver_info, driver_standings, driver_results, 
                    driver_podiums, driver_dnfs, driver_disq, last_completed_round, rounds):
    """Main entry point: merge, build, and write driver JSONs."""
    # Merge with existing data if needed
    driver_results = merge_driver_results(driver_results, SEASON, last_completed_round, rounds)
    
    # Recalculate stats from merged data
    if last_completed_round > 0 and last_completed_round < rounds:
        driver_podiums, driver_dnfs, driver_disq = recalculate_driver_stats(driver_results)
    
    # Build final data structures
    driver_all, driver_indiv = build_driver_data(
        driver_info, driver_standings, driver_results, 
        driver_podiums, driver_dnfs, driver_disq
    )
    
    # Write to files
    write_driver_jsons(OUT_DIR, driver_all, driver_indiv)
    
    return driver_all, driver_indiv
