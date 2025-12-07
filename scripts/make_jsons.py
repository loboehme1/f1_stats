"""Main orchestrator for generating F1 JSON files."""

import os
from fetchers import api_fetchers, utils
from builders import driver_json_builder, constructor_json_builder, race_json_builder, standings_json_builder
from config import OUTPUT_BASE_DIR


def make_jsons(OUT_DIR, SEASON):
    """Generate all F1 JSON files for the given season."""
    
    print("Generate jsons...")
    
    # Ensure output directories exist
    os.makedirs(os.path.join(OUT_DIR, "driver_data"), exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, "constr_data"), exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, "race_data"), exist_ok=True)
    
    # Get rounds, sprints, and last completed round
    rounds, sprints, sprint_rounds, last_completed_round = utils.count_rounds_sprints(SEASON)
    print(f"Total rounds: {rounds}, Sprints: {sprints}, Last completed round: {last_completed_round}")
    
    # Fetch all data from API
    print("Fetch driver data")
    driver_info, constr_driver_info = api_fetchers.fetch_driver_data(SEASON)
    
    print("Fetch constructor data")
    constr_info = api_fetchers.fetch_constr_data(SEASON)
    
    print("Fetch results")
    driver_results, constr_results, driver_podiums, constr_podiums, driver_dnfs, constr_dnfs, driver_disq, constr_disq, race_info, results_info, lap_info, races_to_go = api_fetchers.fetch_results(SEASON, rounds, last_completed_round)
    
    print("Fetch sprint data")
    sprint_info, sprints_to_go = api_fetchers.fetch_sprint(SEASON, rounds, sprint_rounds)
    
    print("Fetch driver standings")
    driver_standings, driver_info, constr_driver_info = api_fetchers.fetch_driver_standings(SEASON, driver_info, constr_driver_info, races_to_go, sprints_to_go)

    print("Fetch driver standings progression")
    driver_standings_progression = api_fetchers.fetch_driver_standings_progression(SEASON, last_completed_round)
    
    print("Fetch qualification data")
    quali_info, quali_race_info = api_fetchers.fetch_quali(SEASON, rounds, last_completed_round)
    
    # Build and write race JSONs first (to get recalculated constructor stats)
    race_all, race_indiv, constr_podiums_recalc, constr_dnfs_recalc, constr_disq_recalc = race_json_builder.build_and_write(
        OUT_DIR, SEASON, race_info, quali_info, quali_race_info,
        results_info, lap_info, sprint_info, last_completed_round, rounds
    )
    
    # Use recalculated constructor stats if available
    if constr_podiums_recalc is not None:
        constr_podiums = constr_podiums_recalc
        constr_dnfs = constr_dnfs_recalc
        constr_disq = constr_disq_recalc
    
    # Merge driver results with existing data (historical/previous rounds)
    driver_results = driver_json_builder.merge_driver_results(driver_results, SEASON, last_completed_round, rounds)

    # Build and write driver standings progression
    standings_json_builder.build_and_write(
        OUT_DIR, SEASON, driver_info, driver_standings_progression, last_completed_round, rounds
    )

    # Build and write driver JSONs
    driver_all, driver_indiv = driver_json_builder.build_and_write(
        OUT_DIR, SEASON, driver_info, driver_standings, driver_results,
        driver_podiums, driver_dnfs, driver_disq, last_completed_round, rounds
    )
    
    # Build and write constructor JSONs
    constr_all, constr_indiv = constructor_json_builder.build_and_write(
        OUT_DIR, SEASON, constr_info, constr_driver_info, driver_standings, driver_podiums,
        constr_results, constr_podiums, constr_dnfs, constr_disq, last_completed_round, rounds
    )
    
    print("Done!")


if __name__ == "__main__":
    # Use settings from config file
    from config import SEASON
    OUT_DIR = f'{OUTPUT_BASE_DIR}/{SEASON}/'
    make_jsons(OUT_DIR, SEASON)
