import os
import requests
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from collections import defaultdict

def color_for(drv):
    driver_colors = {
        # McLaren
        "NOR": "#FF8700", "PIA": "#FF8700",
        # Red Bull
        "VER": "#00008b", "TSU": "#00008b",
        # Ferrari
        "LEC": "#DC0000", "HAM": "#DC0000",
        # Mercedes
        "RUS": "#00A19C", "ANT": "#00A19C",
        # Aston Martin
        "ALO": "#0A7968", "STR": "#0A7968",
        # Williams
        "ALB": "#46b1eb", "SAI": "#46b1eb",
        # Alpine
        "GAS": "#f743e8", "DOO": "#f743e8",
        "COL": "#f743e8",
        # Haas
        "OCO": "#f04a4a", "BEA": "#f04a4a",
        # RB (Visa Cash App RB)
        "LAW": "#B6BABD", "HAD": "#B6BABD",
        # Stake Sauber
        "BOR": "#09eb24", "HUL": "#09eb24",
    }
    return driver_colors.get(drv)

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

def get_df(season=2025, rounds=24):

    s = _session()
    standings = []

    driver_pos_per_round = defaultdict(list) 

    for round in range(rounds):
        url = f"https://api.jolpi.ca/ergast/f1/{season}/{round + 1}/results/"
        response = s.get(url)
        response.raise_for_status()  # Ensure we got a successful response
        data = response.json()

        races_list = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])

        if not races_list:
            print(f"No race data for round {round + 1}")
            continue

        races = races_list[0].get("Results", [])

        for position in races:
            code = f"{position.get("Driver", {}).get("code")}"
            pos = position.get("position")
            points = position.get("points")
            driver_pos_per_round[code].append({'round': round+1, 'points': points, 'position': pos})  

    return driver_pos_per_round

def make_line(folder):

    MAX_ROUNDS_DISPLAY = 20          # x-axis 1..20 always
    Y_MAX_DISPLAY = 26               # optional: constant y-axis upper bound
    Y_LOW_DISPLAY = -1               # optional: constant y-axis lower bound

    plt.style.use('dark_background')
    os.makedirs(folder, exist_ok=True)

    driver_pos_per_round = get_df()

    if driver_pos_per_round == {}:
        print(f"No driver positions data for round {round + 1}")
        return

    for code in sorted(driver_pos_per_round):
        results = sorted(driver_pos_per_round[code], key=lambda r: r['round'])
        r2p = {r['round']: float(r['points']) for r in results}

        xs = list(range(1, MAX_ROUNDS_DISPLAY + 1))
        ys = [r2p.get(x, np.nan) for x in xs]   # NaN => gaps, no fake zeros

        clr = color_for(code) or "#CCCCCC"      # fallback if code not in map

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(xs, ys,
                marker='o', linewidth=2, markersize=4, label=code,
                color=clr, markerfacecolor=clr, markeredgecolor=clr)

        ax.set_title(f"{code} — Points per Race (2025)")
        ax.set_xlabel("Round"); ax.set_ylabel("Points")
        ax.set_xlim(1, MAX_ROUNDS_DISPLAY); ax.set_xticks(xs)
        # Optional fixed Y axis:
        ax.set_ylim(Y_LOW_DISPLAY, Y_MAX_DISPLAY)

        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left')

        os.makedirs(f"{folder}/{code}", exist_ok=True)
        out = f"{folder}/{code}/race_results.png"
        fig.savefig(out, dpi=200, bbox_inches="tight")
        plt.close(fig)
        print("[ok] saved", os.path.abspath(out))

if __name__ == "__main__":
    make_line("public")

