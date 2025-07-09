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

from werkzeug.utils import secure_filename

from extensions import db
from set_view_permissions import admin_required

from . import lien_bp
from .lien_model import Lien
from .lien_forms import LienFormCFAC, LienFormRO, LienUploadForm


def prepare_upload_document(lien, form) -> None:
    file_field_dictionary: dict[str : tuple(str, str, str)] = {
        "court_order_lien": ("court_order_lien_file", "lien_order", "lien_order"),
        "court_order_dd": ("court_order_dd_file", "dd_order", "dd_copy"),
        "lien_dd_reversal_order": (
            "lien_dd_reversal_order_file",
            "lien_dd_reversal",
            "lien_dd_reversal",
        ),
        "appeal_copy": ("appeal_copy_file", "appeal_copy", "appeal_copy"),
        "stay_order": ("stay_order_file", "stay_order", "stay_order"),
        "court_order_lien_reversal": (
            "court_order_lien_reversal_file",
            "lien_reversal",
            "lien_reversal",
        ),
        "court_order_dd_reversal": (
            "court_order_dd_reversal_file",
            "dd_reversal",
            "dd_reversal",
        ),
        "claim_disbursement_voucher": (
            "claim_disbursement_voucher_file",
            "disbursement_voucher",
            "disbursement_voucher",
        ),
    }
    for model_attribute, (
        field,
        document_type,
        folder_name,
    ) in file_field_dictionary.items():
        upload_document(lien, form, field, document_type, model_attribute, folder_name)


@lien_bp.route("/add", methods=["GET", "POST"])
@login_required
@admin_required
def lien_add():
    form = LienFormCFAC()
    if form.validate_on_submit():
        lien = Lien()
        form.populate_obj(lien)
        prepare_upload_document(lien, form)
        db.session.add(lien)
        db.session.commit()
        return redirect(url_for("lien.lien_view", lien_id=lien.id))
    return render_template("lien_edit.html", form=form, title="Add new lien")


@lien_bp.route("/view/<lien_id>/", methods=["GET", "POST"])
@login_required
def lien_view(lien_id):
    lien = db.get_or_404(Lien, lien_id)
    return render_template("lien_view.html", lien=lien)


@lien_bp.route("/edit/<lien_id>/", methods=["GET", "POST"])
@login_required
def lien_edit(lien_id):
    lien = db.get_or_404(Lien, lien_id)
    if current_user.user_type == "admin":
        form = LienFormCFAC(obj=lien)
    elif current_user.user_type in ["ho_motor_tp", "ro_user"]:
        form = LienFormRO(obj=lien)
    if form.validate_on_submit():
        form.populate_obj(lien)
        prepare_upload_document(lien, form)
        db.session.commit()
        return redirect(url_for("lien.lien_view", lien_id=lien.id))
    return render_template("lien_edit.html", form=form, lien=lien, title="Edit lien")


@lien_bp.get("/download/<int:lien_id>/<string:document_type>/")
@login_required
def download_document(document_type, lien_id):
    def get_document_path(lien, document_type):
        document_map = {
            "lien_order": lien.court_order_lien,
            "dd_copy": lien.court_order_dd,
            "lien_reversal": lien.court_order_lien_reversal,
            "dd_reversal": lien.court_order_dd_reversal,
            "appeal_copy": lien.appeal_copy,
            "stay_order": lien.stay_order,
            "lien_dd_reversal": lien.lien_dd_reversal_order,
            "disbursement_voucher": lien.claim_disbursement_voucher,
        }
        return document_map.get(document_type)

    lien = db.get_or_404(Lien, lien_id)

    path = get_document_path(lien, document_type)
    if not path:
        abort(404)

    file_extension = path.rsplit(".", 1)[-1]

    filename = f"{document_type}_{lien.bank_name}_{lien.lien_amount}.{file_extension}"
    return send_from_directory(
        directory=f"{current_app.config.get('UPLOAD_FOLDER')}lien/{document_type}/",
        path=path,
        as_attachment=True,
        download_name=filename,
    )


@lien_bp.route("/")
@login_required
def lien_list():
    liens = db.session.scalars(
        db.select(Lien)
    )  # .where(Lien.lien_status == "Lien exists"))
    column_names = [column.name for column in Lien.__table__.columns][1:35]
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
            db.engine,
            if_exists="append",
            index=False,
        )

        return redirect(url_for("lien.lien_list"))
    return render_template("lien_bulk_upload.html", form=form)


def upload_document(
    model_object, form, field, document_type, model_attribute, folder_name
):
    """
    Uploads a document to the folder specified by folder_name and saves the filename to the object.

    :param object: The object to save the filename to
    :param form: The form containing the file to upload
    :param field: The name of the field in the form containing the file to upload
    :param document_type: The type of document being uploaded (e.g. "statement", "confirmation")
    :param model_attribute: The name of the attribute in the object to save the filename to
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

        setattr(model_object, model_attribute, document_filename)
