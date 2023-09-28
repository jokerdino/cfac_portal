import os


class Config:
    SECRET_KEY = os.urandom(32)
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_DATABASE_URI = (
        "postgresql://barneedhar:barneedhar@localhost:5432/coinsurance"
    )
