from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from math import fabs
import uuid

import pandas as pd
from sqlalchemy import insert, update, select

# from flask_login import current_user

# from extensions import db
from app.pool_credits.pool_credits_model import PoolCredits

from .funds_model import (
    FundDailySheet,
    FundBankStatement,
    FundJournalVoucherFlagSheet,
    FundFlagSheet,
)
from .funds_utils import get_previous_day_closing_balance_refactored, get_daily_sheet


class BankStatementService:
    def __init__(self, session):
        self.session = session

    # self.engine = engine

    def process(self, file, user):
        df = self.parse_bank_statement(file)
        df = self.normalize_bank_statement(df, user)
        df_flag_sheet = self.get_flag_sheet()
        df = self.add_flag(df, df_flag_sheet)

        # if not
        self.verify_closing_balance(df)
        #           raise ValueError("Closing balance mismatch")

        self.save_bank_statement_and_credits(df)

    def parse_bank_statement(self, file) -> pd.DataFrame:
        return pd.read_excel(
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

    def normalize_bank_statement(self, df: pd.DataFrame, user) -> pd.DataFrame:
        df.columns = df.columns.str.lower().str.replace(" ", "_")
        df["date_uploaded_date"] = date.today()
        df["date_created_date"] = datetime.now()
        df["created_by"] = user.username

        # assign same batch_id to all rows in this upload
        df["batch_id"] = str(uuid.uuid4())

        # Move debit values to credit, nullify debit
        mask = df["debit"].notnull()
        df.loc[mask, "credit"] = df.loc[mask, "debit"]
        df.loc[mask, "debit"] = None

        return df

    def verify_closing_balance(self, df: pd.DataFrame) -> bool:
        closing_balance_prev = get_previous_day_closing_balance_refactored(
            date.today() + relativedelta(days=1), "hdfc_closing_balance"
        )

        sum_credits = df["credit"].sum()
        sum_debits = df["debit"].sum()

        try:
            closing_balance_stmt = df.loc[
                df["flag_description"] == "HDFC CLOSING BAL", "ledger_balance"
            ].item()
        except ValueError:
            raise ValueError(
                "Closing balance entry not found in the uploaded statement."
            )
            # return False

        expected_closing = float(closing_balance_prev) + sum_credits - sum_debits

        if fabs(expected_closing - closing_balance_stmt) > 0.001:
            raise ValueError(
                f"Mismatch in closing balance. Uploaded: {closing_balance_stmt}, Expected: {expected_closing}"
            )
            # return False

        return True

    def save_bank_statement_and_credits(self, df: pd.DataFrame):
        try:
            # Save full bank statement
            # Parse date columns
            date_cols = ["value_date", "book_date"]

            for col in date_cols:
                df[col] = pd.to_datetime(
                    df[col],
                    errors="coerce",
                ).dt.date

            cols = ["ledger_balance", "credit", "debit"]
            existing = [c for c in cols if c in df.columns]

            df[existing] = df[existing].fillna(0)

            # Replace NaN/NaT with None for SQLAlchemy
            df = df.where(pd.notnull(df), None)
            self.session.execute(
                insert(FundBankStatement), df.to_dict(orient="records")
            )
            #  db.session.commit()

            #    df.to_sql("fund_bank_statement", db.engine, if_exists="append", index=False)

            batch_id = df["batch_id"].iloc[0]

            stmt = (
                update(FundBankStatement)
                .values(flag_id=FundJournalVoucherFlagSheet.id)
                .where(
                    FundBankStatement.flag_id.is_(None),
                    FundBankStatement.batch_id == batch_id,
                    FundBankStatement.description.contains(
                        FundJournalVoucherFlagSheet.txt_description
                    ),
                )
            )

            self.session.execute(stmt)
            #  db.session.commit()
            unidentified_stmt = select(
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
            ).where(
                FundBankStatement.batch_id == batch_id,
                FundBankStatement.flag_description == "OTHER RECEIPTS",
                FundBankStatement.flag_id.is_(None),
            )

            insert_stmt = insert(PoolCredits).from_select(
                [
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
                ],
                unidentified_stmt,
            )
            self.session.execute(insert_stmt)

        except Exception:
            self.session.rollback()
            raise
        # Filter and process "Other Receipts"
        # other_receipts = df[df["flag_description"] == "OTHER RECEIPTS"]
        # unidentified_credits = filter_unidentified_credits(other_receipts)

        # Upload unidentified credits
        # unidentified_credits.to_sql(
        #     "pool_credits", db.engine, if_exists="append", index=False
        # )

        # # Upload to pool credits portal
        # df_portal = prepare_dataframe(unidentified_credits)
        # df_portal.to_sql("pool_credits_portal", db.engine, if_exists="append", index=False)

        # Update daily sheet
        closing_balance = df.loc[
            df["flag_description"] == "HDFC CLOSING BAL", "ledger_balance"
        ].item()
        self.create_or_update_daily_sheet(closing_balance)
        self.session.commit()

    def create_or_update_daily_sheet(self, closing_balance_statement):
        daily_sheet = get_daily_sheet(date.today())
        # if there is no daily sheet created for the day, initiate blank daily sheet

        if not daily_sheet:
            daily_sheet = FundDailySheet()
            self.session.add(daily_sheet)

        daily_sheet.float_amount_hdfc_closing_balance = closing_balance_statement

    #   def get_flag_sheet(self):
    #      return pd.read_sql("fund_flag_sheet", self.engine)

    def get_flag_sheet(self):
        stmt = select(
            FundFlagSheet.flag_description,
            FundFlagSheet.flag_reg_exp,
        )
        result = self.session.execute(stmt)
        return pd.DataFrame(result.fetchall(), columns=result.keys())

    def add_flag(self, df_bank_statement, df_flag_sheet):
        # obtain flag from database and store it as pandas dataframe
        # df_flag_sheet = pd.read_sql("fund_flag_sheet", self.engine)
        # df_flag_sheet = df_flag_sheet[["flag_description", "flag_reg_exp"]]

        # extract regular expression column into list
        reg_exp = df_flag_sheet["flag_reg_exp"].unique().tolist()

        # add new column flag_reg_exp wherever the description matches the regular_expression
        df_bank_statement["flag_reg_exp"] = df_bank_statement["description"].apply(
            lambda x: "".join([part for part in reg_exp if part in str(x)])
        )

        # use the newly created column to merge with uploaded bank_statement
        df_bank_statement = df_bank_statement.merge(
            df_flag_sheet, on="flag_reg_exp", how="left"
        )

        # Unidentified inflows to be marked as "Other receipts"
        df_bank_statement["flag_description"] = df_bank_statement[
            "flag_description"
        ].fillna("OTHER RECEIPTS")

        # drop the temporarily created column
        df_bank_statement = df_bank_statement.drop("flag_reg_exp", axis=1)

        return df_bank_statement
