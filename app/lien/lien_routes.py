from datetime import datetime
import os
import pandas as pd
from flask import (
    abort,
    current_app,
    redirect,
    render_template,
    url_for,
    send_from_directory,
)
from flask_login import login_required, current_user
from sqlalchemy import create_engine
from werkzeug.utils import secure_filename

from extensions import db
from set_view_permissions import admin_required, ro_user_only

from . import lien_bp
from .lien_model import Lien
from .lien_forms import LienForm, LienUploadForm, LienAddRemarks


@lien_bp.route("/add", methods=["GET", "POST"])
@login_required
@admin_required
def lien_add():
    form = LienForm()
    if form.validate_on_submit():
        lien = Lien()
        form.populate_obj(lien)
        upload_document(
            lien, form, "court_order_lien_file", "court_order_lien", "lien_order"
        )
        upload_document(
            lien, form, "court_order_dd_file", "court_order_dd_file", "dd_copy"
        )
        upload_document(
            lien,
            form,
            "court_order_lien_reversal_file",
            "court_order_lien_reversal",
            "lien_reversal",
        )
        db.session.add(lien)
        db.session.commit()
        return redirect(url_for("lien.lien_view", lien_id=lien.id))
    return render_template("lien_edit.html", form=form, title="Add new lien")


@lien_bp.route("/remarks/<lien_id>/", methods=["GET", "POST"])
@login_required
@ro_user_only
def lien_add_remarks(lien_id):
    lien = db.get_or_404(Lien, lien_id)
    form = LienAddRemarks(obj=lien)
    if form.validate_on_submit():
        form.populate_obj(lien)
        db.session.commit()
        return redirect(url_for("lien.lien_view", lien_id=lien.id))
    return render_template("lien_add_remarks.html", form=form, lien=lien)


@lien_bp.route("/view/<lien_id>", methods=["GET", "POST"])
@login_required
@ro_user_only
def lien_view(lien_id):
    lien = db.get_or_404(Lien, lien_id)
    return render_template("lien_view.html", lien=lien)


@lien_bp.route("/edit/<lien_id>", methods=["GET", "POST"])
@login_required
@admin_required
def lien_edit(lien_id):
    lien = db.get_or_404(Lien, lien_id)
    form = LienForm(obj=lien)
    if form.validate_on_submit():
        form.populate_obj(lien)
        upload_document(
            lien, form, "court_order_lien_file", "court_order_lien", "lien_order"
        )
        upload_document(lien, form, "court_order_dd_file", "court_order_dd", "dd_copy")
        upload_document(
            lien,
            form,
            "court_order_lien_reversal_file",
            "court_order_lien_reversal",
            "lien_reversal",
        )
        db.session.commit()
        return redirect(url_for("lien.lien_view", lien_id=lien.id))
    return render_template("lien_edit.html", form=form, lien=lien, title="Edit lien")


@lien_bp.get("/download/<int:lien_id>/<string:document_type>/")
@login_required
@ro_user_only
def download_document(document_type, lien_id):
    lien = Lien.query.get_or_404(lien_id)

    if document_type == "lien_order":
        file_extension = lien.court_order_lien.rsplit(".", 1)[1]
        path = lien.court_order_lien
    elif document_type == "dd_copy":
        file_extension = lien.court_order_dd.rsplit(".", 1)[1]
        path = lien.court_order_dd
    elif document_type == "lien_reversal":
        file_extension = lien.court_order_lien_reversal.rsplit(".", 1)[1]
        path = lien.court_order_lien_reversal
    else:
        abort(404)

    filename = f"{lien.lien_amount}_{lien.date_of_order}.{file_extension}"
    return send_from_directory(
        directory=f"{current_app.config.get('UPLOAD_FOLDER')}lien/{document_type}/",
        path=path,
        as_attachment=True,
        download_name=filename,
    )


@lien_bp.route("/")
@login_required
@ro_user_only
def lien_list():
    liens = db.session.scalars(
        db.select(Lien)
    )  # .where(Lien.lien_status == "Lien exists"))
    column_names = [column.name for column in Lien.__table__.columns][1:14]
    return render_template("lien_list.html", lien_list=liens, column_names=column_names)


@lien_bp.route("/upload", methods=["GET", "POST"])
@login_required
@admin_required
def lien_bulk_upload():
    form = LienUploadForm()
    if form.validate_on_submit():
        lien_file = form.lien_file.data
        df_lien = pd.read_excel(lien_file)

        df_lien["created_on"] = datetime.now()
        df_lien["created_by"] = current_user.username

        df_lien.to_sql(
            "lien",
            create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI")),
            if_exists="append",
            index=False,
        )

        return redirect(url_for("lien.lien_list"))
    return render_template("lien_bulk_upload.html", form=form)


def upload_document(model_object, form, field, document_type, folder_name):
    """
    Uploads a document to the folder specified by folder_name and saves the filename to the object.

    :param object: The object to save the filename to
    :param form: The form containing the file to upload
    :param field: The name of the field in the form containing the file to upload
    :param document_type: The type of document being uploaded (e.g. "statement", "confirmation")
    :param folder_name: The folder to save the document in
    """
    folder_path = os.path.join(
        current_app.config.get("UPLOAD_FOLDER"), "lien", folder_name
    )
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    if form.data[field]:
        filename = secure_filename(form.data[field].filename)
        file_extension = filename.rsplit(".", 1)[1]
        document_filename = f"{document_type}_{datetime.now().strftime('%d%m%Y %H%M%S')}.{file_extension}"

        form.data[field].save(os.path.join(folder_path, document_filename))

        setattr(model_object, document_type, document_filename)
