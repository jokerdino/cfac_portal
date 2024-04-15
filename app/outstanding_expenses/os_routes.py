from datetime import datetime
from flask import (
    abort,
    flash,
    redirect,
    render_template,
    url_for,
)

from flask_login import current_user, login_required


from app.outstanding_expenses import os_bp
from app.outstanding_expenses.os_model import (
    OutstandingExpenses,
)
from app.outstanding_expenses.os_form import OutstandingExpensesForm, DeleteOSForm


@os_bp.route("/")
@login_required
def os_homepage():
    list_os_entries = OutstandingExpenses.query.filter(OutstandingExpenses.current_status.is_(None)).order_by(
        OutstandingExpenses.date_date_of_creation.desc()
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


@os_bp.route("/exceptions")
def list_deleted_entries():
    list_os_entries = OutstandingExpenses.query.filter(OutstandingExpenses.current_status.is_not(None))
    return render_template("os_homepage.html", list_os_entries=list_os_entries)


@os_bp.route("/add", methods=["GET"])
@login_required
def add_os_entry():
    form = OutstandingExpensesForm()
    from extensions import db

    if form.data["bool_tds_involved"]:
        from wtforms.validators import DataRequired, Regexp

        form.section.validators = [DataRequired()]
        form.tds_amount.validators = [DataRequired()]
        form.pan_number.validators = [
            DataRequired(),
            Regexp(
                "^[A-Za-z]{5}[0-9]{4}[A-Za-z]{1}$",
                message="Not a valid PAN number.",
            ),
        ]

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
        pan_number = form.data["pan_number"].upper() if bool_tds_involved else None
        nature_of_payment = form.data["nature_of_payment"]
        narration = form.data["narration"]
        payment_date = form.data["payment_date"]
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
                date_payment_date=payment_date,
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


@os_bp.route("/view/<int:os_key>", methods=["GET"])
@login_required
def view_os_entry(os_key):
    form = DeleteOSForm()
    from extensions import db
    os = OutstandingExpenses.query.get_or_404(os_key)
    if os.current_status is not None:
        abort(404)
    if form.validate_on_submit():
        os.current_status = "Deleted"
        db.session.commit()
        return redirect(url_for("outstanding_expenses.os_homepage"))
    return render_template("view_os_entry.html", os=os, form=form)


@os_bp.route("/edit/<int:os_key>", methods=["GET"])
@login_required
def edit_os_entry(os_key):
    os = OutstandingExpenses.query.get_or_404(os_key)
    if os.current_status is not None:
        abort(404)

    # Checking if the entry is pertaining to that RO or OO
    if (
        current_user.user_type == "ro_user"
        and current_user.ro_code != os.str_regional_office_code
    ):
        abort(404)
    elif (
        current_user.user_type == "oo_user"
        and current_user.oo_code != os.str_operating_office_code
    ):
        abort(404)

    form = OutstandingExpensesForm()
    from extensions import db

    # adding validators if TDS involved checkbox is ticked
    if bool_tds_involved := form.data["bool_tds_involved"]:
        from wtforms.validators import DataRequired, Regexp

        form.section.validators = [DataRequired()]
        form.tds_amount.validators = [DataRequired()]
        form.pan_number.validators = [
            DataRequired(),
            Regexp(
                "^[A-Za-z]{5}[0-9]{4}[A-Za-z]{1}$",
                message="Not a valid PAN number.",
            ),
        ]

    if form.validate_on_submit():
        gross_amount = form.data["gross_amount"]

        tds_amount = form.data["tds_amount"] if bool_tds_involved else 0

        net_amount = gross_amount - tds_amount  # if bool_tds_involved else gross_amount
        if not net_amount > 0:
            flash("Net amount must be greater than zero.")
        if current_user.user_type == "oo_user":
            regional_office_code = current_user.ro_code
            operating_office_code = current_user.oo_code
        elif current_user.user_type == "ro_user":
            regional_office_code = current_user.ro_code
            operating_office_code = form.data["operating_office_code"]
        elif current_user.user_type == "admin":
            regional_office_code = form.data["regional_office_code"]
            operating_office_code = form.data["operating_office_code"]

        # collect 13 fields and calculate one field

        os.str_regional_office_code = regional_office_code
        os.str_operating_office_code = operating_office_code
        os.str_party_type = form.data["party_type"]
        os.str_party_id = form.data["party_id"]
        os.str_party_name = form.data["party_name"]
        os.str_narration = form.data["narration"]
        os.str_nature_of_payment = form.data["nature_of_payment"]
        os.float_gross_amount = form.data["gross_amount"]
        os.bool_tds_involved = form.data["bool_tds_involved"]
        os.str_section = form.data["section"] if bool_tds_involved else None
        os.str_pan_number = (
            form.data["pan_number"].upper() if bool_tds_involved else None
        )
        os.float_tds_amount = form.data["tds_amount"] if bool_tds_involved else None
        os.float_net_amount = net_amount
        os.date_payment_date = form.data["payment_date"]
        #    os.str_
        db.session.commit()
        return redirect(url_for("outstanding_expenses.view_os_entry", os_key=os_key))

    form.regional_office_code.data = os.str_regional_office_code
    form.operating_office_code.data = os.str_operating_office_code
    form.party_type.data = os.str_party_type
    form.party_id.data = os.str_party_id
    form.party_name.data = os.str_party_name
    form.gross_amount.data = os.float_gross_amount
    form.bool_tds_involved.data = os.bool_tds_involved
    form.tds_amount.data = os.float_tds_amount
    form.section.data = os.str_section
    form.pan_number.data = os.str_pan_number
    form.nature_of_payment.data = os.str_nature_of_payment
    form.narration.data = os.str_narration
    form.payment_date.data = os.date_payment_date

    return render_template(
        "add_os_entry.html", form=form, title="Edit outstanding expenses entry"
    )
