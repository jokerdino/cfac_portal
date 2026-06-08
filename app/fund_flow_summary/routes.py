from datetime import date
from dateutil.relativedelta import relativedelta

import pandas as pd

from flask import flash, redirect, render_template, url_for
from flask_login import login_required

from extensions import db
from set_view_permissions import admin_required


from . import ff_summary_bp
from .models import FundInflowSummary, FundOutflowSummary, FundFlowBankCharges
from .forms import (
    BulkUploadFileForm,
    InflowSummaryInputForm,
    MonthFilterForm,
    BankChargesInputForm,
    FundOutflowInputForm,
)

VIEW_ALL = "View all"


def populate_month_choices(form, Summary, view_all=True):
    subq = (
        db.select(
            Summary.month,
            db.func.to_date(Summary.month, "Month-YYYY").label("month_date"),
        )
        .distinct(Summary.month)
        .subquery()
    )

    month_choices = db.session.scalars(
        db.select(subq.c.month).order_by(subq.c.month_date.desc())
    ).all()

    if view_all:
        form.month.choices = [VIEW_ALL] + month_choices
    else:
        form.month.choices = month_choices


@ff_summary_bp.route("/inflow/bulk_upload/", methods=["POST", "GET"])
@login_required
@admin_required
def bulk_upload_inflow_summary():
    form = BulkUploadFileForm()

    if form.validate_on_submit():
        df_settlement = pd.read_excel(form.data["file_upload"])
        df_settlement.columns = df_settlement.columns.str.lower()
        db.session.execute(
            db.insert(FundInflowSummary), df_settlement.to_dict(orient="records")
        )
        db.session.commit()

        flash("Fundflow summary details have been uploaded successfully.")
    return render_template(
        "ff_upload_file_template.html",
        form=form,
        title="Bulk upload fund inflow summary details",
    )


@ff_summary_bp.route("/outflow/bulk_upload/", methods=["POST", "GET"])
@login_required
@admin_required
def bulk_upload_outflow_summary():
    form = BulkUploadFileForm()

    if form.validate_on_submit():
        df_settlement = pd.read_excel(form.data["file_upload"])
        df_settlement.columns = df_settlement.columns.str.lower()
        db.session.execute(
            db.insert(FundOutflowSummary), df_settlement.to_dict(orient="records")
        )
        db.session.commit()

        flash("Fundflow summary details have been uploaded successfully.")
    return render_template(
        "ff_upload_file_template.html",
        form=form,
        title="Bulk upload fund outflow summary details",
    )


@ff_summary_bp.route("/bank_charges/bulk_upload/", methods=["POST", "GET"])
@login_required
@admin_required
def bulk_upload_bank_charges_summary():
    form = BulkUploadFileForm()

    if form.validate_on_submit():
        df_settlement = pd.read_excel(form.data["file_upload"])
        df_settlement.columns = df_settlement.columns.str.lower()
        db.session.execute(
            db.insert(FundFlowBankCharges), df_settlement.to_dict(orient="records")
        )
        db.session.commit()

        flash("Fundflow summary details have been uploaded successfully.")
    return render_template(
        "ff_upload_file_template.html",
        form=form,
        title="Bulk upload fund flow bank charges details",
    )


@ff_summary_bp.route("/inflow/<string:month>/<string:type>/", methods=["POST", "GET"])
@login_required
@admin_required
def monthly_summary(month, type):
    monthly_summary = db.session.scalars(
        db.select(FundInflowSummary)
        .where(
            FundInflowSummary.month == month,
            FundInflowSummary.type_of_collection == type,
        )
        .order_by(
            FundInflowSummary.bank_vendor_name, FundInflowSummary.mode_of_collection
        )
    )
    form_data = {"summary": monthly_summary}

    form = InflowSummaryInputForm(data=form_data)

    if form.validate_on_submit():
        for input_form in form.summary.data:
            mode = db.get_or_404(FundInflowSummary, input_form["id"])
            mode.number_of_transactions = input_form["number_of_transactions"]
            mode.amount = input_form["amount"]

        db.session.commit()

        return redirect(url_for(".inflow_monthly_summary_list"))

    return render_template("ff_summary_input_form.html", form=form, month=month)


