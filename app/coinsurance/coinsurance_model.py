from datetime import datetime
from dataclasses import dataclass
from extensions import db
from flask_login import current_user

from sqlalchemy import func
from sqlalchemy.orm import column_property


@dataclass
class Coinsurance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uiic_regional_code: str = db.Column(db.String)
    uiic_office_code: str = db.Column(db.String)
    follower_company_name: str = db.Column(db.String)
    follower_office_code: str = db.Column(db.String)

    str_period: str = db.Column(db.String)
    type_of_transaction: str = db.Column(db.String)
    request_id: str = db.Column(db.String)
    payable_amount: float = db.Column(db.Numeric(15, 2))
    receivable_amount: float = db.Column(db.Numeric(15, 2))
    insured_name: str = db.Column(db.String)

    boolean_reinsurance_involved: bool = db.Column(db.Boolean)
    int_ri_payable_amount: float = db.Column(db.Numeric(15, 2))
    int_ri_receivable_amount: float = db.Column(db.Numeric(15, 2))

    #    net_amount = db.Column(db.Integer)

    statement: str = db.Column(db.String)
    confirmation: str = db.Column(db.String)
    ri_confirmation: str = db.Column(db.String)

    current_status: str = db.Column(db.String)

    utr_number: str = db.Column(db.String)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    date_created_date = db.Column(db.DateTime, default=datetime.now)

    @property
    def zone(self):
        self.ro_code = self.uiic_regional_code

        if self.ro_code in [
            "020000",
            "060000",
            "120000",
            "160000",
            "180000",
            "190000",
            "230000",
            "270000",
            "500100",
            "020051",
        ]:
            return "West"
        elif self.ro_code in [
            "010000",
            "050000",
            "070000",
            "090000",
            "100000",
            "150000",
            "170000",
            "240000",
            "280000",
            "300000",
            "500200",
            "500400",
            "500500",
            "050051",
        ]:
            return "South"
        elif self.ro_code in [
            "040000",
            "080000",
            "110000",
            "140000",
            "200000",
            "220000",
            "250000",
            "290000",
            "500300",
            "040051",
        ]:
            return "North"
        elif self.ro_code in [
            "030000",
            "130000",
            "210000",
            "260000",
            "500700",
            "030051",
        ]:
            return "East"
        else:
            return "NA"

    @property
    def net_amount(self):
        amount = (
            (self.payable_amount or 0)
            - (self.receivable_amount or 0)
            + (self.int_ri_payable_amount or 0)
            - (self.int_ri_receivable_amount or 0)
        )
        return amount


class Settlement(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name_of_company = db.Column(db.String)
    date_of_settlement = db.Column(db.Date)
    settled_amount = db.Column(db.Numeric(15, 2))
    utr_number = db.Column(db.String)
    file_settlement_file = db.Column(db.String)
    type_of_transaction = db.Column(db.String)
    notes = db.Column(db.Text)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)

    deleted_by = db.Column(db.String)
    deleted_on = db.Column(db.DateTime)

    month = column_property(func.to_char(date_of_settlement, "YYYY-MM"))


class Remarks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coinsurance_id = db.Column(db.Integer)

    user = db.Column(db.String, default=lambda: current_user.username)
    remarks = db.Column(db.Text)
    time_of_remark = db.Column(db.DateTime, default=datetime.now)


class CoinsuranceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    coinsurance_id = db.Column(db.Integer)

    user = db.Column(db.String, default=lambda: current_user.username)
    time_of_update = db.Column(db.DateTime, default=datetime.now)

    uiic_regional_code = db.Column(db.String)
    uiic_office_code = db.Column(db.String)
    follower_company_name = db.Column(db.String)
    follower_office_code = db.Column(db.String)

    str_period = db.Column(db.String)
    type_of_transaction = db.Column(db.String)
    request_id = db.Column(db.String)
    payable_amount = db.Column(db.Numeric(15, 2))
    receivable_amount = db.Column(db.Numeric(15, 2))
    insured_name = db.Column(db.String)

    boolean_reinsurance_involved = db.Column(db.Boolean)
    int_ri_payable_amount = db.Column(db.Numeric(15, 2))
    int_ri_receivable_amount = db.Column(db.Numeric(15, 2))

    # net_amount = db.Column(db.Integer)

    statement = db.Column(db.String)
    confirmation = db.Column(db.String)
    ri_confirmation = db.Column(db.String)

    current_status = db.Column(db.String)
    utr_number = db.Column(db.String)


class CoinsuranceBalances(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    str_zone = db.Column(db.String)
    str_regional_office_code = db.Column(db.String)

    office_code = db.Column(db.String)
    company_name = db.Column(db.String)
    period = db.Column(db.String)
    hub_due_to_claims = db.Column(db.Float)
    hub_due_to_premium = db.Column(db.Float)
    hub_due_from_claims = db.Column(db.Float)
    hub_due_from_premium = db.Column(db.Float)
    oo_due_to = db.Column(db.Float)
    oo_due_from = db.Column(db.Float)
    net_amount = db.Column(db.Float)

    created_by = db.Column(db.String)
    created_on = db.Column(db.DateTime)

    updated_by = db.Column(db.String)
    updated_on = db.Column(db.DateTime)

    deleted_by = db.Column(db.String)
    deleted_on = db.Column(db.DateTime)


class CoinsuranceCashCall(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    txt_hub = db.Column(db.String)
    txt_ro_code = db.Column(db.String)
    txt_oo_code = db.Column(db.String)

    str_leader_follower = db.Column(db.String)
    txt_insured_name = db.Column(db.String)
    date_policy_start_date = db.Column(db.Date)
    date_policy_end_date = db.Column(db.Date)

    amount_total_paid = db.Column(db.Numeric(15, 2))
    txt_remarks = db.Column(db.Text)
    date_claim_payment = db.Column(db.Date)

    txt_coinsurer_name = db.Column(db.String)
    percent_share = db.Column(db.Numeric(5, 2))
    amount_of_share = db.Column(db.Numeric(15, 2))
    txt_request_id = db.Column(db.String)

    date_of_cash_call_raised = db.Column(db.Date)
    txt_current_status = db.Column(db.String)

    txt_utr_number = db.Column(db.String)
    date_of_cash_call_settlement = db.Column(db.Date)
    amount_settlement = db.Column(db.Numeric(15, 2))

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)

    deleted_by = db.Column(db.String)
    deleted_on = db.Column(db.DateTime)


@dataclass
class CoinsuranceBankMandate(db.Model):

    id: int = db.Column(db.Integer, primary_key=True)

    company_name: str = db.Column(db.String)
    office_code: str = db.Column(db.String)
    bank_name: str = db.Column(db.String)
    ifsc_code: str = db.Column(db.String)
    bank_account_number: str = db.Column(db.String)
    bank_mandate: str = db.Column(db.String)

    remarks: str = db.Column(db.Text)

    created_by: str = db.Column(db.String, default=lambda: current_user.username)
    created_on: datetime.time = db.Column(db.DateTime, default=datetime.now)

    updated_by: str = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on: datetime.time = db.Column(db.DateTime, onupdate=datetime.now)


class CoinsuranceReceipts(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    book_date = db.Column(db.Date)
    description = db.Column(db.String)
    company_name = db.Column(db.String)
    credit = db.Column(db.Float)
    value_date = db.Column(db.Date)
    reference_no = db.Column(db.String)  # , unique=True)
    transaction_code = db.Column(db.String)
    remarks = db.Column(db.Text)
    status = db.Column(db.String)
    receipting_office = db.Column(db.String)
    date_of_receipt = db.Column(db.Date)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)
