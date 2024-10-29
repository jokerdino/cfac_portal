from datetime import datetime

from flask_login import current_user

from extensions import db


class Contacts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    office_code = db.Column(db.String)
    office_name = db.Column(db.String)
    name = db.Column(db.String)
    employee_number = db.Column(db.Integer)
    email_address = db.Column(db.String)
    mobile_number = db.Column(db.String)
    zone = db.Column(db.String)
    designation = db.Column(db.String)
    role = db.Column(db.String)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)
