import os

class Config:
    # Email backend selection
    EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "imap").lower()  # 'imap' or 'gmail'
    
    # IMAP settings (for Gmail with App Password)
    IMAP_HOST = os.environ.get("IMAP_HOST", "imap.gmail.com")
    IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))
    IMAP_SSL = os.environ.get("IMAP_SSL", "true").lower() == "true"
    IMAP_USER = os.environ.get("IMAP_USER", "")
    IMAP_PASSWORD = os.environ.get("IMAP_PASSWORD", "")
    IMAP_FOLDER = os.environ.get("IMAP_FOLDER", "Idealista")  # Gmail label mapped as folder
    IMAP_SEARCH_QUERY = os.environ.get("IMAP_SEARCH_QUERY", "ALL")  # e.g. 'UNSEEN' or date filters
    MAX_EMAILS_PER_RUN = int(os.environ.get("MAX_EMAILS_PER_RUN", "200"))
    
    # Gmail API (legacy, kept for compatibility)
    GMAIL_API_KEY = os.environ.get("GMAIL_API_KEY", "")
    GMAIL_CLIENT_ID = os.environ.get("GMAIL_CLIENT_ID", "")
    GMAIL_CLIENT_SECRET = os.environ.get("GMAIL_CLIENT_SECRET", "")
    GMAIL_REFRESH_TOKEN = os.environ.get("GMAIL_REFRESH_TOKEN", "")
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
