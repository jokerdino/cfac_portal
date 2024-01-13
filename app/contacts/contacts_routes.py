import pandas as pd
from flask import (
    current_app,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
    flash,
)
from flask_login import current_user
from sqlalchemy import create_engine, text

from app.contacts import contacts_bp
from app.contacts.contacts_form import ContactsForm
from app.contacts.contacts_model import Contacts


@contacts_bp.route("/add", methods=["POST", "GET"])
def add_contact():
    from server import db

    form = ContactsForm()

    if form.validate_on_submit():
        contact = Contacts(
            name=form.data["name"],
            employee_number=form.data["employee_number"],
            zone=form.data["zone"],
            designation=form.data["designation"],
            mobile_number=form.data["mobile_number"],
            email_address=form.data["email_address"],
            office_code=form.data["office_code"],
            office_name=form.data["office_name"],
            role=form.data["role"],
        )
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

    form = ContactsForm()
    if form.validate_on_submit():
        contact.name = form.data["name"]
        contact.zone = form.data["zone"]
        contact.role = form.data["role"]
        contact.office_code = form.data["office_code"]
        contact.office_name = form.data["office_name"]
        contact.designation = form.data["designation"]
        contact.email_address = form.data["email_address"]
        contact.mobile_number = form.data["mobile_number"]
        contact.employee_number = form.data["employee_number"]
        db.session.commit()
        return redirect(url_for("contacts.view_contact", contact_id=contact.id))
    form.name.data = contact.name
    form.zone.data = contact.zone
    form.role.data = contact.role
    form.office_code.data = contact.office_code
    form.office_name.data = contact.office_name
    form.email_address.data = contact.email_address
    form.mobile_number.data = contact.mobile_number
    form.designation.data = contact.designation
    form.employee_number.data = contact.employee_number

    return render_template("add_contact.html", form=form, title="Edit contact details")


@contacts_bp.route("/")
def contacts_homepage():
    contacts = Contacts.query.all()

    return render_template("contacts_homepage.html", contacts=contacts)


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
