from datetime import date

from flask import render_template
from flask_login import login_required
from sqlalchemy import case, cast, String, union

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
        # if no start date is provided, default to 01/04/2024
        start_date = form.data["start_date"] or date(2024, 4, 1)
        # if no end date is provided, default to today
        end_date = form.data["end_date"] or date.today()

        inflow = form.data["check_inflow"]
        outflow = form.data["check_outflow"]
        investments = form.data["check_investments"]
        major_payments = form.data["check_major_payments"]
        major_receipts = form.data["check_major_receipts"]

        all_queries = []
        if inflow:
            case_inflow = case((FundBankStatement.credit != 0, "Inflow"), else_="")
            inflow_query = (
                db.session.query(FundBankStatement)
                .with_entities(
                    FundBankStatement.value_date,
                    FundBankStatement.flag_description,
                    FundBankStatement.description,
                    cast(FundBankStatement.credit, String),
                    case_inflow,
                )
                .filter(
                    (
                        (FundBankStatement.value_date >= start_date)
                        & (FundBankStatement.value_date <= end_date)
                    )
                    & (FundBankStatement.credit != 0)
                    & (FundBankStatement.flag_description != "Drawn from investment")
                )
            )
            all_queries.append(inflow_query)

        if outflow:
            case_outflow = case(
                (FundDailyOutflow.outflow_amount > 0, "Outflow"), else_=""
            )
            outflow_query = (
                db.session.query(FundDailyOutflow)
                .with_entities(
                    FundDailyOutflow.outflow_date,
                    FundDailyOutflow.outflow_description,
                    FundDailyOutflow.outflow_description,
                    cast(FundDailyOutflow.outflow_amount, String),
                    case_outflow,
                )
                .filter(
                    (FundDailyOutflow.outflow_date >= start_date)
                    & (FundDailyOutflow.outflow_date <= end_date)
                    & (FundDailyOutflow.outflow_amount > 0)
                )
            )
            all_queries.append(outflow_query)

        if investments:
            case_investment_given = case(
                (
                    FundDailySheet.float_amount_given_to_investments > 0,
                    "Given to investment",
                ),
                else_="",
            )
            case_investment_taken = case(
                (
                    FundDailySheet.float_amount_taken_from_investments > 0,
                    "Taken from investments",
                ),
                else_="",
            )
            investment_given_query = (
                db.session.query(FundDailySheet)
                .with_entities(
                    FundDailySheet.date_current_date,
                    case_investment_given,
                    case_investment_given,
                    cast(FundDailySheet.float_amount_given_to_investments, String),
                    case_investment_given,
                )
                .filter(
                    (FundDailySheet.date_current_date >= start_date)
                    & (FundDailySheet.date_current_date <= end_date)
                    & (FundDailySheet.float_amount_given_to_investments > 0)
                )
            )
            investment_taken_query = (
                db.session.query(FundDailySheet)
                .with_entities(
                    FundDailySheet.date_current_date,
                    case_investment_taken,
                    case_investment_taken,
                    cast(FundDailySheet.float_amount_taken_from_investments, String),
                    case_investment_taken,
                )
                .filter(
                    (FundDailySheet.date_current_date >= start_date)
                    & (FundDailySheet.date_current_date <= end_date)
                    & (FundDailySheet.float_amount_taken_from_investments > 0)
                )
            )
            all_queries.append(investment_given_query)
            all_queries.append(investment_taken_query)
        if major_receipts:
            case_major_receipts = case(
                (
                    FundDailySheet.text_major_collections.is_not(None),
                    "Major collections",
                ),
                else_="",
            )
            major_receipts_query = (
                db.session.query(FundDailySheet)
                .with_entities(
                    FundDailySheet.date_current_date,
                    case_major_receipts,
                    case_major_receipts,
                    FundDailySheet.text_major_collections,
                    case_major_receipts,
                )
                .filter(
                    (FundDailySheet.date_current_date >= start_date)
                    & (FundDailySheet.date_current_date <= end_date)
                    & (FundDailySheet.text_major_collections.is_not(None))
                    & (FundDailySheet.text_major_collections != "")
                )
            )

            all_queries.append(major_receipts_query)
        if major_payments:
            case_major_payments = case(
                (
                    FundDailySheet.text_major_payments.is_not(None),
                    "Major payments",
                ),
                else_="",
            )
            major_payments_query = (
                db.session.query(FundDailySheet)
                .with_entities(
                    FundDailySheet.date_current_date,
                    case_major_payments,
                    case_major_payments,
                    FundDailySheet.text_major_payments,
                    case_major_payments,
                )
                .filter(
                    (FundDailySheet.date_current_date >= start_date)
                    & (FundDailySheet.date_current_date <= end_date)
                    & (FundDailySheet.text_major_payments.is_not(None))
                    & (FundDailySheet.text_major_payments != "")
                )
            )

            all_queries.append(major_payments_query)

        query_set = union(*all_queries)
        query = db.session.execute(query_set)
        return render_template("reports_output.html", query=query)

    return render_template("reports_form.html", form=form)
