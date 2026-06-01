from abc import ABC, abstractmethod
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import uuid

import pandas as pd
from sqlalchemy import insert, update, select

from app.pool_credits.pool_credits_model import PoolCredits
from .funds_model import (
    FundDailySheet,
    FundBankStatement,
    FundJournalVoucherFlagSheet,
    FundFlagSheet,
)
from .funds_utils import get_previous_day_closing_balance_refactored, get_daily_sheet


class BaseBankStatementService(ABC):
    def __init__(self, session):
        self.session = session

    def process(self, file, user):
        df, closing_balance = self.parse_bank_statement(file)
        df = self._normalize(df, user)
        df = self._apply_flags(df)
        self._verify_closing_balance(df, closing_balance)
        self._persist(df, closing_balance)

    @abstractmethod
    def parse_bank_statement(self, file) -> tuple[pd.DataFrame, float]:
        """
        Parse the raw file.
        Must return (df, closing_balance) so the base class can route both.
        """

    @abstractmethod
    def _verify_closing_balance(self, df: pd.DataFrame, closing_balance: float) -> None:
        """Raise ValueError if the closing balance does not reconcile."""

    def _normalize(self, df: pd.DataFrame, user) -> pd.DataFrame:
        df.columns = df.columns.str.lower().str.replace(" ", "_")
        df["date_uploaded_date"] = date.today()
        df["date_created_date"] = datetime.now()
        df["created_by"] = user.username
        df["batch_id"] = str(uuid.uuid4())
        return df

    def _get_flag_sheet(self) -> pd.DataFrame:
        stmt = select(FundFlagSheet.flag_description, FundFlagSheet.flag_reg_exp)
        result = self.session.execute(stmt)
        return pd.DataFrame(result.fetchall(), columns=result.keys())

    def _apply_flags(self, df: pd.DataFrame) -> pd.DataFrame:
        flag_sheet = self._get_flag_sheet()

        # Sort flag sheet by string length descending
        flag_sheet = flag_sheet.dropna(subset=["flag_reg_exp"]).copy()
        flag_sheet["len"] = flag_sheet["flag_reg_exp"].astype(str).str.len()
        flag_sheet = flag_sheet.sort_values(by="len", ascending=False)

        patterns = [
            (str(pattern), str(flag))
            for pattern, flag in zip(
                flag_sheet["flag_reg_exp"], flag_sheet["flag_description"]
            )
        ]

        # Helper function to find the first substring match
        def find_flag(desc: str) -> str:
            for substring, flag in patterns:
                if substring in desc:
                    return flag
            return "OTHER RECEIPTS"

        df["flag_description"] = [find_flag(str(d)) for d in df["description"]]

        return df

    def _persist(self, df: pd.DataFrame, closing_balance: float) -> None:
        try:
            self._insert_bank_statement(df)
            self._update_jv_flags(df["batch_id"].iloc[0])
            self._insert_pool_credits(df["batch_id"].iloc[0])
            self._upsert_daily_sheet(closing_balance)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def _insert_bank_statement(self, df: pd.DataFrame) -> None:
        for col in ["value_date", "book_date"]:
            if col in df.columns:
                df[col] = pd.to_datetime(
                    df[col], errors="coerce", dayfirst=True
                ).dt.date

        for col in ["ledger_balance", "credit", "debit"]:
            if col in df.columns:
                df[col] = df[col].fillna(0)

        df = df.where(pd.notnull(df), None)
        self.session.execute(insert(FundBankStatement), df.to_dict(orient="records"))

    def _update_jv_flags(self, batch_id: str) -> None:
        """
        For rows in this batch that still have no flag_id, attempt to match
        against the JournalVoucher flag sheet via a DB-side update.
        """
        stmt = (
            update(FundBankStatement)
            .values(flag_id=FundJournalVoucherFlagSheet.id)
            .where(
                FundBankStatement.flag_id.is_(None),
                FundBankStatement.batch_id == batch_id,
                FundBankStatement.description.contains(
                    FundJournalVoucherFlagSheet.pattern
                ),
            )
        )
        self.session.execute(stmt)

    def _insert_pool_credits(self, batch_id: str) -> None:
        """Copy unidentified OTHER RECEIPTS rows into the pool credits table."""
        cols = [
            FundBankStatement.book_date,
            FundBankStatement.description,
            FundBankStatement.ledger_balance,
            FundBankStatement.credit,
            FundBankStatement.debit,
            FundBankStatement.value_date,
            FundBankStatement.reference_no,
            FundBankStatement.transaction_branch,
            FundBankStatement.date_uploaded_date,
            FundBankStatement.batch_id,
            FundBankStatement.flag_description,
        ]
        pool_cols = [
            PoolCredits.book_date,
            PoolCredits.description,
            PoolCredits.ledger_balance,
            PoolCredits.credit,
            PoolCredits.debit,
            PoolCredits.value_date,
            PoolCredits.reference_no,
            PoolCredits.transaction_branch,
            PoolCredits.date_uploaded_date,
            PoolCredits.batch_id,
            PoolCredits.flag_description,
        ]

        source = select(*cols).where(
            FundBankStatement.batch_id == batch_id,
            FundBankStatement.flag_description == "OTHER RECEIPTS",
            FundBankStatement.flag_id.is_(None),
        )
        self.session.execute(insert(PoolCredits).from_select(pool_cols, source))

    def _upsert_daily_sheet(self, closing_balance: float) -> None:
        daily_sheet = get_daily_sheet(date.today())
        if not daily_sheet:
            daily_sheet = FundDailySheet()
            self.session.add(daily_sheet)
        daily_sheet.float_amount_hdfc_closing_balance = closing_balance


