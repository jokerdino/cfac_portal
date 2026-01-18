from datetime import date

from flask import render_template, flash
from flask_login import login_required


from . import funds_bp
from .funds_form import ReportsForm
from .funds_model import FundBankStatement, FundDailyOutflow, FundDailySheet

from set_view_permissions import admin_required
from extensions import db


@funds_bp.route("/reports", methods=["POST", "GET"])
@login_required
@admin_required
def funds_reports():
    form = ReportsForm()
    if form.validate_on_submit():
        start_date = form.data["start_date"] or date(2024, 4, 1)
        end_date = form.data["end_date"] or date.today()

        inflow = form.data["check_inflow"]
        outflow = form.data["check_outflow"]
        investments = form.data["check_investments"]
        major_payments = form.data["check_major_payments"]
        major_receipts = form.data["check_major_receipts"]

        all_queries = []

        # --- Helper: standard date filter ---
        def date_filter(column):
            return (column >= start_date) & (column <= end_date)

        if inflow:
            inflow_query = db.select(
                FundBankStatement.value_date,
                FundBankStatement.flag_description,
                FundBankStatement.description,
                db.cast(FundBankStatement.credit, db.String),
                db.literal("Inflow"),
            ).where(
                date_filter(FundBankStatement.value_date)
                & (FundBankStatement.credit != 0)
                & (FundBankStatement.flag_description != "Drawn from investment")
            )
            all_queries.append(inflow_query)

        if outflow:
            outflow_query = db.select(
                FundDailyOutflow.outflow_date,
                FundDailyOutflow.normalized_description,
                FundDailyOutflow.normalized_description,
                db.cast(FundDailyOutflow.outflow_amount, db.String),
                db.literal("Outflow"),
            ).where(
                date_filter(FundDailyOutflow.outflow_date)
                & (FundDailyOutflow.outflow_amount > 0)
            )
            all_queries.append(outflow_query)

        if investments:
            investment_given_query = db.select(
                FundDailySheet.date_current_date,
                db.literal("Given to investment"),
                db.literal("Given to investment"),
                db.cast(FundDailySheet.float_amount_given_to_investments, db.String),
                db.literal("Given to investment"),
            ).where(
                date_filter(FundDailySheet.date_current_date)
                & (FundDailySheet.float_amount_given_to_investments > 0)
            )
            investment_taken_query = db.select(
                FundDailySheet.date_current_date,
                db.literal("Taken from investments"),
                db.literal("Taken from investments"),
                db.cast(FundDailySheet.float_amount_taken_from_investments, db.String),
                db.literal("Taken from investments"),
            ).where(
                date_filter(FundDailySheet.date_current_date)
                & (FundDailySheet.float_amount_taken_from_investments > 0)
            )
            all_queries.append(investment_given_query)
            all_queries.append(investment_taken_query)
        if major_receipts:
            major_receipts_query = db.select(
                FundDailySheet.date_current_date,
                db.literal("Major collections"),
                db.literal("Major collections"),
                FundDailySheet.text_major_collections,
                db.literal("Major collections"),
            ).where(
                date_filter(FundDailySheet.date_current_date)
                & (FundDailySheet.text_major_collections.is_not(None))
                & (FundDailySheet.text_major_collections != "")
            )

            all_queries.append(major_receipts_query)
        if major_payments:
            major_payments_query = db.select(
                FundDailySheet.date_current_date,
                db.literal("Major payments"),
                db.literal("Major payments"),
                FundDailySheet.text_major_payments,
                db.literal("Major payments"),
            ).where(
                date_filter(FundDailySheet.date_current_date)
                & (FundDailySheet.text_major_payments.is_not(None))
                & (FundDailySheet.text_major_payments != "")
            )

            all_queries.append(major_payments_query)
        if not all_queries:
            flash("Please select at least one report type.")
            return render_template(
                "funds_form.html", form=form, title="Funds - Reports"
            )

        query_set = db.union_all(*all_queries)
        query = db.session.execute(query_set)
        return render_template("reports_output.html", query=query)

    return render_template("funds_form.html", form=form, title="Funds - Reports")
