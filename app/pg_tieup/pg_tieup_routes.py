from datetime import datetime
import os
import pandas as pd
from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    url_for,
    send_from_directory,
)
from flask_login import current_user, login_required

from werkzeug.utils import secure_filename

from app.pg_tieup import pg_tieup_bp
from app.pg_tieup.pg_tieup_form import PaymentGatewayTieupAddForm, UploadFileForm
from app.pg_tieup.pg_tieup_model import PaymentGatewayTieup
from set_view_permissions import admin_required

from extensions import db


@pg_tieup_bp.route("/add/", methods=["POST", "GET"])
@login_required
@admin_required
def add_pg_tieup():
    form = PaymentGatewayTieupAddForm()
    if form.validate_on_submit():
        pg_tieup = PaymentGatewayTieup()
        form.populate_obj(pg_tieup)
        upload_document(
            pg_tieup,
            form,
            "bank_mandate_file_string",
            "bank_mandate_file",
            "bank_mandate",
            "bank_mandate",
        )

        db.session.add(pg_tieup)
        db.session.commit()

        return redirect(url_for("pg_tieup.view_pg_tieup", key=pg_tieup.id))
    return render_template("add_pg_tieup.html", form=form)


@pg_tieup_bp.route("/edit/<int:key>/", methods=["POST", "GET"])
@login_required
@admin_required
def edit_pg_tieup(key):
    pg_tieup = db.session.query(PaymentGatewayTieup).get_or_404(key)
    form = PaymentGatewayTieupAddForm(obj=pg_tieup)

    if form.validate_on_submit():
        form.populate_obj(pg_tieup)
        upload_document(
            pg_tieup,
            form,
            "bank_mandate_file_string",
            "bank_mandate_file",
            "bank_mandate",
            "bank_mandate",
        )
        # pg_tieup.date_updated_date = datetime.now()
        #        pg_tieup.updated_by = current_user.username

        db.session.commit()
        return redirect(url_for("pg_tieup.view_pg_tieup", key=pg_tieup.id))

    return render_template("add_pg_tieup.html", form=form)


@pg_tieup_bp.route("/view/<int:key>/")
@login_required
@admin_required
def view_pg_tieup(key):
    pg_tieup = db.session.query(PaymentGatewayTieup).get_or_404(key)
    return render_template("view_pg_tieup.html", pg_tieup=pg_tieup)


@pg_tieup_bp.route("/list/")
@login_required
@admin_required
def list_pg_tieup():
    column_names = db.session.query(PaymentGatewayTieup).statement.columns.keys()

    meta_columns = [
        "id",
        "bank_mandate_file",
        "current_status",
        "created_by",
        "updated_by",
        "deleted_by",
        "date_created_date",
        "date_updated_date",
        "date_deleted_date",
    ]
    column_names = [col for col in column_names if col not in meta_columns]
    query = db.session.query(PaymentGatewayTieup).order_by(PaymentGatewayTieup.id)
    return render_template("list_pg_tieup.html", query=query, column_names=column_names)


@pg_tieup_bp.route("/bulk_upload", methods=["POST", "GET"])
@login_required
@admin_required
def bulk_upload_pg_tieup():
    form = UploadFileForm()
    if form.validate_on_submit():
        df_cash_call = pd.read_excel(form.data["file_upload"])
        # engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
        df_cash_call.columns = df_cash_call.columns.str.lower()

        df_cash_call["date_created_date"] = datetime.now()
        df_cash_call["created_by"] = current_user.username

        df_cash_call.to_sql(
            "payment_gateway_tieup",
            db.engine,
            if_exists="append",
            index=False,
        )
        flash("PG tieup details have been uploaded successfully.")

    return render_template("bulk_upload_pg_tieup.html", form=form)


@pg_tieup_bp.route("/bank_mandate/<int:id>/")
@login_required
@admin_required
def download_bank_mandate(id):
    pg_tieup = db.get_or_404(PaymentGatewayTieup, id)
    return send_from_directory(
        directory=f"{current_app.config.get('UPLOAD_FOLDER')}/pg_tieup/bank_mandate/",
        path=pg_tieup.bank_mandate_file,
        download_name=f"{pg_tieup.name_of_tieup_partner}.pdf",
        as_attachment=True,
    )


def upload_document(
    model_object, form, field, model_attribute, document_type, folder_name
):
    """
    Uploads a document to the folder specified by folder_name and saves the filename to the object.

    :param object: The object to save the filename to
    :param form: The form containing the file to upload
    :param field: The name of the field in the form containing the file to upload
    :param model_attribute: The name of the attribute in the object to save the filename to
    :param document_type: The type of document being uploaded (e.g. "statement", "confirmation")
    :param folder_name: The folder to save the document in
    """
    folder_path = os.path.join(
        current_app.config.get("UPLOAD_FOLDER"), "pg_tieup", folder_name
    )
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    if form.data[field]:
        filename = secure_filename(form.data[field].filename)
        file_extension = filename.rsplit(".", 1)[1]
        document_filename = f"{document_type}_{datetime.now().strftime('%d%m%Y %H%M%S')}.{file_extension}"

        form.data[field].save(os.path.join(folder_path, document_filename))

        setattr(model_object, model_attribute, document_filename)
