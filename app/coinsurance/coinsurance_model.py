from datetime import date
from typing import Optional

from flask import abort
from sqlalchemy.orm import Mapped, column_property, mapped_column
from sqlalchemy_continuum import make_versioned
from sqlalchemy_continuum.plugins import FlaskPlugin

from extensions import CreatedBy, CreatedOn, IntPK, UpdatedBy, UpdatedOn, db
from utils import indian_number_format

make_versioned(plugins=[FlaskPlugin()])


class Coinsurance(db.Model):
    __versioned__ = {}

    id: Mapped[IntPK]
    uiic_regional_code: Mapped[str]
    uiic_office_code: Mapped[str]
    follower_company_name: Mapped[str]
    follower_office_code: Mapped[str]

    str_period: Mapped[Optional[str]]
    type_of_transaction: Mapped[str]
    request_id: Mapped[Optional[str]]
    payable_amount: Mapped[Optional[float]] = mapped_column(db.Numeric(15, 2))
    receivable_amount: Mapped[Optional[float]] = mapped_column(db.Numeric(15, 2))
    insured_name: Mapped[Optional[str]]

    boolean_reinsurance_involved: Mapped[Optional[bool]]
    int_ri_payable_amount: Mapped[Optional[float]] = mapped_column(db.Numeric(15, 2))
    int_ri_receivable_amount: Mapped[Optional[float]] = mapped_column(db.Numeric(15, 2))

    statement: Mapped[Optional[str]]
    confirmation: Mapped[Optional[str]]
    ri_confirmation: Mapped[Optional[str]]

    current_status: Mapped[str]

    utr_number: Mapped[Optional[str]]

    created_by: Mapped[CreatedBy]
    date_created_date: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    coinsurance_remarks: Mapped[list["Remarks"]] = db.relationship(
        back_populates="coinsurance", cascade="all, delete-orphan"
    )

    def has_access(self, user) -> bool:
        role = user.user_type

        if role in ["admin", "coinsurance_hub_user"]:
            return True

        if role in ["ro_user"]:
            return user.ro_code == self.uiic_regional_code
        if role in ["oo_user"]:
            return user.oo_code == self.uiic_office_code

        return False

    def require_access(self, user):
        if not self.has_access(user):
            abort(404)

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
    id: Mapped[IntPK]

    name_of_company: Mapped[str]
    date_of_settlement: Mapped[date] = mapped_column(db.Date)
    settled_amount: Mapped[float] = mapped_column(db.Numeric(15, 2))
    utr_number: Mapped[str]
    file_settlement_file: Mapped[Optional[str]]
    type_of_transaction: Mapped[str]
    notes: Mapped[str] = mapped_column(db.Text)

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    month: Mapped[str] = column_property(db.func.to_char(date_of_settlement, "YYYY-MM"))

    def __str__(self):
        return (
            f"{self.name_of_company}-{self.utr_number} "
            f"Rs. {indian_number_format(self.settled_amount)} "
            f"on {self.date_of_settlement.strftime('%d/%m/%Y')} "
            f"({self.notes})"
        )


class Remarks(db.Model):
    id: Mapped[IntPK]
    coinsurance_id: Mapped[int] = mapped_column(db.ForeignKey("coinsurance.id"))

    user: Mapped[CreatedBy]
    remarks: Mapped[str] = mapped_column(db.Text)
    time_of_remark: Mapped[CreatedOn]

    coinsurance: Mapped["Coinsurance"] = db.relationship(
        back_populates="coinsurance_remarks"
    )


class CoinsuranceLog(db.Model):
    id: Mapped[IntPK]

    coinsurance_id: Mapped[int]

    user: Mapped[CreatedBy]
    time_of_update: Mapped[CreatedOn]

    uiic_regional_code: Mapped[str]
    uiic_office_code: Mapped[str]
    follower_company_name: Mapped[str]
    follower_office_code: Mapped[str]

    str_period: Mapped[Optional[str]]
    type_of_transaction: Mapped[str]
    request_id: Mapped[Optional[str]]
    payable_amount: Mapped[Optional[float]] = mapped_column(db.Numeric(15, 2))
    receivable_amount: Mapped[Optional[float]] = mapped_column(db.Numeric(15, 2))
    insured_name: Mapped[Optional[str]]

    boolean_reinsurance_involved: Mapped[Optional[bool]]
    int_ri_payable_amount: Mapped[Optional[float]] = mapped_column(db.Numeric(15, 2))
    int_ri_receivable_amount: Mapped[Optional[float]] = mapped_column(db.Numeric(15, 2))

    # net_amount : Mapped[int]

    statement: Mapped[Optional[str]]
    confirmation: Mapped[Optional[str]]
    ri_confirmation: Mapped[Optional[str]]

    current_status: Mapped[str]
    utr_number: Mapped[Optional[str]]


