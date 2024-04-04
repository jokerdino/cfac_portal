from extensions import db


class BankGuarantee(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    ro_code = db.Column(db.String)
    oo_code = db.Column(db.String)

    customer_name = db.Column(db.String)
    customer_id = db.Column(db.String)
    debit_amount = db.Column(db.Numeric(15, 2))
    credit_amount = db.Column(db.Numeric(15, 2))
    payment_id = db.Column(db.String)

    date_of_payment = db.Column(db.Date)
    reason = db.Column(db.Text)
    course_of_action = db.Column(db.Text)
