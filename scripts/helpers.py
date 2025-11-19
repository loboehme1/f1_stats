def color_driver(drv_id):
    driver_colors_primary = {
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
        "BOR": "#09eb24", "HUL": "#09eb24"
    }

    driver_colors_secondary = {
        # McLaren
        "NOR": "#B6BABD", "PIA": "#B6BABD",
        # Red Bull
        "VER": "#B6BABD", "TSU": "#B6BABD",
        # Ferrari
        "LEC": "#B6BABD", "HAM": "#B6BABD",
        # Mercedes
        "RUS": "#B6BABD", "ANT": "#B6BABD",
        # Aston Martin
        "ALO": "#B6BABD", "STR": "#B6BABD",
        # Williams
        "ALB": "#B6BABD", "SAI": "#B6BABD",
        # Alpine
        "GAS": "#B6BABD", "DOO": "#B6BABD",
        "COL": "#B6BABD",
        # Haas
        "OCO": "#B6BABD", "BEA": "#B6BABD",
        # RB (Visa Cash App RB)
        "LAW": "#4B4B4C", "HAD": "#4B4B4C",
        # Stake Sauber
        "BOR": "#B6BABD", "HUL": "#B6BABD"
    }

    primary = driver_colors_primary.get(drv_id) or "#FFFFFF" # default white
    secondary = driver_colors_secondary.get(drv_id) or "#B6BABD" # default light grey

    return primary, secondary

def color_constr(constr_id):
    constr_colors = {
        # McLaren
        "mclaren": "#FF8700",
        # Red Bull
        "red_bull": "#00008b",
        # Ferrari
        "ferrari": "#DC0000", 
        # Mercedes
        "mercedes": "#00A19C", 
        # Aston Martin
        "aston_martin": "#0A7968", 
        # Williams
        "williams": "#46b1eb", 
        # Alpine
        "alpine": "#f743e8", 
        # Haas
        "haas": "#f04a4a", 
        # RB (Visa Cash App RB)
        "rb": "#B6BABD", 
        # Stake Sauber
        "sauber": "#09eb24"
    }

    return constr_colors.get(constr_id) or "#FFFFFF"  # default white


def code_to_id(driver_id):
    driver_code = {
        # McLaren
        "NOR": "norris", "PIA": "piastri",
        # Red Bull
        "VER": "verstappen", "TSU": "tsunoda",
        # Ferrari
        "LEC": "leclerc", "HAM": "hamilton",
        # Mercedes
        "RUS": "russell", "ANT": "antonelli",
        # Aston Martin
        "ALO": "alonso", "STR": "stroll",
        # Williams
        "ALB": "albon", "SAI": "sainz",
        # Alpine
        "GAS": "gasly", "DOO": "doohan",
        "COL": "colapinto",
        # Haas
        "OCO": "ocon", "BEA": "bearman",
        # RB (Visa Cash App RB)
        "LAW": "lawson", "HAD": "hadjar",
        # Stake Sauber
        "BOR": "bortoleto", "HUL": "hulkenberg"
    }

    return driver_code.get(driver_id) or driver_id

def id_to_code(driver_id):
    driver_code = {
        # McLaren
        "norris": "NOR", "piastri": "PIA",
        # Red Bull
        "verstappen": "VER", "tsunoda": "TSU",
        # Ferrari
        "leclerc": "LEC", "hamilton": "HAM",
        # Mercedes
        "russell": "RUS", "antonelli": "ANT",
        # Aston Martin
        "alonso": "ALO", "stroll": "STR",
        # Williams
        "albon": "ALB", "sainz": "SAI",
        # Alpine
        "gasly": "GAS", "doohan": "DOO",
        "colapinto": "COL",
        # Haas
        "ocon": "OCO", "bearman": "BEA",
        # RB (Visa Cash App RB)
        "lawson": "LAW", "hadjar": "HAD",
        # Stake Sauber
        "bortoleto": "BOR", "hulkenberg": "HUL"
    }

    return driver_code.get(driver_id) or driver_id
