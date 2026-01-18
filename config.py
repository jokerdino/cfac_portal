import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")

    WTF_CSRF_ENABLED = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI")
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER")
    UPLOAD_FOLDER_PATH = Path(UPLOAD_FOLDER)
    FLASK_ADMIN_FLUID_LAYOUT = True
    FLASK_ADMIN_SWATCH = "united"
    SERVER_NAME = os.environ.get("SERVER_NAME")
    PREFERRED_URL_SCHEME = "https"


class TestConfig(Config):
    UPLOAD_FOLDER = "/home/jokerdino/Projects/data/"
    UPLOAD_FOLDER_PATH = Path(UPLOAD_FOLDER)

    SQLALCHEMY_RECORD_QUERIES = True
    DEBUG_TB_INTERCEPT_REDIRECTS = False
