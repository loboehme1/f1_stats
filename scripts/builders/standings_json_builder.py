import json
import os
from collections import defaultdict
from config import OUTPUT_BASE_DIR

from fetchers.utils import load_existing_json
from helpers import normalize_driver_name

def merge_standings_progression(driver_standings_progression, constr_standings_progression, SEASON, last_completed_round):
    """Merge newly fetched standings progression with existing data."""
    if last_completed_round == 0:
        return driver_standings_progression, constr_standings_progression
        
    print(f"Merging standings progression data...")
    start_round = max(1, last_completed_round - 2)
    fetched_rounds = set(range(start_round, last_completed_round + 1))
    
    driver_path = os.path.join(OUTPUT_BASE_DIR, str(SEASON), "driver_data")
    existing_file_driver = os.path.join(driver_path, "driver_standings_progression.json")

    constr_path = os.path.join(OUTPUT_BASE_DIR, str(SEASON), "constructor_data")
    existing_file_constr = os.path.join(constr_path, "constr_standings_progression.json")
    
    existing_data_list_driver = load_existing_json(existing_file_driver)
    existing_data_list_constr = load_existing_json(existing_file_constr)

    if existing_data_list_driver:
        existing_data_map_driver = {d['driver_id']: d for d in existing_data_list_driver}

        # Merge for each driver
        all_driver_ids = set(driver_standings_progression.keys()) | set(existing_data_map_driver.keys())
        
        for driver_id in all_driver_ids:
            new_progression = driver_standings_progression.get(driver_id, [])
            
            if driver_id in existing_data_map_driver:
                existing_entry = existing_data_map_driver[driver_id]
                existing_progression = existing_entry.get('progression', [])
                
                # Filter out rounds that we just fetched from existing data to avoid duplicates
                # (though we should trust the new fetch for those rounds)
                kept_progression = [p for p in existing_progression if int(p.get('round', 0)) not in fetched_rounds]
                
                # Combine
                combined = kept_progression + new_progression
                # Sort by round
                combined.sort(key=lambda x: int(x.get('round', 0)))
                
                # Deduplicate by round
                seen_rounds = set()
                unique_progression = []
                for p in combined:
                    r = int(p.get('round', 0))
                    if r not in seen_rounds:
                        seen_rounds.add(r)
                        unique_progression.append(p)
                
                driver_standings_progression[driver_id] = unique_progression
            else:
                # If only in existing (driver left?) or only in new (new driver?)
                # If only in new, it's already in driver_standings_progression
                if driver_id not in driver_standings_progression:
                    driver_standings_progression[driver_id] = existing_data_map_driver[driver_id].get('progression', [])


    if existing_data_list_constr:
        existing_data_map_constr = {d['constructor_id']: d for d in existing_data_list_constr}

        all_constr_ids = set(constr_standings_progression.keys()) | set(existing_data_map_constr.keys())

        for constr_id in all_constr_ids:
            new_progression = constr_standings_progression.get(constr_id, [])
            
            if constr_id in existing_data_map_constr:
                existing_entry = existing_data_map_constr[constr_id]
                existing_progression = existing_entry.get('progression', [])
                
                # Filter out rounds that we just fetched from existing data to avoid duplicates
                # (though we should trust the new fetch for those rounds)
                kept_progression = [p for p in existing_progression if int(p.get('round', 0)) not in fetched_rounds]
                
                # Combine
                combined = kept_progression + new_progression
                # Sort by round
                combined.sort(key=lambda x: int(x.get('round', 0)))
                
                # Deduplicate by round
                seen_rounds = set()
                unique_progression = []
                for p in combined:
                    r = int(p.get('round', 0))
                    if r not in seen_rounds:
                        seen_rounds.add(r)
                        unique_progression.append(p)
                
                constr_standings_progression[constr_id] = unique_progression
            else:
                # If only in existing (constructor left?) or only in new (new constructor?)
                # If only in new, it's already in constr_standings_progression
                if constr_id not in constr_standings_progression:
                    constr_standings_progression[constr_id] = existing_data_map_constr[constr_id].get('progression', [])


    return driver_standings_progression, constr_standings_progression


def build_and_write(OUT_DIR, SEASON, driver_info, constr_info, driver_standings_progression, constr_standings_progression, last_completed_round):
    """Builds and writes the driver standings progression JSON."""
    
    # Merge with existing data
    driver_standings_progression, constr_standings_progression = merge_standings_progression(driver_standings_progression, constr_standings_progression, SEASON, last_completed_round)
    
    print("Building standings progression...")
    
    # Structure: driver_id -> { info, progression: [] }
    drivers_data = {}
    constr_data = {}
    
    # Initialize drivers from driver_info
    for driver_id, info in driver_info.items():
        drivers_data[driver_id] = {
            "driver_id": driver_id,
            "code": info.get("original_driver_id", driver_id).upper()[:3], 
            "name": normalize_driver_name(info.get("name")),
            "color": info.get("colors", {}).get("primary", "#000000"),
            "progression": driver_standings_progression.get(driver_id, [])
        }

    # Initialize constructors from constr_info
    for constr_id, info in constr_info.items():
        constr_data[constr_id] = {
            "constructor_id": constr_id,
            "name": info.get("name"),
            "color": info.get("colors", {}).get("primary", "#000000"),
            "progression": constr_standings_progression.get(constr_id, [])
        }

    # Also make sure we include drivers that might be in progression but not in current driver_info (rare but possible if driver left)
    for driver_id, progression in driver_standings_progression.items():
        if driver_id not in drivers_data:
            # Try to infer basic info or skip? 
            # Ideally driver_info should have everyone who raced. 
            # If not, we might have a partial entry.
            pass

    
    # Write file
    driver_path = os.path.join(OUT_DIR, "driver_data")
    os.makedirs(driver_path, exist_ok=True)
    out_path = os.path.join(driver_path, "driver_standings_progression.json")
    
    final_output = list(drivers_data.values())
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)
        
    print(f"Written {out_path}")

    constr_path = os.path.join(OUT_DIR, "constr_data")
    os.makedirs(constr_path, exist_ok=True)
    out_path = os.path.join(constr_path, "constructor_standings_progression.json")
    
    final_output = list(constr_data.values())
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)
        
    print(f"Written {out_path}")
