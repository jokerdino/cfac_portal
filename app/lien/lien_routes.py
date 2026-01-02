from datetime import datetime
import os
import re
from pathlib import Path
import threading


import pandas as pd
import numpy as np
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
from sqlalchemy import func, case, event, and_, or_
from sqlalchemy.orm import Session

from flask_login import login_required, current_user
from sqlalchemy_continuum import version_class, versioning_manager

from werkzeug.utils import secure_filename

from extensions import db
from set_view_permissions import admin_required

from . import lien_bp
from .lien_model import Lien, LienRegionalOfficeEmailAddress
from .lien_forms import (
    LienFormCFAC,
    LienFormRO,
    LienUploadForm,
    LienFormHOTP,
    LienStatusFilterForm,
    ALLOWED_RO_CODES,
)

from app.users.user_model import User
from app.contacts.contacts_model import Contacts

from app.users.mail_utils import send_email_async


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
        send_lien_email(lien)
        return redirect(url_for("lien.lien_view", lien_id=lien.id))
    return render_template("lien_edit.html", form=form, title="Add new lien")


def fetch_recipient_email_addresses(ro_code: str) -> list[str]:
    regional_accountants = db.session.scalars(
        db.select(Contacts.email_address).where(
            Contacts.office_code == ro_code,
            Contacts.role.in_(
                [
                    "Regional Accountant",
                    "Second Officer",
                ]
            ),
        )
    )
    tp_email_address = db.session.scalar(
        db.select(LienRegionalOfficeEmailAddress.ro_email_address).where(
            LienRegionalOfficeEmailAddress.ro_code == ro_code
        )
    )

    recipients = [*regional_accountants, tp_email_address]

    return recipients


def send_lien_email(lien):
    recipients: list[str] = fetch_recipient_email_addresses(lien.ro_code)

    # TODO: Comment out below code when live
    recipients = ["44515"]

    attachments = []
    if lien.court_order_lien:
        file_path = (
            Path(current_app.config["UPLOAD_FOLDER"])
            / "lien"
            / "court_order_lien"
            / lien.court_order_lien
        )

        if file_path.exists():
            attachments.append(file_path)
        else:
            raise RuntimeError(f"File not found: {file_path}")
    html_body = render_template(
        "partials/lien_email_template.html",
        lien=lien,
    )
    app = current_app._get_current_object()

    thread = threading.Thread(
        target=send_email_async,
        kwargs={
            "app": app,
            "subject": "Lien",
            "recipients": recipients,
            "cc": ["44515"],
            "bcc": ["barneedhar@uiic.co.in"],
            "body": "Please view this email in HTML.",
            "html": html_body,
            "attachments": attachments,
        },
        daemon=True,
    )
    thread.start()


@lien_bp.route("/view/<int:lien_id>/", methods=["GET", "POST"])
@login_required
def lien_view(lien_id):
    lien = db.get_or_404(Lien, lien_id)
    lien.require_access(current_user)
    return render_template("lien_view.html", lien=lien)


@lien_bp.route("/log/<int:lien_id>/")
@login_required
def lien_log_view(lien_id):
    LienVersion = version_class(Lien)
    col_names = [col.key for col in Lien.__table__.columns]

    stmt = (
        db.select(LienVersion)
        .where(LienVersion.id == lien_id)
        .order_by(LienVersion.transaction_id.asc())
    )
    lien_log = db.session.scalars(stmt)
    return render_template(
        "lien_log_view.html", lien_log=lien_log, column_names=col_names, lien_id=lien_id
    )


@lien_bp.route("/api/edited_ids/")
@login_required
@admin_required
def lien_edited_ids():
    LienVersion = version_class(Lien)
    Transaction = versioning_manager.transaction_cls

    stmt = (
        db.select(
            Lien.id, LienVersion.transaction_id, Transaction.issued_at, User.username
        )
        .join(LienVersion, LienVersion.id == Lien.id)
        .join(Transaction, LienVersion.transaction_id == Transaction.id)
        .join(User, User.id == Transaction.user_id)
        .where(User.user_type != "admin")
        .order_by(Transaction.issued_at.desc())
    )

    rows = db.session.execute(stmt).mappings().all()

    return render_template(
        "partials/edited_ids.html",
        rows=rows,
    )


@lien_bp.get("/api/changes/<int:id>/<int:tx_id>/")
@login_required
@admin_required
def api_changes(id, tx_id):
    LienVersion = version_class(Lien)

    # Composite PK lookup
    version = db.get_or_404(LienVersion, (id, tx_id))

    diff = version.changeset or {}
    return render_template("partials/lien_changes.html", diff=diff, id=id)


@lien_bp.route("/edited_by_ro_users")
@login_required
@admin_required
def edited_by_ro_users():
    return render_template("edited_by_ro.html")


@lien_bp.route("/edit/<int:lien_id>/", methods=["GET", "POST"])
@login_required
def lien_edit(lien_id):
    lien = db.get_or_404(Lien, lien_id)
    lien.require_access(current_user)
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
    lien.require_access(current_user)

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


