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
    date_of_creation = db.Column(db.DateTime)


class TicketRemarks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer)

    user = db.Column(db.String)
    remarks = db.Column(db.Text)
    time_of_remark = db.Column(db.DateTime)
