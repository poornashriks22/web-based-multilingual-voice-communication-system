import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Mail configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') or True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # Supported languages with proper names
    LANGUAGES = {
        'en': 'English',
        'ta': 'Tamil',
        'hi': 'Hindi',
        'ml': 'Malayalam',
        'te': 'Telugu',
        'kn': 'Kannada'
    }
    
    # Correct language codes for gTTS (Indian languages need specific codes)
    GTTS_LANGUAGES = {
        'en': 'en',        # English
        'ta': 'ta',        # Tamil
        'hi': 'hi',        # Hindi
        'ml': 'ml',        # Malayalam
        'te': 'te',        # Telugu
        'kn': 'kn'         # Kannada
    }
    
    # Language codes for Indian languages (alternative)
    INDIAN_LANGUAGE_CODES = {
        'ta': 'ta',  # Tamil
        'hi': 'hi',  # Hindi
        'ml': 'ml',  # Malayalam
        'te': 'te',  # Telugu
        'kn': 'kn'   # Kannada
    }