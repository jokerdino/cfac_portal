from datetime import datetime
import pandas as pd

# from functools import wraps
from flask import (
    render_template,
    abort,
    url_for,
    request,
    redirect,
    flash,
    current_app,
)

from flask_login import current_user, login_required


from sqlalchemy import create_engine, case, func, and_

from set_view_permissions import admin_required
from app.budget import budget_bp
from app.budget.budget_model import BudgetAllocation, BudgetUtilization

from app.budget.budget_form import (
    BudgetAllocationForm,
    BudgetUtilizationForm,
    BudgetQueryForm,
)


@budget_bp.route("/upload_allocation/", methods=["POST", "GET"])
@login_required
@admin_required
def upload_allocation():
    form = BudgetAllocationForm()
    if form.validate_on_submit():
        file_budget_allocation = form.data["str_budget_allocation"]
        df_budget_allocation = pd.read_excel(file_budget_allocation)
        df_budget_allocation.rename(
            columns={
                "Description": "str_expense_head",
                "ro_code": "str_ro_code",
                "budget_allocated": "int_budget_allocated",
            },
            inplace=True,
        )
        df_budget_allocation["str_ro_code"] = (
            df_budget_allocation["str_ro_code"].astype(str).str.zfill(6)
        )
        df_budget_allocation["str_financial_year"] = form.data["str_financial_year"]
        df_budget_allocation["str_type"] = form.data["str_type"]

        df_budget_allocation["created_by"] = current_user.username
        df_budget_allocation["date_created_date"] = datetime.now()

        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
        df_budget_allocation.to_sql(
            "budget_allocation", engine, if_exists="append", index=False
        )
        flash("Budget allocation has been successfully uploaded.")

    return render_template("allocation_upload.html", form=form)


@budget_bp.route("/upload_utilization/", methods=["POST", "GET"])
@login_required
@admin_required
def upload_utilization():
    form = BudgetUtilizationForm()
    if form.validate_on_submit():
        file_budget_utilization = form.data["str_budget_utilization"]
        df_budget_utilization = pd.read_excel(file_budget_utilization)
        df_budget_utilization.rename(
            columns={
                "Description": "str_expense_head",
                "ro_code": "str_ro_code",
                "budget_utilized": "int_budget_utilized",
            },
            inplace=True,
        )
        df_budget_utilization["str_ro_code"] = (
            df_budget_utilization["str_ro_code"].astype(str).str.zfill(6)
        )
        df_budget_utilization["str_financial_year"] = form.data["str_financial_year"]
        df_budget_utilization["str_quarter"] = form.data["str_quarter"]

        df_budget_utilization["created_by"] = current_user.username
        df_budget_utilization["date_created_date"] = datetime.now()

        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
        df_budget_utilization.to_sql(
            "budget_utilization", engine, if_exists="append", index=False
        )
        flash("Budget allocation has been successfully uploaded.")

    return render_template("utilization_upload.html", form=form)


@budget_bp.route("/budget_utilization/", methods=["POST", "GET"])
@login_required
@admin_required
def view_budget_utilization():
    form = BudgetQueryForm()
    from extensions import db

    ro_list = db.session.query(BudgetAllocation.str_ro_code).distinct()
    expense_list = db.session.query(BudgetAllocation.str_expense_head).distinct()
    form.str_ro_code.choices = sorted([ro_code[0] for ro_code in ro_list])
    form.str_expense_head.choices = sorted([expense[0] for expense in expense_list])
    if form.validate_on_submit():

        case_original = case(
            (
                BudgetAllocation.str_type == "Original",
                BudgetAllocation.int_budget_allocated,
            ),
            else_=0,
        )
        case_revised = case(
            (
                BudgetAllocation.str_type == "Revised",
                BudgetAllocation.int_budget_allocated,
            ),
            else_=0,
        )
        case_first_quarter = case(
            (
                BudgetUtilization.str_quarter == "I",
                BudgetUtilization.int_budget_utilized,
            ),
            else_=None,
        )
        case_second_quarter = case(
            (
                BudgetUtilization.str_quarter == "II",
                BudgetUtilization.int_budget_utilized,
            ),
            else_=None,
        )
        case_third_quarter = case(
            (
                BudgetUtilization.str_quarter == "III",
                BudgetUtilization.int_budget_utilized,
            ),
            else_=None,
        )
        case_fourth_quarter = case(
            (
                BudgetUtilization.str_quarter == "IV",
                BudgetUtilization.int_budget_utilized,
            ),
            else_=None,
        )

        budget = (
            db.session.query(BudgetAllocation, BudgetUtilization)
            .with_entities(
                BudgetUtilization.str_financial_year,
                BudgetUtilization.str_ro_code,
                BudgetUtilization.str_expense_head,
                func.max(case_original),
                func.max(case_revised),
                func.max(case_first_quarter),
                func.max(case_second_quarter),
                func.max(case_third_quarter),
                func.max(case_fourth_quarter),
            )
            .filter(
                (BudgetAllocation.str_ro_code == BudgetUtilization.str_ro_code)
                & (
                    BudgetAllocation.str_expense_head
                    == BudgetUtilization.str_expense_head
                )
            )
            .group_by(
                BudgetUtilization.str_financial_year,
                BudgetUtilization.str_ro_code,
                BudgetUtilization.str_expense_head,
            )
            .order_by(BudgetUtilization.str_ro_code, BudgetUtilization.str_expense_head)
        )

        str_financial_year = form.data["str_financial_year"]
        budget = budget.filter(
            BudgetUtilization.str_financial_year == str_financial_year
        )
        if form.data["str_expense_head"]:
            expense_list = form.data["str_expense_head"]
            budget = budget.filter(BudgetUtilization.str_expense_head.in_(expense_list))
        if form.data["str_ro_code"]:
            ro_code_list = form.data["str_ro_code"]
            budget = budget.filter(BudgetUtilization.str_ro_code.in_(ro_code_list))

        return render_template(
            "view_budget_utilization.html",
            budget=budget,
        )
    return render_template("query_budget_utilization.html", form=form)