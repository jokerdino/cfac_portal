from datetime import datetime
from pathlib import Path

from flask import (
    redirect,
    render_template,
    url_for,
    current_app,
    send_from_directory,
    abort,
)
from flask_login import login_required
from werkzeug.utils import secure_filename

from . import ci_bp
from .models import ChangeInstruction
from .forms import ChangeInstructionForm

from set_view_permissions import admin_required
from extensions import db


def upload_document_to_folder(ci_obj, model_attribute, form, field, folder_name):
    base_path = current_app.config.get("UPLOAD_FOLDER_PATH")
    folder_path = base_path / "ci" / folder_name

    # Create folders if missing
    folder_path.mkdir(parents=True, exist_ok=True)

    # Check if file exists in the form
    file = form.data.get(field)
    if file:
        filename = secure_filename(file.filename)

        file_extension = Path(filename).suffix
        document_filename = (
            f"{folder_name}_{datetime.now().strftime('%d%m%Y %H%M%S')}{file_extension}"
        )

        # Save file
        file.save(folder_path / document_filename)

        # Assign filename to model attribute
        setattr(ci_obj, model_attribute, document_filename)


@ci_bp.route("/add", methods=["GET", "POST"])
@login_required
@admin_required
def ci_add():
    form = ChangeInstructionForm()

    if form.validate_on_submit():
        ci = ChangeInstruction()
        form.populate_obj(ci)
        db.session.add(ci)
        upload_document_to_folder(
            ci, "ci_document", form, "ci_document_file", "ci_document"
        )
        upload_document_to_folder(
            ci,
            "approach_note_document",
            form,
            "approach_note_document_file",
            "approach_note_document",
        )
        db.session.commit()
        return redirect(url_for(".ci_view", id=ci.id))
    return render_template("ci_edit_new.html", form=form, title="Add new CI")


@ci_bp.route("/edit/<int:id>/", methods=["GET", "POST"])
@login_required
@admin_required
def ci_edit(id):
    ci = db.get_or_404(ChangeInstruction, id)
    form = ChangeInstructionForm(obj=ci)
    if form.validate_on_submit():
        form.populate_obj(ci)
        upload_document_to_folder(
            ci, "ci_document", form, "ci_document_file", "ci_document"
        )
        upload_document_to_folder(
            ci,
            "approach_note_document",
            form,
            "approach_note_document_file",
            "approach_note_document",
        )
        db.session.commit()
        return redirect(url_for(".ci_view", id=ci.id))
    if ci.ci_document:
        # Generate the complete download URL using your existing route
        form.ci_document_file.data = url_for(
            "ci.download_ci_document", id=ci.id, document_type="ci_document"
        )

    if ci.approach_note_document:
        # Generate the complete download URL for the approach note
        form.approach_note_document_file.data = url_for(
            "ci.download_ci_document",
            id=ci.id,
            document_type="approach_note_document",
        )
    return render_template("ci_edit_new.html", form=form, title="Edit CI", ci=ci)


@ci_bp.route("/view/<int:id>/", methods=["GET", "POST"])
@login_required
@admin_required
def ci_view(id):
    ci = db.get_or_404(ChangeInstruction, id)

    return render_template("ci_view.html", ci=ci)


@ci_bp.route("/download/<int:id>/<string:document_type>/")
@login_required
@admin_required
def download_ci_document(id, document_type):
    ci = db.get_or_404(ChangeInstruction, id)
    base_path = current_app.config.get("UPLOAD_FOLDER_PATH")
    folder_path = base_path / "ci" / document_type

    if document_type == "ci_document":
        filename = ci.ci_document
    elif document_type == "approach_note_document":
        filename = ci.approach_note_document
    else:
        abort(404)
    if not filename:
        abort(404)

    file_path = folder_path / filename
    if not file_path.exists():
        abort(404)

    stored_path = Path(filename)
    file_extension = stored_path.suffix
    download_name = f"{document_type}_{ci.title}{file_extension}"

    return send_from_directory(
        directory=folder_path,
        path=stored_path.name,
        as_attachment=True,
        download_name=download_name,
    )


@ci_bp.route("/")
@login_required
@admin_required
def ci_list():
    ci_list = db.session.scalars(db.select(ChangeInstruction))
    column_headers = [
        "title",
        "description",
        "current_status",
        "ticket_date",
        "ticket_number",
        "ci_document",
        "ci_number",
        "approach_note_date",
        "approach_note_document",
        "approach_note_approval_date",
        "uat_testing_date",
        "uat_remarks",
        "pilot_deployment_date",
        "production_deployment_date",
    ]
    return render_template(
        "ci_list.html", ci_list=ci_list, column_headers=column_headers
    )