@ff_summary_bp.route("/inflow/list_page/", methods=["POST", "GET"])
@login_required
@admin_required
def inflow_monthly_summary_list():
    query = (
        db.select(FundInflowSummary.month, FundInflowSummary.type_of_collection)
        .group_by(FundInflowSummary.month, FundInflowSummary.type_of_collection)
        .order_by(
            db.func.to_date(FundInflowSummary.month, "Month-YYYY").desc(),
            FundInflowSummary.type_of_collection,
        )
    )
    form = MonthFilterForm()
    populate_month_choices(form, FundInflowSummary, view_all=True)

    if form.validate_on_submit():
        month = form.month.data
        if month != VIEW_ALL:
            query = query.where(FundInflowSummary.month == month)

    data_list = db.session.execute(query)
    return render_template("inflow_summary_list.html", data_list=data_list, form=form)


@ff_summary_bp.route("/outflow/list_page/", methods=["POST", "GET"])
@login_required
@admin_required
def outflow_monthly_summary_list():
    query = db.select(FundOutflowSummary).order_by(
        db.func.to_date(FundOutflowSummary.month, "Month-YYYY").desc(),
        FundOutflowSummary.bank_name,
        FundOutflowSummary.mode_of_payment,
    )
    form = MonthFilterForm()
    populate_month_choices(form, FundOutflowSummary, view_all=True)

    if form.validate_on_submit():
        month = form.month.data
        if month != VIEW_ALL:
            query = query.where(FundOutflowSummary.month == month)

    data_list = db.session.scalars(query)
    return render_template("outflow_summary_list.html", data_list=data_list, form=form)


@ff_summary_bp.route("/bank_charges/list_page/", methods=["POST", "GET"])
@login_required
@admin_required
def bank_charges_monthly_summary_list():
    query = db.select(FundFlowBankCharges).order_by(
        db.func.to_date(FundFlowBankCharges.month, "Month-YYYY").desc(),
        FundFlowBankCharges.bank_name,
    )
    form = MonthFilterForm()
    populate_month_choices(form, FundFlowBankCharges, view_all=True)

    if form.validate_on_submit():
        month = form.month.data
        if month != VIEW_ALL:
            query = query.where(FundFlowBankCharges.month == month)

    data_list = db.session.scalars(query)
    return render_template(
        "bank_charges_summary_list.html", data_list=data_list, form=form
    )


@ff_summary_bp.route("/outflow/<int:id>/", methods=["POST", "GET"])
@login_required
@admin_required
def outflow_data_entry(id):
    outflow = db.get_or_404(FundOutflowSummary, id)
    form = FundOutflowInputForm(obj=outflow)
    if form.validate_on_submit():
        form.populate_obj(outflow)
        db.session.commit()
        return redirect(url_for(".outflow_monthly_summary_list"))
    return render_template(
        "ff_outflow_form.html",
        form=form,
        title="Enter payment details",
        outflow=outflow,
    )


@ff_summary_bp.route("/bank_charges/<int:id>/", methods=["POST", "GET"])
@login_required
@admin_required
def bank_charges_data_entry(id):
    bank_charges = db.get_or_404(FundFlowBankCharges, id)
    form = BankChargesInputForm(obj=bank_charges)
    if form.validate_on_submit():
        # due to calculated hybrid property in the model, we are assigning directly
        bank_charges.fixed_charges = form.fixed_charges.data
        bank_charges.variable_charges = form.variable_charges.data
        db.session.commit()
        return redirect(url_for(".bank_charges_monthly_summary_list"))
    return render_template(
        "ff_bank_charges_form.html",
        form=form,
        title="Enter bank charges details",
        bank_charges=bank_charges,
    )


