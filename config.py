import os


class Config:
    SECRET_KEY = os.urandom(32)

    WTF_CSRF_ENABLED = True
    SQLALCHEMY_DATABASE_URI = (
        "postgresql://cfac_user:cfac_user@localhost:5432/cfac_portal"
    )
    UPLOAD_FOLDER = "/home/barneedhar/Projects/data/"

    FLASK_ADMIN_FLUID_LAYOUT = True
    FLASK_ADMIN_SWATCH = "united"


class TestConfig:
    SECRET_KEY = "secret"

    WTF_CSRF_ENABLED = True
    SQLALCHEMY_DATABASE_URI = (
        "postgresql://cfac_user:cfac_user@localhost:5432/cfac_portal"
    )
    UPLOAD_FOLDER = "/home/jokerdino/Projects/data/"

    FLASK_ADMIN_FLUID_LAYOUT = True
    FLASK_ADMIN_SWATCH = "united"
