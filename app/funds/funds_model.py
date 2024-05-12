from extensions import db

class BankStatement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_uploaded_date = db.Column(db.Date)

    book_date = db.Column(db.Date)
    description = db.Column(db.Text)
    ledger_balance = db.Column(db.Numeric(20, 2))
    credit = db.Column(db.Numeric(20, 2))
    debit = db.Column(db.Numeric(20, 2))
    value_date = db.Column(db.Date)
    reference_no = db.Column(db.String)
    transaction_branch = db.Column(db.Text)

    flag_description = db.Column(db.Text)

    text_remarks = db.Column(db.Text)
    current_status = db.Column(db.String)

    date_created_date = db.Column(db.DateTime)
    date_updated_date = db.Column(db.DateTime)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String)
    updated_by = db.Column(db.String)
    deleted_by = db.Column(db.String)

class FlagSheet(db.Model):
    id = db.Column(db.Integer, primary_key = True)

    flag_description = db.Column(db.Text)
    flag_reg_exp = db.Column(db.Text)

    text_remarks = db.Column(db.Text)
    current_status = db.Column(db.String)

    date_created_date = db.Column(db.DateTime)
    date_updated_date = db.Column(db.DateTime)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String)
    updated_by = db.Column(db.String)
    deleted_by = db.Column(db.String)

class DailyOutflow(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    outflow_date = db.Column(db.Date)
    outflow_amount = db.Column(db.Numeric(20, 2))
    outflow_description = db.Column(db.String)

    text_remarks = db.Column(db.Text)
    current_status = db.Column(db.String)

    date_updated_date = db.Column(db.DateTime)
    date_deleted_date = db.Column(db.DateTime)

    updated_by = db.Column(db.String)
    deleted_by = db.Column(db.String)

class DailySheet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_current_date = db.Column(db.Date)

    float_receipts = db.Column(db.Numeric(20, 2))
    float_payments = db.Column(db.Numeric(20, 2))

    text_major_collections = db.Column(db.Text)
    text_major_payments = db.Column(db.Text)

    float_amount_given_to_investments = db.Column(db.Numeric(20,2))
    float_amount_taken_from_investments = db.Column(db.Numeric(20,2))

    float_amount_hdfc_closing_balance = db.Column(db.Numeric(20, 2))
    float_amount_investment_closing_balance = db.Column(db.Numeric(20, 2))


    text_remarks = db.Column(db.Text)
    current_status = db.Column(db.String)

    date_created_date = db.Column(db.DateTime)
    date_updated_date = db.Column(db.DateTime)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String)
    updated_by = db.Column(db.String)
    deleted_by = db.Column(db.String)

class MajorOutgo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_of_outgo = db.Column(db.Date)
    float_expected_outgo = db.Column(db.Numeric(20, 2))
    text_dept = db.Column(db.Text)
    text_remarks = db.Column(db.Text)

    current_status = db.Column(db.String)

    date_created_date = db.Column(db.DateTime)
    date_updated_date = db.Column(db.DateTime)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String)
    updated_by = db.Column(db.String)
    deleted_by = db.Column(db.String)

class AmountGivenToInvestment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_given_to_investment = db.Column(db.Date)
    float_amount_given_to_investment = db.Column(db.Numeric(20, 2))
    date_expected_date_of_return = db.Column(db.Date)
    text_remarks = db.Column(db.Text)

    current_status = db.Column(db.String)

    date_created_date = db.Column(db.DateTime)
    date_updated_date = db.Column(db.DateTime)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String)
    updated_by = db.Column(db.String)
    deleted_by = db.Column(db.String)
