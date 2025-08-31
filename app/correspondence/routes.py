from flask import render_template, redirect, url_for  # , Markup
from flask_login import login_required
from markupsafe import Markup

from . import correspondence_bp
from .models import Circular, InwardDocument, OutwardDocument
from .forms import CircularForm

from extensions import db
from set_view_permissions import admin_required
from .table_helper import Table, Column


@correspondence_bp.route("/circular/add", methods=["GET", "POST"])
@login_required
@admin_required
def circular_add():
    form = CircularForm()
    if form.validate_on_submit():
        circular = Circular()
        form.populate_obj(circular)
        db.session.add(circular)
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
        db.session.commit()
        return redirect(
            url_for("correspondence.circular_view", circular_id=circular.id)
        )
    return render_template("circular_edit.html", form=form, title="Edit circular")


@correspondence_bp.route("/circular/", methods=["GET", "POST"])
@login_required
@admin_required
def circular_list():
    #    list = db.session.scalars(db.select(Circular))
    table = Table(
        Circular,
        classes="table table-striped table-bordered",
        id="circular_table",
        paginate=False,
        #        per_page=2,
        only=[
            "id",
            "date_of_issue",
            "circular_number",
            "circular_title",
            "issued_by",
            "mode_of_dispatch",
            "recipients",
            "number_of_copies",
            "date_of_acknowledgement",
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
