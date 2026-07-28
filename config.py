import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-fallback-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///lms.db'
    
    # Mail Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'your_email@gmail.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'your_app_password')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'your_email@gmail.com')

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', 'your_google_client_id')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', 'your_google_client_secret')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 # 16MB max upload
