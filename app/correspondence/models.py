from datetime import datetime

from flask_login import current_user

from extensions import db


class Circular(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer)
    month = db.Column(db.Integer)
    number = db.Column(db.Integer)
    date_of_issue = db.Column(db.Date)
    circular_number = db.Column(db.String)
    circular_title = db.Column(db.String)
    issued_by_name = db.Column(db.String)
    issued_by_designation = db.Column(db.String)
    mode_of_dispatch = db.Column(db.String)
    recipients = db.Column(db.String)
    number_of_copies = db.Column(db.Integer)
    date_of_acknowledgement = db.Column(db.Date)
    remarks = db.Column(db.Text)
    upload_document = db.Column(db.String)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)
    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)


class OutwardDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    date_of_dispatch = db.Column(db.Date)
    time_of_dispatch = db.Column(db.Time)
    recipient_name = db.Column(db.String)
    recipient_address = db.Column(db.Text)
    mode_of_dispatch = db.Column(db.String)
    reference_number = db.Column(db.String)
    description_of_item = db.Column(db.Text)
    sender_name = db.Column(db.String)
    dispatched_by = db.Column(db.String)
    remarks = db.Column(db.Text)
    upload_document = db.Column(db.String)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)
    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)


class InwardDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    date_of_receipt = db.Column(db.Date)
    time_of_receipt = db.Column(db.Time)
    sender_name = db.Column(db.String)
    sender_address = db.Column(db.Text)
    mode_of_receipt = db.Column(db.String)
    reference_number = db.Column(db.String)
    description_of_item = db.Column(db.Text)

    recipient_name = db.Column(db.String)
    received_by = db.Column(db.String)

    remarks = db.Column(db.Text)
    upload_document = db.Column(db.String)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)
    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)
