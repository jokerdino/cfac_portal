from datetime import datetime, date

# from dataclasses import dataclass
import uuid
from typing import Optional

from sqlalchemy import Uuid
from sqlalchemy.orm import column_property, mapped_column, Mapped, relationship
from sqlalchemy.dialects.postgresql import UUID

from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


# @dataclass
class FundBankStatement(db.Model):
    id: Mapped[IntPK]
    date_uploaded_date: Mapped[date]

    book_date: Mapped[Optional[date]]
    description: Mapped[str] = mapped_column(db.Text)
    ledger_balance: Mapped[Optional[float]] = mapped_column(db.Numeric(20, 2))
    credit: Mapped[Optional[float]] = mapped_column(db.Numeric(20, 2))
    debit: Mapped[Optional[float]] = mapped_column(db.Numeric(20, 2))
    value_date: Mapped[Optional[date]] = mapped_column(db.Date)
    reference_no: Mapped[Optional[str]]
    transaction_branch: Mapped[Optional[str]] = mapped_column(db.Text)

    flag_description: Mapped[str] = mapped_column(db.Text)

    text_remarks: Mapped[Optional[str]] = mapped_column(db.Text)
    current_status: Mapped[Optional[str]]

    flag_id: Mapped[Optional[int]] = mapped_column(
        db.ForeignKey("fund_journal_voucher_flag_sheet.id"),
        index=True,
    )

    flag: Mapped[list["FundJournalVoucherFlagSheet"]] = relationship(
        back_populates="bank_statements"
    )

    batch_id: Mapped[Optional[Uuid]] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, index=True
    )

    date_created_date: Mapped[CreatedOn]
    date_updated_date: Mapped[UpdatedOn]
    date_deleted_date: Mapped[Optional[datetime]]

    created_by: Mapped[CreatedBy]
    updated_by: Mapped[UpdatedBy]
    deleted_by: Mapped[Optional[str]]

    period: Mapped[str] = column_property(db.func.to_char(value_date, "YYYY-MM"))


class FundFlagSheet(db.Model):
    id: Mapped[IntPK]
    flag_description: Mapped[str] = mapped_column(db.Text)
    flag_reg_exp: Mapped[str] = mapped_column(db.Text)

    text_remarks: Mapped[Optional[str]] = mapped_column(db.Text)
    current_status: Mapped[Optional[str]]

    date_created_date: Mapped[CreatedOn]
    date_updated_date: Mapped[UpdatedOn]
    date_deleted_date: Mapped[Optional[datetime]]

    created_by: Mapped[CreatedBy]
    updated_by: Mapped[UpdatedBy]
    deleted_by: Mapped[Optional[str]]


class FundDailyOutflow(db.Model):
    id: Mapped[IntPK]

    outflow_date: Mapped[date]
    outflow_amount: Mapped[float] = mapped_column(db.Numeric(20, 2))
    outflow_description: Mapped[str] = mapped_column(db.String)

    text_remarks: Mapped[Optional[str]] = mapped_column(db.Text)
    current_status: Mapped[Optional[str]] = mapped_column(db.String)

    date_created_date: Mapped[CreatedOn]
    date_updated_date: Mapped[UpdatedOn]
    date_deleted_date: Mapped[Optional[datetime]]

    created_by: Mapped[CreatedBy]
    updated_by: Mapped[UpdatedBy]
    deleted_by: Mapped[Optional[str]]

    normalized_description: Mapped[str] = column_property(
        db.func.replace(
            db.func.replace(db.func.upper(outflow_description), "AMOUNT_", ""), "_", " "
        )
    )