@lien_bp.route("/", methods=["POST", "GET"])
@login_required
def lien_list():
    query = db.select(Lien)

    if current_user.user_type in ["ro_motor_tp", "ro_user"]:
        query = query.where(Lien.ro_code == current_user.ro_code)

    form = LienStatusFilterForm()
    populate_status(query, form)

    if form.validate_on_submit():
        status = form.lien_status.data
        if status != "View all":
            query = query.where(Lien.lien_status == status)

    liens = db.session.scalars(query)
    column_names = [column.name for column in Lien.__table__.columns][0:38]
    return render_template(
        "lien_list.html", lien_list=liens, column_names=column_names, form=form
    )


def populate_status(stmt, form):
    subq = stmt.subquery()

    status_list = db.session.scalars(
        db.select(db.distinct(subq.c.lien_status)).order_by(subq.c.lien_status)
    ).all()

    form.lien_status.choices = ["View all"] + status_list


@lien_bp.route("/review", methods=["POST", "GET"])
@login_required
@admin_required
def lien_list_review():
    review_query = db.select(Lien).where(
        or_(
            and_(
                Lien.lien_status == "Lien exists",
                Lien.court_order_lien_reversal.is_not(None),
            ),
            and_(
                Lien.lien_status == "DD issued",
                Lien.court_order_dd_reversal.is_not(None),
            ),
        )
    )

    form = LienStatusFilterForm()
    populate_status(review_query, form)

    if form.validate_on_submit():
        status = form.lien_status.data
        if status != "View all":
            review_query = review_query.where(Lien.lien_status == status)
    liens = db.session.scalars(review_query)
    column_names = [column.name for column in Lien.__table__.columns][0:38]
    return render_template(
        "lien_list.html", lien_list=liens, column_names=column_names, form=form
    )


@event.listens_for(Session, "before_flush")
def mark_duplicates(session, flush_context=None, instances=None):
    # Handle new and dirty Lien objects
    liens_to_check = [
        obj
        for obj in session.new.union(session.dirty)
        if isinstance(obj, Lien) and session.is_modified(obj, include_collections=False)
    ]

    for obj in liens_to_check:
        # Query other liens with same amount (exclude current obj by identity)
        existing_liens = session.scalars(
            db.select(Lien).where(
                Lien.lien_amount == obj.lien_amount,
                Lien.id.isnot(None),  # exclude transient objects
                Lien.id != obj.id if obj.id else True,  # sanity guard
            )
        ).all()

        # Update duplicate marker flags
        is_duplicate = len(existing_liens) > 0
        obj.is_duplicate = is_duplicate

        if is_duplicate:
            for lien in existing_liens:
                lien.is_duplicate = True


@lien_bp.route("/duplicates", methods=["GET"])
@login_required
@admin_required
def lien_duplicates():
    query = db.select(Lien).where(Lien.is_duplicate)

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
    selected_ids = [int(i) for i in selected_ids]
    if not selected_ids:
        flash("No rows selected", "warning")
        return redirect(url_for("lien.lien_duplicates"))

    stmt = db.update(Lien).where(Lien.id.in_(selected_ids)).values(is_duplicate=False)

    db.session.execute(stmt)
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
            df = pd.read_excel(lien_file, dtype={"ro_code": str, "case_number": str})
            df["ro_code"] = df["ro_code"].astype(str).str.zfill(6)

            df = df.where(pd.notnull(df), None)
            df = df.replace({pd.NaT: None, np.nan: None})
            ro_codes_in_file = set(df["ro_code"].dropna())
            invalid_codes = ro_codes_in_file - ALLOWED_RO_CODES

            if invalid_codes:
                flash(
                    f"Upload failed. Invalid RO codes found: {', '.join(invalid_codes)}",
                    "danger",
                )
                return redirect(url_for("lien.lien_bulk_upload"))

            # Check for duplicates

            # mark duplicate within the file
            df["is_duplicate"] = df.duplicated(subset=["lien_amount"], keep=False)

            # mark duplicate in the database
            upload_amounts = set(df["lien_amount"].dropna())
            stmt = (
                db.update(Lien)
                .where(Lien.lien_amount.in_(upload_amounts))
                .values(is_duplicate=True)
            )

            db.session.execute(stmt)
            db.session.commit()

            # Insert valid rows
            records = df.to_dict(orient="records")

            # ORM aware bulk insert
            # for marking duplicate entries
            db.session.add_all(Lien(**row) for row in records)
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
    lien_statuses = db.session.scalars(
        db.select(Lien.lien_status).distinct().order_by(Lien.lien_status)
    ).all()

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
        .order_by(Lien.ro_code, Lien.bank_name, Lien.account_number)
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
        db.select(func.count()).select_from(Lien).where(Lien.is_duplicate)
    )
    lien_query = db.select(Lien).where(
        (Lien.lien_status == "Lien exists")
        & (Lien.court_order_lien_reversal.is_not(None))
    )
    dd_query = db.select(Lien).where(
        (Lien.lien_status == "DD issued") & (Lien.court_order_dd_reversal.is_not(None))
    )
    union_query = db.union_all(lien_query, dd_query)

    review_count = db.session.scalar(
        db.select(func.count()).select_from(union_query.subquery())
    )

    return dict(duplicate_count=duplicate_count, review_count=review_count)
