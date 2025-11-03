from datetime import datetime, date
from dateutil.relativedelta import relativedelta

import pandas as pd
from flask import redirect, render_template, url_for, flash

from flask_login import current_user, login_required


from . import mis_bp
from .mis_model import MisTracker
from .mis_form import MISTrackerForm, FileUploadForm

from .mis_helper_functions import upload_mis_file
from extensions import db
from set_view_permissions import admin_required


@mis_bp.route("/upload_previous_month/")
def upload_previous_month():
    """View function to upload previous month MIS tracker entries after scheduled monthly cron job"""

    # current_month refers to month that just ended
    current_month = date.today() - relativedelta(months=1)

    # prev_month is the month before current_month
    prev_month = current_month - relativedelta(months=1)

    current_month_string = current_month.strftime("%B-%Y")
    prev_month_string = prev_month.strftime("%B-%Y")

    stmt = db.select(
        MisTracker.txt_mis_type,
        db.literal(current_month_string),
        db.literal("AUTOUPLOAD"),
    ).where(MisTracker.txt_period == prev_month_string)

    insert_stmt = db.insert(MisTracker).from_select(
        [MisTracker.txt_mis_type, MisTracker.txt_period, MisTracker.created_by], stmt
    )
    db.session.execute(insert_stmt)

    db.session.commit()
    return "Success"


@mis_bp.route("/bulk_upload", methods=["POST", "GET"])
@login_required
@admin_required
def bulk_upload_mis_tracker():
    form = FileUploadForm()
    if form.validate_on_submit():
        df_mis_tracker = pd.read_csv(form.data["file_upload"])

        upload_mis_file(df_mis_tracker, db.engine, current_user.username)

        flash("MIS tracker has been uploaded successfully.")

    return render_template(
        "upload_mis_tracker.html", form=form, title="Bulk Upload MIS tracker entries"
    )


@mis_bp.route("/", methods=["GET"])
@login_required
def view_mis_tracker():
    list = db.session.scalars(
        db.select(MisTracker).order_by(
            MisTracker.created_on.desc(), MisTracker.id.asc()
        )
    )
    return render_template("view_mis_tracker.html", list=list)


@mis_bp.route("/edit/<int:mis_key>/", methods=["POST", "GET"])
@login_required
@admin_required
def edit_mis_entry(mis_key):
    mis_entry = db.get_or_404(MisTracker, mis_key)
    form = MISTrackerForm(obj=mis_entry)
    if form.validate_on_submit():
        username = current_user.username
        now = datetime.now()
        # Boolean field → (date_field, user_field)
        update_map = {
            "bool_mis_shared": ("date_mis_shared", "mis_shared_by"),
            "bool_brs_completed": ("date_brs_completed", "brs_completed_by"),
            "bool_jv_passed": ("date_jv_passed", "jv_passed_by"),
        }
        # ✅ Capture original values BEFORE populate_obj changes them
        original_values = {flag: getattr(mis_entry, flag) for flag in update_map.keys()}
        form.populate_obj(mis_entry)
        for flag, (date_attr, user_attr) in update_map.items():
            new_value = form[flag].data
            old_value = original_values[flag]

            if new_value != old_value:  # ✅ change detection
                if new_value:
                    setattr(mis_entry, date_attr, now)
                    setattr(mis_entry, user_attr, username)
                else:
                    setattr(mis_entry, date_attr, None)
                    setattr(mis_entry, user_attr, None)
        db.session.commit()
        return redirect(url_for("mis.view_mis_tracker"))
    return render_template("edit_mis_entry.html", form=form, mis_entry=mis_entry)


@mis_bp.route("/view/<int:mis_key>/")
@login_required
@admin_required
def view_mis_entry(mis_key):
    mis_entry = db.get_or_404(MisTracker, mis_key)
    return render_template(
        "view_mis_entry.html",
        mis_entry=mis_entry,
    )
