"""Fetch race data specifically for the countdown component from Ergast API."""

import os
import json
import requests
from config import SEASON, OUTPUT_BASE_DIR, API_TIMEOUT

def fetch_countdown_races():
    url = f"https://api.jolpi.ca/ergast/f1/{SEASON}/races.json"
    print(f"Fetching races for countdown from {url}...")
    
    try:
        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        races_data = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
        
        countdown_races = []
        for race in races_data:
            countdown_races.append({
                "round": race.get("round"),
                "raceName": race.get("raceName"),
                "date": race.get("date"),
                "time": race.get("time", "00:00:00Z")
            })
            
        out_dir = os.path.join(OUTPUT_BASE_DIR, str(SEASON))
        os.makedirs(out_dir, exist_ok=True)
        
        out_path = os.path.join(out_dir, "countdown_races.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(countdown_races, f, indent=4)
            
        print(f"Successfully saved {len(countdown_races)} races to {out_path}")
        
    except Exception as e:
        print(f"Error fetching countdown races: {e}")

if __name__ == "__main__":
    fetch_countdown_races()
