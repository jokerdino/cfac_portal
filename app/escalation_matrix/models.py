from datetime import datetime
from flask_login import current_user
from extensions import db


class EscalationMatrix(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    service_type = db.Column(db.String)
    nature_of_entity = db.Column(db.String)
    name_of_entity = db.Column(db.String)
    level = db.Column(db.String)
    name = db.Column(db.String)
    roll = db.Column(db.String)
    email_address = db.Column(db.String)
    contact_number = db.Column(db.String)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)
