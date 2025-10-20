# config.py
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.environ.get("FOOTBALL_DATA_KEY")
API_URL = "https://api.football-data.org/v4/competitions/BSA/matches?status=LIVE"
LOGO_API = "https://www.thesportsdb.com/api/v1/json/1/searchteams.php"
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", 15))
TIMEOUT = int(os.environ.get("TIMEOUT", 6))
