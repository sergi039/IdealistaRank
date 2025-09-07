import os

class Config:
    # Gmail API
    GMAIL_API_KEY = os.environ.get("GMAIL_API_KEY", "")
    GMAIL_LABEL = "Idealista"
    
    # Google APIs
    GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
    
    # Database
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    
    # App settings
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    
    # Scheduler settings
    SCHEDULER_TIMEZONE = 'Europe/Madrid'  # CET timezone
    INGESTION_TIMES = ['07:00', '19:00']  # 7 AM and 7 PM CET
    
    # OSM Overpass API
    OSM_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    
    # Default scoring weights
    DEFAULT_SCORING_WEIGHTS = {
        'infrastructure_basic': 0.20,      # 20%
        'infrastructure_extended': 0.15,   # 15%
        'transport': 0.20,                 # 20%
        'environment': 0.15,               # 15%
        'neighborhood': 0.15,              # 15%
        'services_quality': 0.10,          # 10%
        'legal_status': 0.05               # 5%
    }
