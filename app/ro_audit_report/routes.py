from datetime import datetime
from pathlib import Path

import pandas as pd

from flask import (
    redirect,
    render_template,
    url_for,
    flash,
    current_app,
    send_from_directory,
    request,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename


from extensions import db
from set_view_permissions import admin_required, ro_user_only
from app.users.user_model import User

from . import ro_audit_report_bp
from .models import (
    RegionalOfficeAuditObservation,
    RegionalOfficeAuditReport,
    AuditorRegionalOfficeMapping,
)

from .forms import (
    BulkUploadForm,
    RegionalOfficeAuditObservationForm,
    RegionalOfficeAuditReportUploadForm,
    AuditorMappingBulkForm,
)

PERIOD = "March-2026"


@ro_audit_report_bp.route("/upload", methods=["GET", "POST"])
@login_required
@admin_required
def bulk_upload_items():
    form = BulkUploadForm()
    if form.validate_on_submit():
        audit_report_file = form.upload_file.data

        df = pd.read_excel(audit_report_file, dtype={"regional_office_code": str})

        db.session.execute(
            db.insert(RegionalOfficeAuditReport), df.to_dict(orient="records")
        )
        db.session.execute(
            db.insert(AuditorRegionalOfficeMapping), df.to_dict(orient="records")
        )
        db.session.commit()
        flash(f"Successfully uploaded {len(df)} RO items.", "success")
    return render_template(
        "ro_audit_report_form.html", form=form, title="Bulk upload RO audit report list"
    )


@ro_audit_report_bp.route("/reports/<int:id>/upload", methods=["GET", "POST"])
@login_required
@ro_user_only
def ro_report_upload(id):
    audit_report = db.get_or_404(RegionalOfficeAuditReport, id)
    audit_report.require_access(current_user)
    form = RegionalOfficeAuditReportUploadForm(obj=audit_report)
    if form.validate_on_submit():
        form.populate_obj(audit_report)
        if form.data["audit_report_file"]:
            upload_document(
                model_object=audit_report,
                form=form,
                field="audit_report_file",
                document_type="audit_report",
                folder_name="audit_report",
            )
        if form.data["annexures_file"]:
            upload_document(
                model_object=audit_report,
                form=form,
                field="annexures_file",
                document_type="annexures",
                folder_name="annexures",
            )
        if form.data["notes_forming_part_of_accounts_file"]:
            upload_document(
                model_object=audit_report,
                form=form,
                field="notes_forming_part_of_accounts_file",
                document_type="notes_forming_part_of_accounts",
                folder_name="notes_forming_part_of_accounts",
            )
        db.session.commit()
        return redirect(url_for(".ro_report_view", id=id))

    return render_template(
        "ro_audit_report_upload_form.html",
        form=form,
        title="Upload audit report",
        report=audit_report,
    )


@ro_audit_report_bp.route("/reports/<int:id>/", methods=["GET", "POST"])
@login_required
@ro_user_only
def ro_report_view(id):
    audit_report = db.get_or_404(RegionalOfficeAuditReport, id)
    audit_report.require_access(current_user)

    return render_template("ro_audit_report_view.html", report=audit_report)


@ro_audit_report_bp.route("/reports/<int:id>/<string:requirement>/")
@login_required
def download_audit_report_document(id, requirement):
    audit_report = db.get_or_404(RegionalOfficeAuditReport, id)

    path = Path(getattr(audit_report, requirement))

    upload_root = current_app.config.get("UPLOAD_FOLDER_PATH")
    folder_path = upload_root / "ro_audit_report" / requirement

    if requirement == "notes_forming_part_of_accounts":
        requirement = "notes_forming_part_of_audit_report"
    download_name = f"{audit_report.regional_office_name}_{requirement}{path.suffix}"

    return send_from_directory(
        directory=folder_path,
        path=path.name,
        as_attachment=True,
        download_name=download_name,
    )


@ro_audit_report_bp.route("/", methods=["GET", "POST"])
@login_required
def ro_audit_reports_list():
    stmt = db.select(RegionalOfficeAuditReport).where(
        RegionalOfficeAuditReport.period == PERIOD
    )
    if current_user.user_type == "ro_user":
        stmt = stmt.where(
            RegionalOfficeAuditReport.regional_office_code == current_user.ro_code
        )
    elif current_user.user_type == "ho_stat_audit":
        stmt = get_audit_reports_for_ho_stat_audit(current_user.id)
    audit_report = db.session.scalars(stmt)

    return render_template(
        "ro_audit_reports_list.html",
        title="Audit report",
        audit_report=audit_report,
    )


def get_audit_reports_for_ho_stat_audit(user_id: int):
    return (
        db.select(RegionalOfficeAuditReport)
        .join(
            AuditorRegionalOfficeMapping,
            db.and_(
                AuditorRegionalOfficeMapping.user_id == user_id,
                AuditorRegionalOfficeMapping.regional_office_code
                == RegionalOfficeAuditReport.regional_office_code,
                AuditorRegionalOfficeMapping.period == RegionalOfficeAuditReport.period,
            ),
        )
        .where(RegionalOfficeAuditReport.period == PERIOD)
    )


def get_audit_observations_for_ho_stat_audit(user_id: int):
    return (
        db.select(RegionalOfficeAuditObservation)
        .join(
            AuditorRegionalOfficeMapping,
            db.and_(
                AuditorRegionalOfficeMapping.user_id == user_id,
                AuditorRegionalOfficeMapping.regional_office_code
                == RegionalOfficeAuditObservation.regional_office_code,
                AuditorRegionalOfficeMapping.period
                == RegionalOfficeAuditObservation.period,
            ),
        )
        .where(RegionalOfficeAuditObservation.period == PERIOD)
    )


@ro_audit_report_bp.route("/observations/", methods=["GET", "POST"])
@login_required
@ro_user_only
def ro_audit_observations_list():
    stmt = db.select(RegionalOfficeAuditObservation).where(
        RegionalOfficeAuditObservation.period == PERIOD
    )
    if current_user.user_type == "ro_user":
        stmt = stmt.where(
            RegionalOfficeAuditObservation.regional_office_code == current_user.ro_code
        )

    elif current_user.user_type == "ho_stat_audit":
        stmt = get_audit_observations_for_ho_stat_audit(current_user.id)
    audit_observations = db.session.scalars(stmt)

    return render_template(
        "ro_audit_observations_list.html",
        title="List of audit observations",
        audit_observations=audit_observations,
    )


@ro_audit_report_bp.route("/observations/add", methods=["GET", "POST"])
@login_required
@ro_user_only
def ro_audit_observations_add():
    form = RegionalOfficeAuditObservationForm()

    form.regional_office_code.data = current_user.ro_code
    if form.validate_on_submit():
        observation = RegionalOfficeAuditObservation()
        form.populate_obj(observation)
        db.session.add(observation)
        db.session.commit()
        return redirect(url_for(".ro_audit_observations_list"))
    return render_template(
        "ro_audit_report_form.html", form=form, title="Add audit observation"
    )


@ro_audit_report_bp.route("/observations/<int:id>/edit", methods=["GET", "POST"])
@login_required
@ro_user_only
def ro_audit_observations_edit(id):
    observation = db.get_or_404(RegionalOfficeAuditObservation, id)
    observation.require_access(current_user)
    form = RegionalOfficeAuditObservationForm(obj=observation)
    if form.validate_on_submit():
        form.populate_obj(observation)
        db.session.commit()
        return redirect(url_for(".ro_audit_observations_list"))
    return render_template(
        "ro_audit_report_form.html", form=form, title="Edit audit observation"
    )


def upload_document(*, model_object, form, field, document_type, folder_name):
    """
    Uploads a document to the folder specified by folder_name and saves the filename to the object.

    :param object: The object to save the filename to
    :param form: The form containing the file to upload
    :param field: The name of the field in the form containing the file to upload
    :param document_type: The type of document being uploaded (e.g. "statement", "confirmation")
    :param folder_name: The folder to save the document in
    """
    upload_root = current_app.config.get("UPLOAD_FOLDER_PATH")
    folder_path = upload_root / "ro_audit_report" / folder_name

    folder_path.mkdir(parents=True, exist_ok=True)
    file = form.data.get(field)

    if file:
        filename = secure_filename(file.filename)
        file_extension = Path(filename).suffix
        document_filename = f"{document_type}_{datetime.now().strftime('%d%m%Y %H%M%S')}{file_extension}"

        file.save(folder_path / document_filename)

        setattr(model_object, document_type, document_filename)


@ro_audit_report_bp.route("/auditor-mapping/bulk-update", methods=["GET", "POST"])
@admin_required
def bulk_update_auditor_mapping():
    # 1. Fetch choices once
    auditor_list = db.session.execute(
        db.select(User.id, User.display_name)
        .where(User.user_type == "ho_stat_audit")
        .order_by(User.display_name)
    ).all()

    auditor_choices = [(0, "-- None --")] + auditor_list

    if request.method == "GET":
        mappings_db = db.session.scalars(
            db.select(AuditorRegionalOfficeMapping)
            .where(AuditorRegionalOfficeMapping.period == PERIOD)
            .order_by(AuditorRegionalOfficeMapping.regional_office_code)
        ).all()
        # Initializing with database objects (Flask-WTF maps attributes to field names automatically)
        init_data = [
            {
                "mapping_id": m.id,
                "regional_office_code": m.regional_office_code,
                "regional_office_name": m.regional_office_name,
                "period": m.period,
                "user_id": m.user_id or 0,
            }
            for m in mappings_db
        ]
        form = AuditorMappingBulkForm(mappings=init_data)
    else:
        # On POST, initialize with request data
        form = AuditorMappingBulkForm()

    # 2. CRITICAL: Inject choices into every sub-form in the FieldList
    # This must happen for both GET and POST
    for subform in form.mappings:
        subform.user_id.choices = auditor_choices

    # 3. Handle Validation and Submission
    if form.validate_on_submit():
        for subform in form.mappings:
            # Access data via subform.field.data
            mapping_id = subform.mapping_id.data
            selected_user_id = subform.user_id.data

            mapping = db.get_or_404(AuditorRegionalOfficeMapping, mapping_id)
            if mapping:
                # Convert our "0" placeholder back to None for the DB
                mapping.user_id = selected_user_id if selected_user_id != 0 else None

        db.session.commit()
        flash("Mappings updated successfully.", "success")
        return redirect(url_for(".bulk_update_auditor_mapping"))

    return render_template(
        "auditor_mapping_bulk_update.html",
        form=form,
        title="Update HO Auditor - RO mapping",
    )
