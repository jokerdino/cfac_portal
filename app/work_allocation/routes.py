import pandas as pd
from flask import redirect, render_template, url_for
from flask_login import login_required

from . import work_allocation_bp
from .models import WorkAllocation
from .forms import WorkAllocationEditForm, BulkUploadForm

from extensions import db

from set_view_permissions import admin_required


@work_allocation_bp.route("/")
@login_required
def work_allocation_home():
    work_allocation = db.session.scalars(db.select(WorkAllocation))

    return render_template("work_allocation_home.html", work_allocation=work_allocation)


@work_allocation_bp.route("/edit/<int:id>/", methods=["GET", "POST"])
@login_required
@admin_required
def work_allocation_edit(id):
    work_allocation = db.get_or_404(WorkAllocation, id)
    form = WorkAllocationEditForm(obj=work_allocation)

    if form.validate_on_submit():
        form.populate_obj(work_allocation)
        db.session.commit()

        return redirect(url_for("work_allocation.work_allocation_home"))
    return render_template(
        "work_allocation_form.html",
        work_allocation=work_allocation,
        form=form,
        title="Edit work allocation",
    )


@work_allocation_bp.route("/add/", methods=["GET", "POST"])
@login_required
@admin_required
def work_allocation_add():
    form = WorkAllocationEditForm()

    if form.validate_on_submit():
        work_allocation = WorkAllocation()
        form.populate_obj(work_allocation)
        db.session.add(work_allocation)
        db.session.commit()

        return redirect(url_for("work_allocation.work_allocation_home"))
    return render_template(
        "work_allocation_form.html", form=form, title="Add work allocation"
    )


@work_allocation_bp.route("/bulk_upload/", methods=["GET", "POST"])
@login_required
@admin_required
def work_allocation_bulk_upload():
    form = BulkUploadForm()

    if form.validate_on_submit():
        df = pd.read_excel(form.data["file"])
        df.columns = df.columns.str.lower().str.strip().str.replace(" ", "_")

        db.session.execute(db.insert(WorkAllocation), df.to_dict(orient="records"))
        db.session.commit()

        return redirect(url_for("work_allocation.work_allocation_home"))
    return render_template("work_allocation_form.html", form=form, title="Bulk upload")