class BankStatementService(BaseBankStatementService):
    def parse_bank_statement(self, file) -> tuple[pd.DataFrame, float]:
        df = pd.read_excel(
            file,
            parse_dates=["Book Date", "Value Date"],
            date_format="dd-mm-yyyy",
            dtype={
                "Description": str,
                "Ledger Balance": float,
                "Credit": float,
                "Debit": float,
                "Reference No": str,
                "Transaction Branch": str,
            },
        )
        # closing balance is embedded as a row; extract after flagging
        # return a sentinel so _verify_closing_balance can locate it later
        return df, None

    def _normalize(self, df: pd.DataFrame, user) -> pd.DataFrame:
        df = super()._normalize(df, user)

        # Move debit amounts into credit column, clear debit
        mask = df["debit"].notnull()
        df.loc[mask, "credit"] = df.loc[mask, "debit"]
        df.loc[mask, "debit"] = None

        return df

    def _verify_closing_balance(self, df: pd.DataFrame, closing_balance: float) -> None:
        """
        For this format the closing balance is embedded as a tagged row
        in the statement itself, so we derive it from the dataframe.
        """
        closing_balance_prev = get_previous_day_closing_balance_refactored(
            date.today() + relativedelta(days=1), "hdfc_closing_balance"
        )

        sum_credits = df["credit"].sum()
        sum_debits = df["debit"].fillna(0).sum()

        try:
            closing_balance_stmt = df.loc[
                df["flag_description"] == "HDFC CLOSING BAL", "ledger_balance"
            ].item()
        except ValueError:
            raise ValueError(
                "Closing balance entry not found in the uploaded statement."
            )

        expected = float(closing_balance_prev) + sum_credits - sum_debits
        if abs(expected - closing_balance_stmt) > 0.001:
            raise ValueError(
                f"Mismatch in closing balance. "
                f"Uploaded: {closing_balance_stmt}, Expected: {expected}"
            )

    def _persist(self, df: pd.DataFrame, closing_balance: float) -> None:
        # For this format the closing balance lives inside the df
        closing_balance = df.loc[
            df["flag_description"] == "HDFC CLOSING BAL", "ledger_balance"
        ].item()
        super()._persist(df, closing_balance)


class BankStatementServiceCBX(BaseBankStatementService):
    def parse_bank_statement(self, file) -> tuple[pd.DataFrame, float]:
        # Closing balance lives in the summary block at the top
        df_summary = pd.read_excel(file, skiprows=3, nrows=10, header=None)
        mask = df_summary.iloc[:, 0].astype(str).str.strip() == "Closing Balance"
        closing_balance = float(df_summary.loc[mask, 1].iloc[0])

        df = pd.read_excel(
            file,
            skiprows=14,
            parse_dates=["Transaction Date", "Value Date"],
            date_format="dd/mm/yyyy",
            dtype={
                "Transaction Description": str,
                "Transaction Amount": float,
                "Debit / Credit": str,
                "Reference No.": str,
            },
        )
        df = df.rename(
            columns={
                "Transaction Date": "Book Date",
                "Transaction Description": "Description",
                "Transaction Amount": "Credit",
                "Running balance": "Ledger Balance",
                "Debit / Credit": "Debit",
                "Reference No.": "Reference No",
            }
        )
        return df, closing_balance

    def _normalize(self, df: pd.DataFrame, user) -> pd.DataFrame:
        df = super()._normalize(df, user)

        # CBX marks debits with "D" in a text column; flip the sign on credit
        df.loc[df["debit"] == "D", "credit"] *= -1
        df["debit"] = None

        return df

    def _verify_closing_balance(self, df: pd.DataFrame, closing_balance: float) -> None:
        """
        For CBX, after normalisation debits are already folded into credit
        as negative values, so summing credit alone gives the net movement.
        """
        closing_balance_prev = get_previous_day_closing_balance_refactored(
            date.today() + relativedelta(days=1), "hdfc_closing_balance"
        )

        net_movement = df["credit"].sum()  # debits are negative credits here
        expected = float(closing_balance_prev) + net_movement

        if abs(expected - closing_balance) > 0.001:
            raise ValueError(
                f"Mismatch in closing balance. "
                f"Uploaded: {closing_balance}, Expected: {expected}"
            )