class CoinsuranceBalances(db.Model):
    id: Mapped[IntPK]
    str_zone: Mapped[str]
    str_regional_office_code: Mapped[str]

    office_code: Mapped[str]
    company_name: Mapped[str]
    period: Mapped[Optional[str]]
    hub_due_to_claims: Mapped[float]
    hub_due_to_premium: Mapped[float]
    hub_due_from_claims: Mapped[float]
    hub_due_from_premium: Mapped[float]
    oo_due_to: Mapped[float]
    oo_due_from: Mapped[float]
    net_amount: Mapped[float]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]


class CoinsuranceBalanceGeneralLedgerCodeFlagSheet(db.Model):
    id: Mapped[IntPK]

    gl_code: Mapped[str]
    description: Mapped[str]
    company_name: Mapped[Optional[str]]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]


class CoinsuranceBalanceZoneFlagSheet(db.Model):
    id: Mapped[IntPK]

    regional_code: Mapped[str]
    zone: Mapped[str]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]


class CoinsuranceCashCall(db.Model):
    id: Mapped[IntPK]

    txt_hub: Mapped[str]
    txt_ro_code: Mapped[str]
    txt_oo_code: Mapped[str]

    str_leader_follower: Mapped[str]
    txt_insured_name: Mapped[str]
    date_policy_start_date: Mapped[date]
    date_policy_end_date: Mapped[date]

    amount_total_paid: Mapped[float] = mapped_column(db.Numeric(15, 2))
    txt_remarks: Mapped[str] = mapped_column(db.Text)
    date_claim_payment: Mapped[Optional[date]]

    txt_coinsurer_name: Mapped[str]
    percent_share: Mapped[float] = mapped_column(db.Numeric(5, 2))
    amount_of_share: Mapped[float] = mapped_column(db.Numeric(15, 2))
    txt_request_id: Mapped[str]

    date_of_cash_call_raised: Mapped[date]
    txt_current_status: Mapped[str]

    txt_utr_number: Mapped[str]
    date_of_cash_call_settlement: Mapped[Optional[date]]
    amount_settlement: Mapped[Optional[date]] = mapped_column(db.Numeric(15, 2))

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]


class CoinsuranceBankMandate(db.Model):
    id: Mapped[IntPK]

    company_name: Mapped[str]
    office_code: Mapped[str]
    bank_name: Mapped[str]
    ifsc_code: Mapped[str]
    bank_account_number: Mapped[str]
    bank_mandate: Mapped[str]

    remarks: Mapped[str] = mapped_column(db.Text)

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]


class CoinsuranceReceipts(db.Model):
    id: Mapped[IntPK]

    book_date: Mapped[Optional[date]]
    description: Mapped[str]
    company_name: Mapped[str]
    credit: Mapped[float]
    value_date: Mapped[date] = mapped_column(db.Date)
    reference_no: Mapped[str]
    transaction_code: Mapped[str]
    remarks: Mapped[Optional[str]] = mapped_column(db.Text)
    status: Mapped[str]
    receipting_office: Mapped[Optional[str]]
    date_of_receipt: Mapped[Optional[date]]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    period: Mapped[str] = column_property(db.func.to_char(value_date, "Mon-YY"))


class CoinsuranceReceiptsJournalVoucher(db.Model):
    id: Mapped[IntPK]

    pattern: Mapped[Optional[str]]
    company_name: Mapped[Optional[str]]
    gl_code: Mapped[str]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]


class CoinsuranceTokenRequestId(db.Model):
    id: Mapped[IntPK]

    hub_office_code: Mapped[str]
    company_name: Mapped[str]
    coinsurer_office_code: Mapped[str]
    name_of_insured: Mapped[str]
    request_id: Mapped[str]
    amount: Mapped[float] = mapped_column(db.Numeric(15, 2))
    type_of_amount: Mapped[str]
    gl_code: Mapped[str]
    remarks: Mapped[str] = mapped_column(db.Text)
    upload_document: Mapped[Optional[str]]

    jv_gl_code: Mapped[Optional[str]]
    jv_sl_code: Mapped[Optional[str]]
    jv_passed: Mapped[Optional[bool]] = mapped_column(default=False)

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]
