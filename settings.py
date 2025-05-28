import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory of the application
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = os.environ.get("SECRET_KEY")

# Logging configuration
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Database constants
DB_USERS = 'users'
DB_FILES = 'files'
DB_CATEGORIES = 'categories'

# MySQL Database configuration
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")

# MySQL connection string
DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Database configuration
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_recycle": 300,
    "pool_pre_ping": True
}

# Upload folder configuration
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  
# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Data storage configuration
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'txt',
    'xls', 'xlsx', 'csv',
    'ppt', 'pptx',
    'jpg', 'jpeg', 'png'
}


