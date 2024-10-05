from datetime import datetime

from flask_login import current_user

from extensions import db


class Tickets(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    regional_office_code = db.Column(db.String)
    office_code = db.Column(db.String)
    ticket_number = db.Column(db.String)
    contact_person = db.Column(db.String)
    contact_mobile_number = db.Column(db.String)
    contact_email_address = db.Column(db.String)
    #  remarks = db.Column(db.String)
    status = db.Column(db.String)
    department = db.Column(db.String)

    date_of_creation = db.Column(db.DateTime, default=datetime.now)
    created_by = db.Column(db.String, default=lambda: current_user.username)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)


class TicketRemarks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer)
    remarks = db.Column(db.Text)

    user = db.Column(db.String, default=lambda: current_user.username)
    time_of_remark = db.Column(db.DateTime, default=datetime.now)
