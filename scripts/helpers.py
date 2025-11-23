import json
import os
from config import OUTPUT_BASE_DIR, SEASON

def color_driver(drv_id, season):
    if season == "2025":
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
            "LAW": "#8A8D8F", "HAD": "#8A8D8F",
            # Stake Sauber
            "BOR": "#09eb24", "HUL": "#09eb24"
        }

        driver_colors_secondary = {
            # RB (Visa Cash App RB)
            "LAW": "#4B4B4C", "HAD": "#4B4B4C",
            "RIC": "#4B4B4C",
        }
    elif season == '2024':
        driver_colors_primary = {
            # McLaren
            "NOR": "#FF8700", "PIA": "#FF8700",
            # Red Bull
            "VER": "#00008b", "PER": "#00008b",
            # Ferrari
            "LEC": "#DC0000", "SAI": "#DC0000",
            # Mercedes
            "RUS": "#00A19C", "HAM": "#00A19C",
            # Aston Martin
            "ALO": "#0A7968", "STR": "#0A7968",
            # Williams
            "ALB": "#46b1eb", "COL": "#46b1eb",
            "SAR": "#46b1eb", 
            # Alpine
            "GAS": "#f743e8", "OCO": "#f743e8",
            "DOO": "#f743e8",
            # Haas
            "HUL": "#f04a4a", "MAG": "#f04a4a",
            # RB (Visa Cash App RB)
            "LAW": "#8A8D8F", "TSU": "#8A8D8F",
            "RIC": "#8A8D8F",
            # Stake Sauber
            "BOT": "#09eb24", "ZHO": "#09eb24"
        }

        driver_colors_secondary = {
            # RB (Visa Cash App RB)
            "LAW": "#4B4B4C", "TSU": "#4B4B4C",
            "RIC": "#4B4B4C",
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
        "rb": "#8A8D8F", 
        # Stake Sauber
        "sauber": "#09eb24"
    }

    return constr_colors.get(constr_id) or "#FFFFFF"  # default white




# Cache for loaded mappings
_driver_mappings = None

def _load_driver_mappings():
    """Load driver mappings from JSON file."""
    global _driver_mappings
    
    if _driver_mappings is not None:
        return _driver_mappings
    
    mapping_file = os.path.join(OUTPUT_BASE_DIR, str(SEASON), "driver_mappings.json")
    
    try:
        with open(mapping_file, 'r') as f:
            _driver_mappings = json.load(f)
    except FileNotFoundError:
        # This might happen if make_jsons.py hasn't run yet
        # Return empty dicts to avoid crashes, but functions will fallback
        _driver_mappings = {"id_to_code": {}, "code_to_id": {}}
    except Exception as e:
        print(f"Error loading driver mappings: {e}")
        _driver_mappings = {"id_to_code": {}, "code_to_id": {}}
    
    return _driver_mappings


def code_to_id(driver_code):
    """
    Convert driver code (e.g. 'VER') to original driver ID (e.g. 'verstappen').
    Uses dynamically generated mappings.
    """
    mappings = _load_driver_mappings()
    return mappings.get("code_to_id", {}).get(driver_code) or driver_code

def id_to_code(driver_id):
    """
    Convert driver ID from API format to driver code.
    Handles formats like 'max_verstappen' -> 'VER' or 'verstappen' -> 'VER'
    Uses dynamically generated mappings.
    """
    if not driver_id:
        return driver_id

    mappings = _load_driver_mappings()
    return mappings.get("id_to_code", {}).get(driver_id) or driver_id.upper()[:3]


def normalize_driver_name(name):
    """
    Normalize driver names to their preferred/shortened versions.
    
    Args:
        name (str): Full driver name as it appears in the API
        
    Returns:
        str: Normalized driver name
    """
    DRIVER_NAME_FIXES = {
        "Andrea Kimi Antonelli": "Kimi Antonelli",
    }
    
    return DRIVER_NAME_FIXES.get(name) or name


def normalize_constr_name(name):
    TEAM_FIX = {
        "Haas F1 Team": "Haas",
        "Alpine F1 Team": "Alpine",
        "RB F1 Team": "Racing Bulls",
        "Red Bull": "Red Bull",
        "McLaren": "McLaren",
        "Aston Martin": "Aston Martin",
        "Williams": "Williams",
        "Mercedes": "Mercedes",
        "Ferrari": "Ferrari",
        "Sauber": "Sauber",
    }
    
    return TEAM_FIX.get(name) or name
