import os
import requests
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry



def color_for(drv):
    driver_colors = {
        # McLaren
        "Lando Norris":      "#FF8700", "Oscar Piastri":         "#FF8700",
        # Red Bull
        "Max Verstappen":    "#00008b", "Yuki Tsunoda":          "#00008b",
        # Ferrari
        "Charles Leclerc":   "#DC0000", "Lewis Hamilton":        "#DC0000",
        # Mercedes
        "George Russell":    "#00A19C", "Andrea Kimi Antonelli": "#00A19C",
        # Aston Martin
        "Fernando Alonso":   "#0A7968", "Lance Stroll":          "#0A7968",
        # Williams
        "Alexander Albon":   "#46b1eb", "Carlos Sainz":          "#46b1eb",
        # Alpine
        "Pierre Gasly":      "#f743e8", "Jack Doohan":           "#f743e8",
        "Franco Colapinto":  "#f743e8",
        # Haas
        "Esteban Ocon":      "#f04a4a", "Oliver Bearman":        "#f04a4a",
        # RB (Visa Cash App RB)
        "Liam Lawson":       "#B6BABD", "Isack Hadjar":          "#B6BABD",
        # Stake Sauber
        "Gabriel Bortoleto": "#09eb24", "Nico Hülkenberg":       "#09eb24"
    }

    return driver_colors.get(drv) or "#FFFFFF"  # default white

def _session():
    s = requests.Session()
    retry = Retry(
        total=5,                # up to 5 retries
        backoff_factor=0.7,     # 0.7s, 1.4s, 2.1s, ...
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods={"GET"},
        raise_on_status=False,
    )
    s.headers.update({"User-Agent": "f1-charts/1.0"})
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


# Fetch driver standings data from the Ergast API and return as a DataFrame
def get_df(season=2024, rounds=24):

    s = _session()
    standings = []

    for round in range(rounds):
        url = f"https://api.jolpi.ca/ergast/f1/2025/{round + 1}/driverstandings/"
        response = s.get(url)
        response.raise_for_status()  # Ensure we got a successful response
        data = response.json()

        standings_list = data.get("MRData", {}).get("StandingsTable", {}).get("StandingsLists", [])

        if not standings_list:
            print(f"No standings data for round {round + 1}")
            continue

        standings_drivers = standings_list[0].get("DriverStandings", [])

        for driver in standings_drivers:
            name = f"{driver.get("Driver", {}).get("givenName")} {driver.get("Driver", {}).get("familyName")}"
            pos = driver.get("position")
            points = driver.get("points")
            standings.append({"Round": round+1, "Driver": name, "Position": pos, "Points": points})


    # extract driver info
    series = {}  # driver -> list[(Round, Position)]
    for entry in standings:
        pos = entry["Position"]
        if pos is None:
            continue  # don't plot missing positions
        drv = entry["Driver"]
        series.setdefault(drv, []).append((int(entry["Round"]), int(pos)))

    return standings, series


# Generate and save a PNG plot of driver standings over the season
def make_line(path):
    plt.style.use("dark_background") 
    standings, series = get_df()

    make_bar("public/driverstandings_bar.png", standings)

    # Plotting
    fig, ax = plt.subplots(figsize=(12, 6), constrained_layout=False)
    fig, ax = plt.subplots(figsize=(14,6), facecolor='#111111')
    ax.set_facecolor('#111111')
    for drv, pts in series.items():
        pts.sort(key=lambda x: x[0])        # sort by Round
        xs = [r for r, _ in pts]
        ys = [p for _, p in pts]
        plt.plot(xs, ys, marker='o', linewidth=1.5, label=drv, color=color_for(drv))

    plt.gca().invert_yaxis()                 # 1st at top
    seen_rounds = sorted({s["Round"] for s in standings})
    plt.xticks(seen_rounds)
    if series:
        max_pos = max(p for pts in series.values() for _, p in pts)
        plt.yticks(range(1, max_pos + 1))

    plt.xlabel('Round')
    plt.ylabel('Position')
    plt.grid(True, linestyle='--', alpha=0.4)

    ax.legend(
        ncol=1, fontsize=8, frameon=False,
        loc='upper left', bbox_to_anchor=(1.02, 1.0), borderaxespad=0.0
    )

    plt.subplots_adjust(right=0.78)   # tweak (0.75–0.85) as needed

    os.makedirs(os.path.dirname(path), exist_ok=True)

    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)

def make_bar(path, standings):
    if standings:  # avoid ValueError on empty
        max_round = max(item["Round"] for item in standings)
        latest_entries = [item for item in standings if item["Round"] == max_round]
    else:
        latest_entries = []

    # Sort by Points descending
    data = sorted(latest_entries, key=lambda d: int(d['Points']), reverse=True)

    names  = [d['Driver'] for d in data]
    points = [int(d['Points']) for d in data]

    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(14,6), facecolor='#111111')
    ax.set_facecolor('#111111')

    bars = ax.bar(names, points, color="#69d2ed")  # light blue
    ax.set_ylabel('Points', color='white')
    ax.tick_params(axis='x', rotation=55, labelsize=9, colors='#dddddd')
    ax.tick_params(axis='y', colors='#dddddd')
    for spine in ax.spines.values():
        spine.set_color('#444')

    # value labels
    for rect, val in zip(bars, points):
        ax.text(rect.get_x()+rect.get_width()/2, val+1, str(val),
                ha='center', va='bottom', fontsize=8, color="#69d2ed")

    plt.subplots_adjust(right=0.78)   # tweak (0.75–0.85) as needed

    os.makedirs(os.path.dirname(path), exist_ok=True)

    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)

if __name__ == "__main__":
    make_line("public/driverstandings.png")
