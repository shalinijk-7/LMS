"""
Configuration settings for the LMS application.
Loads environment variables and defines the configuration class.
"""
import os
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

class Config:
    """
    Base configuration class containing application settings for
    database, mail, OAuth, and file uploads.
    """
    # Secret key for session management and CSRF protection. Fallback used only in dev.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-fallback-secret-key'
    # SQLAlchemy database URI. Defaults to a local SQLite database named lms.db.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///lms.db'
    
    # Mail Configuration: Settings for Flask-Mail to handle outgoing emails
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'your_email@gmail.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'your_app_password')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'your_email@gmail.com')

    # Google OAuth Configuration: Credentials for Google Sign-In integration
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', 'your_google_client_id')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', 'your_google_client_secret')

    # Gemini AI Configuration: API key for AI-powered features
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

    # Disable SQLAlchemy event system to save memory
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Absolute path to the directory where user-uploaded files will be stored
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    # Restrict maximum allowed payload to 16 megabytes
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 # 16MB max upload
