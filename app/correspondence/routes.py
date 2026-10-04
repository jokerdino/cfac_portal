import re
from pathlib import Path

from flask import (
    abort,
    current_app,
    redirect,
    render_template,
    send_from_directory,
    url_for,
)
from flask_login import login_required

from extensions import db
from set_view_permissions import admin_required

from . import correspondence_bp
from .forms import CircularForm, InwardForm, OutwardForm
from .models import Circular, InwardDocument, OutwardDocument
from .utils import get_last_number, upload_document_to_folder


@correspondence_bp.route("/circular/add", methods=["GET", "POST"])
@login_required
@admin_required
def circular_add():
    form = CircularForm()
    if form.validate_on_submit():
        circular = Circular()
        date_of_issue = form.date_of_issue.data
        year = date_of_issue.year
        month = date_of_issue.month
        last_doc_number = get_last_number(Circular, year, month)

        form.populate_obj(circular)
        db.session.add(circular)
        circular.year = circular.date_of_issue.year
        circular.month = circular.date_of_issue.month

        number = last_doc_number + 1 if last_doc_number else 1
        circular.number = number

        circular.reference_number = f"HO:CFAC:{year}/{month:02d}/{number:03d}"
        upload_document_to_folder(
            circular,
            form,
            "upload_document_file",
            "circular",
            "upload_document",
            "circular",
        )
        db.session.commit()
        return redirect(url_for("correspondence.circular_view", id=circular.id))
    return render_template(
        "correspondence_edit.html", form=form, title="Add new circular"
    )


@correspondence_bp.route("/circular/<int:id>/", methods=["GET"])
@login_required
@admin_required
def circular_view(id):
    circular = db.get_or_404(Circular, id)
    return render_template("circular_view.html", circular=circular)


