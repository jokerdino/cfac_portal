from dataclasses import dataclass
from datetime import datetime

from flask_login import current_user

from extensions import db


@dataclass
class MisTracker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    txt_period = db.Column(db.String)
    txt_mis_type: str = db.Column(db.String)

    bool_mis_shared = db.Column(db.Boolean)
    date_mis_shared = db.Column(db.DateTime)
    mis_shared_by = db.Column(db.String)

    bool_brs_completed = db.Column(db.Boolean)
    date_brs_completed = db.Column(db.DateTime)
    brs_completed_by = db.Column(db.String)

    bool_jv_passed = db.Column(db.Boolean)
    date_jv_passed = db.Column(db.DateTime)
    jv_passed_by = db.Column(db.String)
