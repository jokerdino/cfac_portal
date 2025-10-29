from flask import (
    redirect,
    render_template,
    url_for,
)
from flask_login import current_user, login_required


from . import os_bp
from .os_model import OutstandingExpenses
from .os_form import OutstandingExpensesForm, DeleteOSForm

from extensions import db
from set_view_permissions import admin_required, oo_user_only


@os_bp.route("/")
@login_required
@oo_user_only
def os_homepage():
    stmt = (
        db.select(OutstandingExpenses)
        .where(OutstandingExpenses.current_status.is_(None))
        .order_by(OutstandingExpenses.date_date_of_creation.desc())
    )

    if current_user.user_type == "ro_user":
        stmt = stmt.where(
            OutstandingExpenses.str_regional_office_code == current_user.ro_code
        )
    elif current_user.user_type == "oo_user":
        stmt = stmt.where(
            OutstandingExpenses.str_operating_office_code == current_user.oo_code
        )
    list_os_entries = db.session.scalars(stmt)
    return render_template("os_homepage.html", list_os_entries=list_os_entries)


@os_bp.route("/exceptions")
@login_required
@admin_required
def list_deleted_entries():
    list_os_entries = db.session.scalars(
        db.select(OutstandingExpenses).where(
            OutstandingExpenses.current_status == "Deleted"
        )
    )

    return render_template("os_homepage.html", list_os_entries=list_os_entries)


@os_bp.route("/add", methods=["GET"])
@login_required
@oo_user_only
def add_os_entry():
    form = OutstandingExpensesForm()

    # --- Prepopulate fields based on user type ---
    if current_user.user_type == "oo_user":
        form.str_regional_office_code.data = current_user.ro_code
        form.str_operating_office_code.data = current_user.oo_code

    elif current_user.user_type == "ro_user":
        form.str_regional_office_code.data = current_user.ro_code

    if form.validate_on_submit():
        os = OutstandingExpenses()

        form.populate_obj(os)
        db.session.add(os)
        db.session.commit()
        return redirect(url_for(".view_os_entry", os_key=os.id))

    return render_template(
        "add_os_entry.html", form=form, title="Add outstanding expenses entry"
    )


@os_bp.route("/view/<int:os_key>/", methods=["GET"])
@login_required
@oo_user_only
def view_os_entry(os_key):
    form = DeleteOSForm()

    os = db.get_or_404(OutstandingExpenses, os_key)
    os.require_access(current_user)

    if form.validate_on_submit():
        os.current_status = "Deleted"
        db.session.commit()
        return redirect(url_for(".os_homepage"))
    return render_template("view_os_entry.html", os=os, form=form)


@os_bp.route("/edit/<int:os_key>/", methods=["GET"])
@login_required
@oo_user_only
def edit_os_entry(os_key):
    os = db.get_or_404(OutstandingExpenses, os_key)
    os.require_access(current_user)

    form = OutstandingExpensesForm(obj=os)

    if form.validate_on_submit():
        form.populate_obj(os)
        db.session.commit()
        return redirect(url_for(".view_os_entry", os_key=os_key))

    return render_template(
        "add_os_entry.html", form=form, title="Edit outstanding expenses entry"
    )
