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
