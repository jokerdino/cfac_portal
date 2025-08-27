from datetime import datetime
import os
import re

import pandas as pd
from flask import (
    abort,
    current_app,
    flash,
    redirect,
    request,
    render_template,
    url_for,
    send_from_directory,
)
from sqlalchemy import func, case, event
from sqlalchemy.orm import Session

from flask_login import login_required, current_user
from sqlalchemy_continuum import version_class

from werkzeug.utils import secure_filename

from extensions import db
from set_view_permissions import admin_required

from . import lien_bp
from .lien_model import Lien
from .lien_forms import (
    LienFormCFAC,
    LienFormRO,
    LienUploadForm,
    LienFormHOTP,
    ALLOWED_RO_CODES,
)


def prepare_upload_document(lien, form) -> None:
    file_field_dictionary: dict[str : tuple(str, str, str)] = {
        "court_order_lien": (
            "court_order_lien_file",
            "court_order_lien",
            "court_order_lien",
        ),
        "court_order_dd": ("court_order_dd_file", "court_order_dd", "court_order_dd"),
        "lien_dd_reversal_order": (
            "lien_dd_reversal_order_file",
            "lien_dd_reversal_order",
            "lien_dd_reversal_order",
        ),
        "appeal_copy": ("appeal_copy_file", "appeal_copy", "appeal_copy"),
        "appeal_copy_2": ("appeal_copy_2_file", "appeal_copy_2", "appeal_copy_2"),
        "stay_order": ("stay_order_file", "stay_order", "stay_order"),
        "court_order_lien_reversal": (
            "court_order_lien_reversal_file",
            "court_order_lien_reversal",
            "court_order_lien_reversal",
        ),
        "court_order_dd_reversal": (
            "court_order_dd_reversal_file",
            "court_order_dd_reversal",
            "court_order_dd_reversal",
        ),
        "claim_disbursement_voucher": (
            "claim_disbursement_voucher_file",
            "claim_disbursement_voucher",
            "claim_disbursement_voucher",
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


@lien_bp.route("/log/<lien_id>/")
@login_required
def lien_log_view(lien_id):

    LienVersion = version_class(Lien)
    col_names = column_names = Lien.query.statement.columns.keys()
    lien_log = (
        db.session.query(LienVersion)
        .filter_by(id=lien_id)
        .order_by(LienVersion.transaction_id.asc())
    )
    return render_template(
        "lien_log_view.html", lien_log=lien_log, column_names=col_names, lien_id=lien_id
    )


@lien_bp.route("/edit/<lien_id>/", methods=["GET", "POST"])
@login_required
def lien_edit(lien_id):
    lien = db.get_or_404(Lien, lien_id)
    if current_user.user_type == "admin":
        form = LienFormCFAC(obj=lien)
    elif current_user.user_type in ["ro_motor_tp", "ro_user"]:
        if current_user.ro_code != lien.ro_code:
            return redirect(url_for("lien.lien_view", lien_id=lien.id))
        form = LienFormRO(obj=lien)

    elif current_user.user_type in ["ho_motor_tp"]:
        form = LienFormHOTP(obj=lien)
    else:
        flash("You are not authorized to edit this lien.", "danger")
        return redirect(url_for("lien.lien_view", lien_id=lien.id))
    form.model_obj = lien
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
            "court_order_lien": lien.court_order_lien,
            "court_order_dd": lien.court_order_dd,
            "court_order_lien_reversal": lien.court_order_lien_reversal,
            "court_order_dd_reversal": lien.court_order_dd_reversal,
            "appeal_copy": lien.appeal_copy,
            "appeal_copy_2": lien.appeal_copy_2,
            "stay_order": lien.stay_order,
            "lien_dd_reversal_order": lien.lien_dd_reversal_order,
            "claim_disbursement_voucher": lien.claim_disbursement_voucher,
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
    query = db.select(Lien)

    if current_user.user_type in ["ro_motor_tp", "ro_user"]:
        query = query.where(Lien.ro_code == current_user.ro_code)
    liens = db.session.scalars(query)
    column_names = [column.name for column in Lien.__table__.columns][0:38]
    return render_template("lien_list.html", lien_list=liens, column_names=column_names)


@event.listens_for(Session, "before_flush")
def mark_duplicates(session, flush_context, instances):
    # 1. Handle new objects
    for obj in session.new:
        if isinstance(obj, Lien):
            existing_liens = (
                session.query(Lien)
                .filter(Lien.lien_amount == obj.lien_amount, Lien.id != obj.id)
                .all()
            )

            if existing_liens:
                obj.is_duplicate = True
                for lien in existing_liens:
                    lien.is_duplicate = True

    # 2. Handle updated objects
    for obj in session.dirty:
        if isinstance(obj, Lien) and session.is_modified(
            obj, include_collections=False
        ):
            existing_liens = (
                session.query(Lien)
                .filter(Lien.lien_amount == obj.lien_amount, Lien.id != obj.id)
                .all()
            )

            if existing_liens:
                obj.is_duplicate = True
                for lien in existing_liens:
                    lien.is_duplicate = True
            else:
                # If no duplicates anymore, reset flag
                obj.is_duplicate = False


@lien_bp.route("/duplicates", methods=["GET"])
@login_required
@admin_required
def lien_duplicates():

    query = db.select(Lien).where(Lien.is_duplicate == True)

    liens = db.session.scalars(query)
    column_names = [column.name for column in Lien.__table__.columns][0:38]

    show_checkbox = True
    return render_template(
        "lien_list.html",
        lien_list=liens,
        column_names=column_names,
        show_checkbox=show_checkbox,
    )


@lien_bp.route("/duplicates/mark_as_not_duplicate/", methods=["POST"])
@login_required
@admin_required
def mark_lien_as_not_duplicates():
    selected_ids = request.form.getlist("selected_ids")
    if not selected_ids:
        flash("No rows selected", "warning")
        return redirect(url_for("lien.lien_duplicates"))

    db.session.query(Lien).filter(Lien.id.in_(selected_ids)).update(
        {Lien.is_duplicate: False}, synchronize_session=False
    )
    db.session.commit()
    flash(f"{len(selected_ids)} rows marked as not duplicate", "success")
    return redirect(url_for("lien.lien_duplicates"))


@lien_bp.route("/upload", methods=["GET", "POST"])
@login_required
@admin_required
def lien_bulk_upload():
    form = LienUploadForm()
    if form.validate_on_submit():
        lien_file = form.lien_file.data

        try:
            df = pd.read_excel(lien_file)
            df["ro_code"] = df["ro_code"].astype(str).str.zfill(6)
            ro_codes_in_file = set(df["ro_code"].dropna())
            invalid_codes = ro_codes_in_file - ALLOWED_RO_CODES

            if invalid_codes:
                flash(
                    f"Upload failed. Invalid RO codes found: {', '.join(invalid_codes)}",
                    "danger",
                )
                return redirect(url_for("lien.lien_bulk_upload"))

            # Insert valid rows
            for row in df.to_dict(orient="records"):
                lien = Lien(**row)
                db.session.add(lien)

            db.session.commit()
            flash(f"Successfully uploaded {len(df)} liens.", "success")

        except Exception as e:
            db.session.rollback()
            flash(f"Upload failed. Error: {str(e)}", "danger")

        return redirect(url_for("lien.lien_bulk_upload"))

    return render_template("lien_bulk_upload.html", title="Upload Liens", form=form)


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


@lien_bp.route("/dashboard", methods=["GET", "POST"])
@login_required
def lien_dashboard():

    # 1. Get distinct statuses
    lien_status_query = (
        db.session.query(Lien.lien_status).distinct().order_by(Lien.lien_status)
    )
    lien_statuses = [item[0] for item in lien_status_query]

    # 2. Build dynamic case statements
    status_columns = []
    status_labels = {}  # mapping from original -> sanitized
    for status in lien_statuses:
        safe_status = sanitize_status(status)
        status_labels[status] = safe_status

        col_count = func.count(case((Lien.lien_status == status, 1))).label(
            f"count_{safe_status}"
        )
        col_sum = func.sum(
            case((Lien.lien_status == status, Lien.lien_amount), else_=0)
        ).label(f"sum_{safe_status}")
        status_columns.extend([col_count, col_sum])

    # 3. Build main query
    query = (
        db.select(
            Lien.ro_code,
            Lien.bank_name,
            Lien.account_number,
            *status_columns,
            func.count(Lien.id).label("total_count"),
            func.sum(Lien.lien_amount).label("total_amount"),
        )
        .group_by(Lien.ro_code, Lien.bank_name, Lien.account_number)
        .order_by(Lien.ro_code, Lien.bank_name)
    )

    # 4. Apply filter for RO users
    if current_user.user_type in ["ro_motor_tp", "ro_user"]:
        query = query.where(Lien.ro_code == current_user.ro_code)
    lien_query = db.session.execute(query)
    return render_template(
        "lien_dashboard.html",
        lien_data=lien_query,
        lien_statuses=lien_statuses,
        status_labels=status_labels,
    )


def sanitize_status(status: str) -> str:
    """Make status safe for SQLAlchemy labels (replace spaces, special chars)."""
    if status:
        return re.sub(r"\W+", "_", status.strip())
    else:
        return ""


@lien_bp.context_processor
def get_duplicate_count():

    duplicate_count = db.session.scalar(
        db.select(func.count(Lien.id)).where(Lien.is_duplicate == True)
    )

    return dict(duplicate_count=duplicate_count)
