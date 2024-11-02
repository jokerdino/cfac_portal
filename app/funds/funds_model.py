from datetime import datetime
from dataclasses import dataclass

from flask_login import current_user

from extensions import db


@dataclass
class FundBankStatement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_uploaded_date = db.Column(db.Date)

    book_date: datetime.date = db.Column(db.Date)
    description: str = db.Column(db.Text)
    ledger_balance = db.Column(db.Numeric(20, 2))
    credit: float = db.Column(db.Numeric(20, 2))
    debit = db.Column(db.Numeric(20, 2))
    value_date: datetime.date = db.Column(db.Date)
    reference_no: str = db.Column(db.String)
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


class FundFlagSheet(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    flag_description = db.Column(db.Text)
    flag_reg_exp = db.Column(db.Text)

    text_remarks = db.Column(db.Text)
    current_status = db.Column(db.String)

    date_created_date = db.Column(db.DateTime, default=datetime.now)
    date_updated_date = db.Column(db.DateTime, onupdate=datetime.now)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    deleted_by = db.Column(db.String)


class FundDailyOutflow(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    outflow_date = db.Column(db.Date)
    outflow_amount = db.Column(db.Numeric(20, 2))
    outflow_description = db.Column(db.String)

    text_remarks = db.Column(db.Text)
    current_status = db.Column(db.String)

    date_created_date = db.Column(db.DateTime)
    date_updated_date = db.Column(db.DateTime)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String)
    updated_by = db.Column(db.String)
    deleted_by = db.Column(db.String)


class FundDailySheet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_current_date = db.Column(db.Date)

    # float_receipts = db.Column(db.Numeric(20, 2))
    # float_payments = db.Column(db.Numeric(20, 2))

    text_major_collections = db.Column(db.Text)
    text_major_payments = db.Column(db.Text)

    float_amount_given_to_investments = db.Column(db.Numeric(20, 2))
    float_amount_taken_from_investments = db.Column(db.Numeric(20, 2))

    float_amount_hdfc_closing_balance = db.Column(db.Numeric(20, 2))
    float_amount_investment_closing_balance = db.Column(db.Numeric(20, 2))

    text_person1_name = db.Column(db.String)
    text_person1_designation = db.Column(db.String)
    text_person2_name = db.Column(db.String)
    text_person2_designation = db.Column(db.String)
    text_person3_name = db.Column(db.String)
    text_person3_designation = db.Column(db.String)
    text_person4_name = db.Column(db.String)
    text_person4_designation = db.Column(db.String)

    text_remarks = db.Column(db.Text)
    current_status = db.Column(db.String)

    date_created_date = db.Column(db.DateTime, default=datetime.now)
    date_updated_date = db.Column(db.DateTime, onupdate=datetime.now)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    deleted_by = db.Column(db.String)

    @property
    def get_net_investment(self):
        return (self.float_amount_given_to_investments or 0) - (
            self.float_amount_taken_from_investments or 0
        )


class FundMajorOutgo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_of_outgo = db.Column(db.Date)
    float_expected_outgo = db.Column(db.Numeric(20, 2))
    text_dept = db.Column(db.Text)
    text_remarks = db.Column(db.Text)

    current_status = db.Column(db.String)

    date_created_date = db.Column(db.DateTime, default=datetime.now)
    date_updated_date = db.Column(db.DateTime, onupdate=datetime.now)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    deleted_by = db.Column(db.String)


class FundAmountGivenToInvestment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_given_to_investment = db.Column(db.Date)
    float_amount_given_to_investment = db.Column(db.Numeric(20, 2))
    date_expected_date_of_return = db.Column(db.Date)
    text_remarks = db.Column(db.Text)

    current_status = db.Column(db.String)

    date_created_date = db.Column(db.DateTime, default=datetime.now)
    date_updated_date = db.Column(db.DateTime, onupdate=datetime.now)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    deleted_by = db.Column(db.String)


class FundBankAccountNumbers(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    outflow_description = db.Column(db.String)
    bank_name = db.Column(db.String)
    bank_type = db.Column(db.String)
    bank_account_number = db.Column(db.String)

    current_status = db.Column(db.String)

    date_created_date = db.Column(db.DateTime)
    date_updated_date = db.Column(db.DateTime)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String)
    updated_by = db.Column(db.String)
    deleted_by = db.Column(db.String)


@dataclass
class FundJournalVoucherFlagSheet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    txt_description: str = db.Column(db.String)
    txt_flag: str = db.Column(db.String)
    txt_gl_code: str = db.Column(db.String)
    txt_sl_code: str = db.Column(db.String)

    current_status = db.Column(db.String)

    date_created_date = db.Column(db.DateTime, default=datetime.now)
    date_updated_date = db.Column(db.DateTime, onupdate=datetime.now)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    deleted_by = db.Column(db.String)
