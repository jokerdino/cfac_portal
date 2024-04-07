from datetime import datetime
import calendar
from sqlalchemy.sql import exists, select, or_
from typing import List, Any

import pandas as pd

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from flask_login import current_user, login_required
from sqlalchemy import create_engine, func

from app.outstanding_expenses import os_bp
from app.outstanding_expenses.os_model import (
    OutstandingExpenses,
    # OutstandingExpensesJournalVoucher,
)
from app.outstanding_expenses.os_form import OutstandingExpensesForm

from app.tickets.tickets_routes import humanize_datetime


@os_bp.route("/", methods=["POST", "GET"])
@login_required
def os_homepage():
    list_os_entries = OutstandingExpenses.query.order_by(
        OutstandingExpenses.date_date_of_creation
    )

    if current_user.user_type == "ro_user":
        list_os_entries = list_os_entries.filter(
            OutstandingExpenses.str_regional_office_code == current_user.ro_code
        )
    elif current_user.user_type == "oo_user":
        list_os_entries = list_os_entries.filter(
            OutstandingExpenses.str_operating_office_code == current_user.oo_code
        )

    return render_template("os_homepage.html", list_os_entries=list_os_entries)


@os_bp.route("/add", methods=["POST", "GET"])
@login_required
def add_os_entry():
    form = OutstandingExpensesForm()
    from extensions import db

    if form.data["bool_tds_involved"]:
        from wtforms.validators import DataRequired

        form.section.validators = [DataRequired()]
        form.tds_amount.validators = [DataRequired()]
        form.pan_number.validators = [DataRequired()]

    if form.validate_on_submit():
        if current_user.user_type == "oo_user":
            regional_office_code = current_user.ro_code
            operating_office_code = current_user.oo_code
        elif current_user.user_type == "ro_user":
            regional_office_code = current_user.ro_code
            operating_office_code = form.data["operating_office_code"]
        elif current_user.user_type == "admin":
            regional_office_code = form.data["regional_office_code"]
            operating_office_code = form.data["operating_office_code"]
        # regional_office_code = form.data["regional_office_code"]
        # operating_office_code = form.data["operating_office_code"]
        party_type = form.data["party_type"]
        party_name = form.data["party_name"]
        party_id = form.data["party_id"]
        gross_amount = form.data["gross_amount"]
        bool_tds_involved = form.data["bool_tds_involved"]
        section = form.data["section"] if bool_tds_involved else None
        tds_amount = form.data["tds_amount"] if bool_tds_involved else None
        pan_number = form.data["pan_number"] if bool_tds_involved else None
        nature_of_payment = form.data["nature_of_payment"]
        narration = form.data["narration"]
        net_amount = (gross_amount - tds_amount) if bool_tds_involved else gross_amount
        if net_amount > 0:
            os = OutstandingExpenses(
                str_regional_office_code=regional_office_code,
                str_operating_office_code=operating_office_code,
                str_party_type=party_type,
                str_party_name=party_name,
                str_party_id=party_id,
                float_gross_amount=gross_amount,
                bool_tds_involved=bool_tds_involved,
                str_section=section,
                float_tds_amount=tds_amount,
                str_pan_number=pan_number,
                str_nature_of_payment=nature_of_payment,
                str_narration=narration,
                float_net_amount=net_amount,
                date_date_of_creation=datetime.now(),
            )
            db.session.add(os)
            db.session.commit()
            return redirect(url_for("outstanding_expenses.view_os_entry", os_key=os.id))
        else:
            flash("Net amount must be greater than zero.")
    return render_template(
        "add_os_entry.html", form=form, title="Add outstanding expenses entry"
    )


@os_bp.route("/view/<int:os_key>")
@login_required
def view_os_entry(os_key):
    os = OutstandingExpenses.query.get_or_404(os_key)
    return render_template("view_os_entry.html", os=os)


@os_bp.route("/edit/<int:os_key>", methods=["GET", "POST"])
@login_required
def edit_os_entry(os_key):
    os = OutstandingExpenses.query.get_or_404(os_key)
    form = OutstandingExpensesForm()
    from extensions import db

    if form.data["bool_tds_involved"]:
        from wtforms.validators import DataRequired

        form.section.validators = [DataRequired()]
        form.tds_amount.validators = [DataRequired()]
        form.pan_number.validators = [DataRequired()]

    if form.validate_on_submit():
        if current_user.user_type == "oo_user":
            regional_office_code = current_user.ro_code
            operating_office_code = current_user.oo_code
        elif current_user.user_type == "ro_user":
            regional_office_code = current_user.ro_code
            operating_office_code = form.data["operating_office_code"]

        elif current_user.user_type == "admin":
            regional_office_code = form.data["regional_office_code"]
            operating_office_code = form.data["operating_office_code"]
        # regional_office_code = form.data["regional_office_code"]
        #  os.str_regional_office_code = regional_office_code
        db.session.commit()
        return redirect(url_for("view_os_entry", os_key=os_key))
    form.regional_office_code.data = os.str_regional_office_code

    return render_template(
        "add_os_entry.html", form=form, title="Edit outstanding expenses entry"
    )
