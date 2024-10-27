import pandas as pd
from flask import (
    current_app,
    redirect,
    render_template,
    request,
    url_for,
    flash,
)
from flask_login import current_user
from sqlalchemy import create_engine

from app.contacts import contacts_bp
from app.contacts.contacts_form import ContactsForm
from app.contacts.contacts_model import Contacts


@contacts_bp.route("/add", methods=["POST", "GET"])
def add_contact():
    from server import db

    form = ContactsForm()

    if form.validate_on_submit():
        contact = Contacts()
        form.populate_obj(contact)

        db.session.add(contact)
        db.session.commit()
        return redirect(url_for("contacts.view_contact", contact_id=contact.id))
    return render_template("add_contact.html", form=form, title="Add new contact")


@contacts_bp.route("/view/<int:contact_id>")
def view_contact(contact_id):
    contact = Contacts.query.get_or_404(contact_id)

    return render_template("view_contact.html", contact=contact)


@contacts_bp.route("/edit/<int:contact_id>", methods=["POST", "GET"])
def edit_contact(contact_id):
    contact = Contacts.query.get_or_404(contact_id)
    from server import db

    form = ContactsForm(obj=contact)
    if form.validate_on_submit():
        form.populate_obj(contact)
        db.session.commit()
        return redirect(url_for("contacts.view_contact", contact_id=contact.id))

    return render_template("add_contact.html", form=form, title="Edit contact details")


@contacts_bp.route("/")
def contacts_homepage():
    contacts = Contacts.query.all()

    return render_template(
        "contacts_homepage.html", contacts=contacts, sort_order=order_based_on_role
    )


@contacts_bp.route("/bulk_upload", methods=["POST", "GET"])
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

        from server import db

        db.session.query(Contacts).delete()
        db.session.commit()
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))

        # try:
        df_contact_upload.to_sql(
            "contacts",
            engine,
            if_exists="append",
            index=False,
        )

        flash("Contact details have been uploaded to database.")

    return render_template("bulk_upload_contacts.html")


def order_based_on_role(role) -> int:
    sort_order: dict[str, int] = {
        "Regional Accountant": 1,
        "Second Officer": 2,
        "Regional Manager-Accounts": 3,
    }
    return sort_order.get(role, 4)
