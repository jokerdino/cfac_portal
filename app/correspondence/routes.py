from datetime import datetime
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
from .forms import CircularForm
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

        circular.circular_number = f"HO:CFAC:{year}/{month:02d}/{number:03d}"
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
    return render_template("circular_edit.html", form=form, title="Add new circular")


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
    return render_template("circular_edit.html", form=form, title="Edit circular")


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
            "circular_number",
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
    return render_template("circular_list.html", table=table, title="Circulars")


@correspondence_bp.get("/<string:document_type>/download/<int:circular_id>/")
@login_required
@admin_required
def download_document(document_type, circular_id):
    model_dict = {
        "circular": (Circular, "circular_title"),
        "inwardDocument": (InwardDocument, "description_of_item"),
        "outwardDocument": (OutwardDocument, "description_of_item"),
    }
    model, field = model_dict[document_type]
    model_obj = db.get_or_404(model, circular_id)

    path = model_obj.upload_document
    if not path:
        abort(404)

    file_extension = path.rsplit(".", 1)[-1]
    file_title = getattr(model_obj, field)

    filename = f"{model_obj.circular_number}_{file_title}.{file_extension}"
    return send_from_directory(
        directory=f"{current_app.config.get('UPLOAD_FOLDER')}correspondence/{document_type}/",
        path=path,
        as_attachment=True,
        download_name=filename,
    )
