import os


class Config:
    SECRET_KEY = "secret"  # os.urandom(32)
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_DATABASE_URI = (
        "postgresql://cfac_user:cfac_user@localhost:5432/cfac_portal"
    )
