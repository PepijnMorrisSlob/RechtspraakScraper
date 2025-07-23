# Configuration for Dutch Law Scraper

# Law categories to scrape
LAW_CATEGORIES = [
    "Bestuursrecht",
    "Ambtenarenrecht", 
    "Belastingrecht",
    "Bestuursprocesrecht",
    "Bestuursstrafrecht",
    "Europees Bestuursrecht",
    "Mededingingsrecht",
    "Omgevingsrecht",
    "Socialezekerheidsrecht",
    "Vreemdelingenrecht",
    "Civiel recht",
    "Aanbestedingsrecht",
    "Arbeidsrecht",
    "Burgerlijk procesrecht",
    "Europees civiel recht",
    "Goederenrecht",
    "Insolventierecht",
    "Intellectueel-eigendomsrecht",
    "Internationaal privaatrecht",
    "Ondernemingsrecht",
    "Personen- en familierecht",
    "Verbintenissenrecht",
    "Strafrecht",
    "Europees strafrecht",
    "Internationaal strafrecht",
    "Materieel strafrecht",
    "Penitentiair strafrecht",
    "Strafprocesrecht",
    "Internationaal publiekrecht",
    "Mensenrechten",
    "Volkenrecht"
]

# Current law category to scrape
CURRENT_LAW = "Vreemdelingenrecht"

# Scraping parameters
MAX_PAGES = 200
DELAY_BETWEEN_PAGES = 3  # seconds
DELAY_BETWEEN_CASES = 2   # seconds
DELAY_AFTER_ERROR = 5     # seconds

# Output settings
OUTPUT_DIR = "run"
CASE_TXT_FILE = "all_cases.txt"
METADATA_CSV_FILE = "cases_metadata.csv"

# Content extraction settings
MAX_CONTENT_LENGTH = 50000  # characters per case 