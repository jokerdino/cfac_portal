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

    bool_jv_passed = db.Column(db.Boolean, default=False)

    # meta data
    date_created_date = db.Column(db.DateTime)
    date_updated_date = db.Column(db.DateTime)
    date_deleted_date = db.Column(db.DateTime)
    date_jv_passed_date = db.Column(db.DateTime)

    created_by = db.Column(db.String)
    updated_by = db.Column(db.String)
    deleted_by = db.Column(db.String)
    jv_passed_by = db.Column(db.String)

    def to_dict(self):
        return {
            "book_date": self.book_date,
            "description": self.description,
            "credit": self.credit,
            "debit": self.debit,
            "value_date": self.value_date,
            "reference_no": self.reference_no,
            "transaction_branch": self.transaction_branch,
            "str_regional_office_code": self.str_regional_office_code,
            "text_remarks": self.text_remarks,
            "date_updated_date": self.date_updated_date,
            "updated_by": self.updated_by,
            "id": self.id,
            "bool_jv_passed": self.bool_jv_passed,
        }


class PoolCreditsPortal(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    txt_reference_number = db.Column(db.String)
    date_value_date = db.Column(db.Date)
    amount_credit = db.Column(db.Numeric(20, 2))
    txt_name_of_remitter = db.Column(db.String)

    date_created_date = db.Column(db.DateTime)
    date_updated_date = db.Column(db.DateTime)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String)
    updated_by = db.Column(db.String)
    deleted_by = db.Column(db.String)

    def to_dict(self):
        return {
            "id": self.id,
            "txt_reference_number": self.txt_reference_number,
            "date_value_date": self.date_value_date,
            "amount_credit": self.amount_credit,
            "txt_name_of_remitter": self.txt_name_of_remitter,
            "date_created_date": self.date_created_date,
        }