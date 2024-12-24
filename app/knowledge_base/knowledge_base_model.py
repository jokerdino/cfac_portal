from datetime import datetime

from flask_login import current_user

from extensions import db


class KnowledgeBase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String)
    title = db.Column(db.String)
    knowledge_base_document = db.Column(db.String)

    is_visible = db.Column(db.Boolean)
    status = db.Column(db.Boolean)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)