class FundDailySheet(db.Model):
    id: Mapped[IntPK]
    date_current_date: Mapped[date] = mapped_column(default=date.today)

    text_major_collections: Mapped[Optional[str]] = mapped_column(db.Text)
    text_major_payments: Mapped[Optional[str]] = mapped_column(db.Text)

    float_amount_given_to_investments: Mapped[Optional[float]] = mapped_column(
        db.Numeric(20, 2)
    )
    float_amount_taken_from_investments: Mapped[Optional[float]] = mapped_column(
        db.Numeric(20, 2)
    )

    float_amount_hdfc_closing_balance: Mapped[Optional[float]] = mapped_column(
        db.Numeric(20, 2)
    )
    float_amount_investment_closing_balance: Mapped[Optional[float]] = mapped_column(
        db.Numeric(20, 2)
    )

    text_person1_name: Mapped[Optional[str]]
    text_person1_designation: Mapped[Optional[str]]
    text_person2_name: Mapped[Optional[str]]
    text_person2_designation: Mapped[Optional[str]]
    text_person3_name: Mapped[Optional[str]]
    text_person3_designation: Mapped[Optional[str]]
    text_person4_name: Mapped[Optional[str]]
    text_person4_designation: Mapped[Optional[str]]

    text_remarks: Mapped[Optional[str]] = mapped_column(db.Text)
    current_status: Mapped[Optional[str]]

    date_created_date: Mapped[CreatedOn]
    date_updated_date: Mapped[UpdatedOn]
    date_deleted_date: Mapped[Optional[datetime]]

    created_by: Mapped[CreatedBy]
    updated_by: Mapped[UpdatedBy]
    deleted_by: Mapped[Optional[str]]

    @property
    def get_net_investment(self):
        return (self.float_amount_given_to_investments or 0) - (
            self.float_amount_taken_from_investments or 0
        )


class FundMajorOutgo(db.Model):
    id: Mapped[IntPK]
    date_of_outgo: Mapped[date]
    float_expected_outgo: Mapped[float] = mapped_column(db.Numeric(20, 2))
    text_dept: Mapped[str] = mapped_column(db.Text)
    text_remarks: Mapped[str] = mapped_column(db.Text)

    current_status: Mapped[Optional[str]]

    date_created_date: Mapped[CreatedOn]
    date_updated_date: Mapped[UpdatedOn]
    date_deleted_date: Mapped[Optional[datetime]]

    created_by: Mapped[CreatedBy]
    updated_by: Mapped[UpdatedBy]
    deleted_by: Mapped[Optional[str]]


class FundAmountGivenToInvestment(db.Model):
    id: Mapped[IntPK]
    date_given_to_investment: Mapped[date]
    float_amount_given_to_investment: Mapped[float] = mapped_column(db.Numeric(20, 2))
    date_expected_date_of_return: Mapped[Optional[date]]
    text_remarks: Mapped[Optional[str]] = mapped_column(db.Text)

    current_status: Mapped[Optional[str]]

    date_created_date: Mapped[CreatedOn]
    date_updated_date: Mapped[UpdatedOn]
    date_deleted_date: Mapped[Optional[datetime]]

    created_by: Mapped[CreatedBy]
    updated_by: Mapped[UpdatedBy]
    deleted_by: Mapped[Optional[str]]


class FundBankAccountNumbers(db.Model):
    id: Mapped[IntPK]

    outflow_description: Mapped[str]
    bank_name: Mapped[Optional[str]]
    bank_type: Mapped[Optional[str]]
    bank_account_number: Mapped[Optional[str]]

    current_status: Mapped[Optional[str]]

    date_created_date: Mapped[CreatedOn]
    date_updated_date: Mapped[UpdatedOn]
    date_deleted_date: Mapped[Optional[datetime]]

    created_by: Mapped[CreatedBy]
    updated_by: Mapped[UpdatedBy]
    deleted_by: Mapped[Optional[str]]


class FundJournalVoucherFlagSheet(db.Model):
    id: Mapped[IntPK]
    txt_description: Mapped[str]
    txt_flag: Mapped[str]
    txt_gl_code: Mapped[str]
    txt_sl_code: Mapped[str]

    current_status: Mapped[Optional[str]]

    date_created_date: Mapped[CreatedOn]
    date_updated_date: Mapped[UpdatedOn]
    date_deleted_date: Mapped[Optional[datetime]]

    created_by: Mapped[CreatedBy]
    updated_by: Mapped[UpdatedBy]
    deleted_by: Mapped[Optional[str]]
    bank_statements: Mapped["FundBankStatement"] = relationship(
        back_populates="flag",
    )
