import os, requests, pandas as pd, matplotlib.pyplot as plt

def get_df(season=2024, rounds=24):
    rows=[]
    for rnd in range(1, rounds+1):
        r=requests.get(f"https://api.jolpi.ca/ergast/f1/{season}/{rnd}/driverStandings.json", timeout=30)
        lists=r.json().get("MRData",{}).get("StandingsTable",{}).get("StandingsLists",[])
        if not lists: continue
        for e in lists[0].get("DriverStandings",[]):
            d=e["Driver"]; name=f'{d["givenName"]} {d["familyName"]}'
            rows.append({"Round":rnd,"Driver":name,"Position":int(e["position"])})
    return pd.DataFrame(rows)

def make_png(path):
    df=get_df()
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(16,9))
    for name, g in df.groupby("Driver"):
        ax.plot(g["Round"], g["Position"], marker="o", linewidth=1, markersize=3, label=name)
    ax.invert_yaxis()
    ax.set_title("F1 2024 Driver Standings Over Races")
    ax.set_xlabel("Race Round"); ax.set_ylabel("Championship Position")
    ax.grid(True, linestyle="--", alpha=.3)
    ax.legend(loc="upper left", bbox_to_anchor=(1.02,1), frameon=False, title="Driver")
    fig.subplots_adjust(right=0.78)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)

if __name__ == "__main__":
    make_png("public/driverstandings.png")
