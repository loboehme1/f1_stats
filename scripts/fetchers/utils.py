"""Utility functions for data fetching and processing."""

import json
import os
import requests
from datetime import datetime
from config import YELLOW, RESET


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


def count_rounds_sprints(SEASON):
    """
    Count total rounds, sprints, and determine last completed round.
    
    Returns:
        tuple: (count_races, count_sprints, sprint_rounds, last_completed_round)
    """
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