@correspondence_bp.route("/circular/<int:id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def circular_edit(id):
    circular = db.get_or_404(Circular, id)
    form = CircularForm(obj=circular)
    if form.validate_on_submit():
        form.populate_obj(circular)
        upload_document_to_folder(
            circular,
            form,
            "upload_document_file",
            "circular",
            "upload_document",
            "circular",
        )
        db.session.commit()
        return redirect(url_for("correspondence.circular_view", id=circular.id))
    return render_template("correspondence_edit.html", form=form, title="Edit circular")


@correspondence_bp.route("/circular/", methods=["GET", "POST"])
@login_required
@admin_required
def circular_list():
    query = db.select(Circular).order_by(Circular.date_of_issue.desc())
    correspondence_list = db.session.scalars(query).all()
    column_names = [
        "date_of_issue",
        "reference_number",
        "circular_title",
        "issued_by_name",
        "issued_by_designation",
        "recipients",
        "remarks",
    ]

    return render_template(
        "correspondence_list.html",
        title="Circulars",
        correspondence_list=correspondence_list,
        column_names=column_names,
        edit_url=".circular_edit",
        view_url=".circular_view",
    )


@correspondence_bp.get("/<string:document_type>/download/<int:document_id>/")
@login_required
@admin_required
def download_document(document_type, document_id):
    model_dict = {
        "circular": (Circular, "circular_title"),
        "inward": (InwardDocument, "description_of_item"),
        "outward": (OutwardDocument, "description_of_item"),
    }
    model, field = model_dict[document_type]
    model_obj = db.get_or_404(model, document_id)

    stored_filename = model_obj.upload_document
    if not stored_filename:
        abort(404)

    stored_path = Path(stored_filename)

    file_extension = stored_path.suffix

    def clean_filename(name: str) -> str:
        # Remove newlines (causes send_file header break)
        name = name.replace("\n", "").replace("\r", "")

        # Remove only characters not allowed by OS or HTTP headers
        return re.sub(r'[\\/:*?"<>|]', "", name).strip()

    file_title = clean_filename(getattr(model_obj, field))
    download_name = f"{model_obj.reference_number}_{file_title}{file_extension}"
    base_directory = (
        current_app.config.get("UPLOAD_FOLDER_PATH") / "correspondence" / document_type
    )

    return send_from_directory(
        directory=base_directory,
        path=stored_path.name,
        as_attachment=True,
        download_name=download_name,
    )


@correspondence_bp.route("/inward/add", methods=["GET", "POST"])
@login_required
@admin_required
def inward_add():
    form = InwardForm()
    if form.validate_on_submit():
        inward = InwardDocument()
        date_of_receipt = form.date_of_receipt.data
        year = date_of_receipt.year
        month = date_of_receipt.month
        last_doc_number = get_last_number(InwardDocument, year, month)

        form.populate_obj(inward)
        db.session.add(inward)
        inward.year = inward.date_of_receipt.year
        inward.month = inward.date_of_receipt.month

        number = last_doc_number + 1 if last_doc_number else 1
        inward.number = number

        inward.reference_number = f"HO:CFAC:Inward:{year}/{month:02d}/{number:03d}"
        upload_document_to_folder(
            inward,
            form,
            "upload_document_file",
            "inward",
            "upload_document",
            "inward",
        )
        db.session.commit()
        return redirect(url_for("correspondence.inward_view", id=inward.id))
    return render_template(
        "correspondence_edit.html", form=form, title="Add new inward document"
    )


@correspondence_bp.route("/inward/", methods=["GET", "POST"])
@login_required
@admin_required
def inward_list():
    query = db.select(InwardDocument).order_by(InwardDocument.date_of_receipt.desc())
    correspondence_list = db.session.scalars(query).all()
    column_names = [
        "reference_number",
        "date_of_receipt",
        "time_of_receipt",
        "sender_name",
        "letter_reference_number",
        "description_of_item",
        "recipient_name",
        "received_by",
        "remarks",
    ]

    return render_template(
        "correspondence_list.html",
        title="Inwards",
        correspondence_list=correspondence_list,
        column_names=column_names,
        edit_url=".inward_edit",
        view_url=".inward_view",
    )


@correspondence_bp.route("/inward/<int:id>/", methods=["GET"])
@login_required
@admin_required
def inward_view(id):
    inward = db.get_or_404(InwardDocument, id)
    return render_template("inward_view.html", inward=inward)


@correspondence_bp.route("/inward/<int:id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def inward_edit(id):
    inward = db.get_or_404(InwardDocument, id)
    form = InwardForm(obj=inward)
    if form.validate_on_submit():
        form.populate_obj(inward)
        upload_document_to_folder(
            inward,
            form,
            "upload_document_file",
            "inward",
            "upload_document",
            "inward",
        )
        db.session.commit()
        return redirect(url_for("correspondence.inward_view", id=inward.id))
    return render_template("correspondence_edit.html", form=form, title="Edit inward")


@correspondence_bp.route("/outward/add", methods=["GET", "POST"])
@login_required
@admin_required
def outward_add():
    form = OutwardForm()
    if form.validate_on_submit():
        outward = OutwardDocument()
        date_of_dispatch = form.date_of_dispatch.data
        year = date_of_dispatch.year
        month = date_of_dispatch.month
        last_doc_number = get_last_number(OutwardDocument, year, month)

        form.populate_obj(outward)
        db.session.add(outward)
        outward.year = outward.date_of_dispatch.year
        outward.month = outward.date_of_dispatch.month

        number = last_doc_number + 1 if last_doc_number else 1
        outward.number = number

        outward.reference_number = f"HO:CFAC:Outward:{year}/{month:02d}/{number:03d}"
        upload_document_to_folder(
            outward,
            form,
            "upload_document_file",
            "outward",
            "upload_document",
            "outward",
        )
        db.session.commit()
        return redirect(url_for("correspondence.outward_view", id=outward.id))
    return render_template(
        "correspondence_edit.html", form=form, title="Add new outward document"
    )


@correspondence_bp.route("/outward/", methods=["GET", "POST"])
@login_required
@admin_required
def outward_list():
    query = db.select(OutwardDocument).order_by(OutwardDocument.date_of_dispatch.desc())
    correspondence_list = db.session.scalars(query).all()
    column_names = [
        "reference_number",
        "date_of_dispatch",
        "time_of_dispatch",
        "description_of_item",
        "recipient_name",
        "sender_name",
        "dispatched_by",
        "remarks",
    ]
    return render_template(
        "correspondence_list.html",
        title="Outwards",
        correspondence_list=correspondence_list,
        column_names=column_names,
        edit_url=".outward_edit",
        view_url=".outward_view",
    )


@correspondence_bp.route("/outward/<int:id>/", methods=["GET"])
@login_required
@admin_required
def outward_view(id):
    outward = db.get_or_404(OutwardDocument, id)
    return render_template("outward_view.html", outward=outward)


@correspondence_bp.route("/outward/<int:id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def outward_edit(id):
    outward = db.get_or_404(OutwardDocument, id)
    form = OutwardForm(obj=outward)
    if form.validate_on_submit():
        form.populate_obj(outward)
        upload_document_to_folder(
            outward,
            form,
            "upload_document_file",
            "outward",
            "upload_document",
            "outward",
        )
        db.session.commit()
        return redirect(url_for("correspondence.outward_view", id=outward.id))
    return render_template("correspondence_edit.html", form=form, title="Edit outward")
