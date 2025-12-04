import json
import os
from collections import defaultdict
from config import OUTPUT_BASE_DIR

def build_and_write(OUT_DIR, SEASON, driver_info, driver_results, last_completed_round, rounds):
    """Builds and writes the driver standings progression JSON."""
    
    print("Building driver standings progression...")
    
    # Structure: driver_id -> { info, progression: [] }
    drivers_data = {}
    
    # Initialize drivers from driver_info
    for driver_id, info in driver_info.items():
        drivers_data[driver_id] = {
            "driver_id": driver_id,
            "code": info.get("original_driver_id", driver_id).upper()[:3], 
            "name": info.get("name"),
            "color": info.get("colors", {}).get("primary", "#000000"),
            "progression": []
        }

    # Pivot results: Round -> Driver -> Points
    round_results = defaultdict(dict) # round -> driver_id -> points_in_that_round
    
    for driver_id, results in driver_results.items():
        for result in results:
            try:
                r = int(result.get("round", 0))
                p = float(result.get("points", 0))
                round_results[r][driver_id] = p
            except (ValueError, TypeError):
                continue
            
    # Calculate cumulative points and positions for each round
    cumulative_points = defaultdict(float) # driver_id -> total_points
    
    # Iterate from round 1 to last_completed_round
    for r in range(1, last_completed_round + 1):
        # Update cumulative points with results from this round
        current_round_points = round_results.get(r, {})
        for driver_id, points in current_round_points.items():
            cumulative_points[driver_id] += points
            
        # Create a list to sort for this round
        standings = []
        # We include all drivers who have points so far or are in the current round
        # Actually, we should include all drivers in driver_info to show their position even if 0 points?
        # Typically standings show everyone.
        
        for driver_id in drivers_data.keys():
            total = cumulative_points.get(driver_id, 0)
            standings.append({"driver_id": driver_id, "points": total})
            
        # Sort by points desc
        # Secondary sort could be wins, but we don't have wins easily accessible here without more processing.
        # For now, simple points sort.
        standings.sort(key=lambda x: x["points"], reverse=True)
        
        # Assign positions
        for i, entry in enumerate(standings):
            pos = i + 1
            driver_id = entry["driver_id"]
            
            # Add to driver's progression
            if driver_id in drivers_data:
                drivers_data[driver_id]["progression"].append({
                    "round": r,
                    "points": entry["points"],
                    "position": pos
                })
                
    # Convert to list and sort by current (final) position
    final_output = list(drivers_data.values())
    
    # Sort final output by the position in the last round
    # We can use the last entry in progression
    final_output.sort(key=lambda x: x["progression"][-1]["position"] if x["progression"] else 999)
    
    # Write file
    driver_path = os.path.join(OUT_DIR, "driver_data")
    os.makedirs(driver_path, exist_ok=True)
    out_path = os.path.join(driver_path, "driver_standings_progression.json")
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)
        
    print(f"Written {out_path}")
