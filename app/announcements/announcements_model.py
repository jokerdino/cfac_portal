from datetime import datetime

from flask_login import current_user

from extensions import db


class Announcements(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    txt_title = db.Column(db.Text)
    txt_message = db.Column(db.Text)
