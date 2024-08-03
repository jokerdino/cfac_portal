from extensions import db


class PoolCredits(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    date_uploaded_date = db.Column(db.Date)

    # below columns are uploaded from bank statement excel
    book_date = db.Column(db.Date)
    description = db.Column(db.Text)
    ledger_balance = db.Column(db.Numeric(20, 2))
    credit = db.Column(db.Numeric(20, 2))
    debit = db.Column(db.Numeric(20, 2))
    value_date = db.Column(db.Date)
    reference_no = db.Column(db.String)
    transaction_branch = db.Column(db.Text)

    # flag description is assigned from our table
    flag_description = db.Column(db.Text)

    # user inputs

    # regional office users will self assign the credits to their RO
    str_regional_office_code = db.Column(db.String)
    text_remarks = db.Column(db.Text)

    # meta data
    date_created_date = db.Column(db.DateTime)
    date_updated_date = db.Column(db.DateTime)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String)
    updated_by = db.Column(db.String)
    deleted_by = db.Column(db.String)
