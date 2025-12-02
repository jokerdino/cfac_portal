from datetime import datetime
import re

from flask import (
    abort,
    render_template,
    redirect,
    url_for,
    current_app,
    send_from_directory,
)  # , Markup
from flask_login import login_required
from markupsafe import Markup

from . import correspondence_bp
from .models import Circular, InwardDocument, OutwardDocument
from .forms import CircularForm, InwardForm, OutwardForm
from .utils import get_last_number, upload_document_to_folder
from extensions import db
from set_view_permissions import admin_required
from app.main.table_helper import Table, Column


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
        return redirect(
            url_for("correspondence.circular_view", circular_id=circular.id)
        )
    return render_template(
        "correspondence_edit.html", form=form, title="Add new circular"
    )


@correspondence_bp.route("/circular/<int:circular_id>/", methods=["GET"])
@login_required
@admin_required
def circular_view(circular_id):
    circular = db.get_or_404(Circular, circular_id)
    return render_template("circular_view.html", circular=circular)


@correspondence_bp.route("/circular/<int:circular_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def circular_edit(circular_id):
    circular = db.get_or_404(Circular, circular_id)
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
        return redirect(
            url_for("correspondence.circular_view", circular_id=circular.id)
        )
    return render_template("correspondence_edit.html", form=form, title="Edit circular")


@correspondence_bp.route("/circular/", methods=["GET", "POST"])
@login_required
@admin_required
def circular_list():
    table = Table(
        Circular,
        classes="table table-striped table-bordered",
        id="circular_table",
        paginate=False,
        only=[
            "date_of_issue",
            "reference_number",
            "circular_title",
            "issued_by_name",
            "issued_by_designation",
            "recipients",
            "remarks",
        ],
        extra_columns=[
            (
                "view",
                Column(
                    "View",
                    formatter=lambda u: Markup(
                        f"<a href='{url_for('.circular_view', circular_id=u.id)}'>View</a>"
                    ),
                    is_html=True,
                ),
            ),
            (
                "edit",
                Column(
                    "Edit",
                    formatter=lambda u: Markup(
                        f"<a href='{url_for('.circular_edit', circular_id=u.id)}'>Edit</a>"
                    ),
                    is_html=True,
                ),
            ),
        ],
    )
    return render_template("correspondence_list.html", table=table, title="Circulars")


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

    path = model_obj.upload_document
    if not path:
        abort(404)

    file_extension = path.rsplit(".", 1)[-1]

    def clean_filename(name: str) -> str:
        # Remove newlines (causes send_file header break)
        name = name.replace("\n", "").replace("\r", "")

        # Remove only characters not allowed by OS or HTTP headers
        return re.sub(r'[\\/:*?"<>|]', "", name).strip()

    file_title = clean_filename(getattr(model_obj, field))
    filename = f"{model_obj.reference_number}_{file_title}.{file_extension}"
    return send_from_directory(
        directory=f"{current_app.config.get('UPLOAD_FOLDER')}correspondence/{document_type}/",
        path=path,
        as_attachment=True,
        download_name=filename,
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
        return redirect(url_for("correspondence.inward_view", inward_id=inward.id))
    return render_template(
        "correspondence_edit.html", form=form, title="Add new inward document"
    )


@correspondence_bp.route("/inward/", methods=["GET", "POST"])
@login_required
@admin_required
def inward_list():
    table = Table(
        InwardDocument,
        classes="table table-striped table-bordered",
        id="inward_table",
        paginate=False,
        only=[
            "reference_number",
            "date_of_receipt",
            "time_of_receipt",
            "sender_name",
            "letter_reference_number",
            "description_of_item",
            "recipient_name",
            "received_by",
            "remarks",
        ],
        extra_columns=[
            (
                "view",
                Column(
                    "View",
                    formatter=lambda u: Markup(
                        f"<a href='{url_for('.inward_view', inward_id=u.id)}'>View</a>"
                    ),
                    is_html=True,
                ),
            ),
            (
                "edit",
                Column(
                    "Edit",
                    formatter=lambda u: Markup(
                        f"<a href='{url_for('.inward_edit', inward_id=u.id)}'>Edit</a>"
                    ),
                    is_html=True,
                ),
            ),
        ],
    )
    return render_template("correspondence_list.html", table=table, title="Inwards")


@correspondence_bp.route("/inward/<int:inward_id>/", methods=["GET"])
@login_required
@admin_required
def inward_view(inward_id):
    inward = db.get_or_404(InwardDocument, inward_id)
    return render_template("inward_view.html", inward=inward)


@correspondence_bp.route("/inward/<int:inward_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def inward_edit(inward_id):
    inward = db.get_or_404(InwardDocument, inward_id)
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
        return redirect(url_for("correspondence.inward_view", inward_id=inward.id))
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
        return redirect(url_for("correspondence.outward_view", outward_id=outward.id))
    return render_template(
        "correspondence_edit.html", form=form, title="Add new outward document"
    )


@correspondence_bp.route("/outward/", methods=["GET", "POST"])
@login_required
@admin_required
def outward_list():
    table = Table(
        OutwardDocument,
        classes="table table-striped table-bordered",
        id="inward_table",
        paginate=False,
        only=[
            "reference_number",
            "date_of_dispatch",
            "time_of_dispatch",
            "description_of_item",
            "recipient_name",
            "sender_name",
            "dispatched_by",
            "remarks",
        ],
        extra_columns=[
            (
                "view",
                Column(
                    "View",
                    formatter=lambda u: Markup(
                        f"<a href='{url_for('.outward_view', outward_id=u.id)}'>View</a>"
                    ),
                    is_html=True,
                ),
            ),
            (
                "edit",
                Column(
                    "Edit",
                    formatter=lambda u: Markup(
                        f"<a href='{url_for('.outward_edit', outward_id=u.id)}'>Edit</a>"
                    ),
                    is_html=True,
                ),
            ),
        ],
    )
    return render_template("correspondence_list.html", table=table, title="Outwards")


@correspondence_bp.route("/outward/<int:outward_id>/", methods=["GET"])
@login_required
@admin_required
def outward_view(outward_id):
    outward = db.get_or_404(OutwardDocument, outward_id)
    return render_template("outward_view.html", outward=outward)


@correspondence_bp.route("/outward/<int:outward_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def outward_edit(outward_id):
    outward = db.get_or_404(OutwardDocument, outward_id)
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
        return redirect(url_for("correspondence.outward_view", outward_id=outward.id))
    return render_template("correspondence_edit.html", form=form, title="Edit outward")
