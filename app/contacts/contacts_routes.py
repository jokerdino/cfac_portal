import pandas as pd
from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required


from extensions import db
from set_view_permissions import admin_required, ro_user_only

from . import contacts_bp
from .contacts_form import ContactsForm
from .contacts_model import Contacts


@contacts_bp.route("/add", methods=["POST", "GET"])
@login_required
@admin_required
def add_contact():
    form = ContactsForm()

    if form.validate_on_submit():
        contact = Contacts()
        form.populate_obj(contact)

        db.session.add(contact)
        db.session.commit()
        return redirect(url_for("contacts.view_contact", contact_id=contact.id))
    return render_template("add_contact.html", form=form, title="Add new contact")


@contacts_bp.route("/view/<int:contact_id>/")
@login_required
@ro_user_only
def view_contact(contact_id):
    contact = db.get_or_404(Contacts, contact_id)

    return render_template("view_contact.html", contact=contact)


@contacts_bp.route("/edit/<int:contact_id>/", methods=["POST", "GET"])
@login_required
@ro_user_only
def edit_contact(contact_id):
    contact = db.get_or_404(Contacts, contact_id)

    # enable edit only if the RO code of login user matches with contact RO code
    if current_user.user_type == "ro_user":
        if current_user.ro_code != contact.office_code:
            abort(404)

    form = ContactsForm(obj=contact)
    if form.validate_on_submit():
        form.populate_obj(contact)
        db.session.commit()
        return redirect(url_for("contacts.view_contact", contact_id=contact.id))

    return render_template("add_contact.html", form=form, title="Edit contact details")


@contacts_bp.route("/")
@login_required
def contacts_homepage():
    contacts = db.session.scalars(db.select(Contacts))

    return render_template(
        "contacts_homepage.html", contacts=contacts, sort_order=order_based_on_role
    )


@contacts_bp.route("/bulk_upload", methods=["POST", "GET"])
@login_required
@admin_required
def bulk_upload():
    if request.method == "POST":
        upload_file = request.files.get("file")
        df_contact_upload = pd.read_csv(
            upload_file,
            dtype={
                "office_code": str,
                "name": str,
                "zone": str,
                "mobile_number": str,
                "email_address": str,
                "employee_number": int,
                "designation": str,
                "role": str,
                "office_name": str,
            },
        )

        # db.session.query(Contacts).delete()
        # db.session.commit()

        # try:
        df_contact_upload.to_sql(
            "contacts",
            db.engine,
            if_exists="append",
            index=False,
        )

        flash("Contact details have been uploaded to database.")

    return render_template("bulk_upload_contacts.html")


def order_based_on_role(role) -> int:
    sort_order: dict[str, int] = {
        "Coinsurance Hub - Incharge": 1,
        "Coinsurance Hub - Officer": 2,
        "Regional Accountant": 3,
        "Second Officer": 4,
        "GST Nodal officer": 5,
        "Regional Manager-Accounts": 6,
        "Head Office": 7,
    }
    return sort_order.get(role, 8)
