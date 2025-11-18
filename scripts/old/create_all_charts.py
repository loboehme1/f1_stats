# scripts/charts/make_all.py
from pathlib import Path
from driverstandings import make_png as make_driverstandings
# ... import other chart builders

OUT = Path("public"); OUT.mkdir(parents=True, exist_ok=True)

def main():
    # each function writes a file into public/
    make_driverstandings(OUT / "drivers_over_races.png")
    # ... call other builders here
    # optionally also write JSON alongside PNG if you want in-app charts later

if __name__ == "__main__":
    main()