@ff_summary_bp.route("/", methods=["POST", "GET"])
@login_required
@admin_required
def fundflow_summary_homepage():
    inflow_query = db.select(FundInflowSummary).order_by(
        db.func.to_date(FundInflowSummary.month, "Month-YYYY").desc(),
        FundInflowSummary.type_of_collection,
        FundInflowSummary.bank_vendor_name,
        FundInflowSummary.mode_of_collection,
    )
    outflow_query = db.select(FundOutflowSummary).order_by(
        db.func.to_date(FundOutflowSummary.month, "Month-YYYY").desc(),
        FundOutflowSummary.bank_name,
        FundOutflowSummary.mode_of_payment,
    )
    bank_charges_query = db.select(FundFlowBankCharges).order_by(
        db.func.to_date(FundFlowBankCharges.month, "Month-YYYY").desc(),
        FundFlowBankCharges.bank_name,
    )

    form = MonthFilterForm()
    populate_month_choices(form, FundInflowSummary, view_all=True)

    if form.validate_on_submit():
        month = form.month.data
        if month != VIEW_ALL:
            inflow_query = inflow_query.where(FundInflowSummary.month == month)
            outflow_query = outflow_query.where(FundOutflowSummary.month == month)
            bank_charges_query = bank_charges_query.where(
                FundFlowBankCharges.month == month
            )
    inflow_data = db.session.scalars(inflow_query)
    outflow_data = db.session.scalars(outflow_query)
    bank_charges_data = db.session.scalars(bank_charges_query)
    return render_template(
        "ff_home_page.html",
        form=form,
        inflow_data=inflow_data,
        outflow_data=outflow_data,
        bank_charges_data=bank_charges_data,
    )


@ff_summary_bp.route("/upload_previous_month/")
def brs_auto_upload_prev_month():
    """
    View function to upload fresh BRS entries from previous month's entries.
    Also adds the month to DeleteEntry table.

    URL will be fetched using cron at the start of new month.
    current_month will be the month that just ended.
    New entries will be fetched from the previous month data.

    Returns:
        string: "Success" is returned as response
    """

    # current_month refers to month that just ended
    current_month = date.today() - relativedelta(months=1)

    # prev_month is the month before current_month
    prev_month = current_month - relativedelta(months=1)
    # FY will be fetched based on current_month value

    current_month_string = current_month.strftime("%B-%Y")

    inflow_stmt = db.select(
        FundInflowSummary.type_of_collection,
        FundInflowSummary.bank_vendor_name,
        FundInflowSummary.mode_of_collection,
        db.literal(current_month_string),
        db.literal("AUTOUPLOAD").label("created_by"),
    ).where(FundInflowSummary.month == prev_month.strftime("%B-%Y"))

    insert_inflow_stmt = db.insert(FundInflowSummary).from_select(
        [
            FundInflowSummary.type_of_collection,
            FundInflowSummary.bank_vendor_name,
            FundInflowSummary.mode_of_collection,
            FundInflowSummary.month,
            FundInflowSummary.created_by,
        ],
        inflow_stmt,
    )

    outflow_stmt = db.select(
        FundOutflowSummary.bank_name,
        FundOutflowSummary.mode_of_payment,
        db.literal(current_month_string),
        db.literal("AUTOUPLOAD").label("created_by"),
    ).where(FundOutflowSummary.month == prev_month.strftime("%B-%Y"))

    insert_outflow_stmt = db.insert(FundOutflowSummary).from_select(
        [
            FundOutflowSummary.bank_name,
            FundOutflowSummary.mode_of_payment,
            FundOutflowSummary.month,
            FundOutflowSummary.created_by,
        ],
        outflow_stmt,
    )
    bank_charges_stmt = db.select(
        FundFlowBankCharges.bank_name,
        db.literal(current_month_string),
        db.literal("AUTOUPLOAD").label("created_by"),
    ).where(FundFlowBankCharges.month == prev_month.strftime("%B-%Y"))

    insert_bank_charges_stmt = db.insert(FundFlowBankCharges).from_select(
        [
            FundFlowBankCharges.bank_name,
            FundFlowBankCharges.month,
            FundFlowBankCharges.created_by,
        ],
        bank_charges_stmt,
    )

    db.session.execute(insert_inflow_stmt)
    db.session.execute(insert_outflow_stmt)
    db.session.execute(insert_bank_charges_stmt)

    db.session.commit()

    return "Success"
