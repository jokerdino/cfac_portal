from flask_login import UserMixin

from extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ro_code = db.Column(db.String)
    oo_code = db.Column(db.String, unique=True)
    password = db.Column(db.String)
    user_type = db.Column(db.String)
    reset_password = db.Column(db.Boolean)
    time_last_login = db.Column(db.DateTime)

    @property
    def is_active(self):
        return True

    def is_authenticated(self):
        return True


class Log_user(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String)

    type_of_action = db.Column(db.String)
    time_of_action = db.Column(db.DateTime)
