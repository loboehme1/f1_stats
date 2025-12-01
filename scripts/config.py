# Configuration file for F1 data fetching scripts

# Season settings
SEASON = 2025
ROUNDS = 24
SPRINTS = 6

# Pagination settings
OFFSET = 0
LIMIT = 1000

# colors
YELLOW = "\033[93m"
RESET = "\033[0m"

# API settings
API_BASE_URL = "https://api.jolpi.ca/ergast/f1"
API_TIMEOUT = 30  # seconds - higher timeout in case API is busy
API_RETRY_DELAY = 0.9  # seconds between paginated requests

# Output settings
OUTPUT_BASE_DIR = "./data"

# Script behavior
SKIP_EXISTING_FILES = True  # Set to False to regenerate all files
VERBOSE_LOGGING = True  # Set to False for less output
