"""Builder for constructor JSON files."""

import json
import os
from itertools import chain

from helpers import normalize_driver_name, normalize_constr_name
from config import OUTPUT_BASE_DIR
from fetchers.utils import load_existing_json


def normalize_constr(data):
    """Dict keyed by constr_id → constructor dict."""

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


def merge_constructor_results(constr_results, SEASON, last_completed_round, rounds):
    """Merge newly fetched constructor results with existing data."""
    if last_completed_round == 0:
        return constr_results
    
    print(f"Merging constructor data with existing data...")
    start_round = max(1, last_completed_round - 2)
    fetched_rounds = set(range(start_round, last_completed_round + 1))
    
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
    
    return constr_results


def build_constructor_data(constr_info, constr_driver_info, driver_standings, driver_podiums,
                           constr_results, constr_podiums, constr_dnfs, constr_disq):
    """Combine all constructor data into final structure."""
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
    
    return constr_comb_norm_all, constr_comb_norm_indiv


def write_constructor_jsons(OUT_DIR, constr_all, constr_indiv):
    """Write constructor JSON files."""
    constr_path = os.path.join(OUT_DIR, "constr_data")
    os.makedirs(constr_path, exist_ok=True)
    
    # Write constr_json_all.json
    constr_all_list = list(constr_all.values())
    path = os.path.join(constr_path, f"constr_json_all.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(constr_all_list, f, indent=2, ensure_ascii=False)

    # Write individual constructor JSONs
    for constr_id, data in constr_indiv.items():
        path = os.path.join(constr_path, f"constr_json_{constr_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)


def build_and_write(OUT_DIR, SEASON, constr_info, constr_driver_info, driver_standings, driver_podiums,
                    constr_results, constr_podiums, constr_dnfs, constr_disq, last_completed_round, rounds):
    """Main entry point: merge, build, and write constructor JSONs."""
    # Merge with existing data if needed
    constr_results = merge_constructor_results(constr_results, SEASON, last_completed_round, rounds)
    
    # Build final data structures
    constr_all, constr_indiv = build_constructor_data(
        constr_info, constr_driver_info, driver_standings, driver_podiums,
        constr_results, constr_podiums, constr_dnfs, constr_disq
    )
    
    # Write to files
    write_constructor_jsons(OUT_DIR, constr_all, constr_indiv)
    
    return constr_all, constr_indiv
