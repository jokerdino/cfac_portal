from dataclasses import asdict
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

import pandas as pd
from flask import redirect, render_template, url_for, flash, current_app

from flask_login import current_user, login_required

from sqlalchemy import create_engine

from app.mis_tracker import mis_bp
from app.mis_tracker.mis_model import MisTracker
from app.mis_tracker.mis_form import MISTrackerForm, FileUploadForm

from app.mis_tracker.mis_helper_functions import upload_mis_file


@mis_bp.route("/upload_previous_month")
def upload_previous_month():
    """View function to upload previous month MIS tracker entries after scheduled monthly cron job"""
    from extensions import db

    # current_month refers to month that just ended
    current_month = date.today() - relativedelta(months=1)

    # prev_month is the month before current_month
    prev_month = current_month - relativedelta(months=1)

    fresh_entries = []
    mis_entries = db.session.scalars(
        db.select(MisTracker).where(
            MisTracker.txt_period == prev_month.strftime("%B-%Y")
        )
    )
    for entry in mis_entries:

        new_entry = MisTracker(
            **asdict(entry),
            txt_period=current_month.strftime("%B-%Y"),
            created_by="AUTOUPLOAD"
        )

        fresh_entries.append(new_entry)

    db.session.add_all(fresh_entries)
    db.session.commit()
    return "Success"


@mis_bp.route("/bulk_upload", methods=["POST", "GET"])
@login_required
def bulk_upload_mis_tracker():
    form = FileUploadForm()
    if form.validate_on_submit():
        df_mis_tracker = pd.read_csv(form.data["file_upload"])
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
        upload_mis_file(df_mis_tracker, engine, current_user.username)
        # engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
        # df_mis_tracker["created_by"] = current_user.username
        # df_mis_tracker["created_on"] = datetime.now()
        # df_mis_tracker.to_sql("mis_tracker", engine, if_exists="append", index=False)
        flash("MIS tracker has been uploaded successfully.")

    return render_template(
        "upload_mis_tracker.html", form=form, title="Bulk Upload MIS tracker entries"
    )


@mis_bp.route("/", methods=["GET"])
@login_required
def view_mis_tracker():
    list = MisTracker.query.order_by(MisTracker.created_on.desc(), MisTracker.id.asc())
    return render_template("view_mis_tracker.html", list=list)


@mis_bp.route("/edit/<int:mis_key>", methods=["POST", "GET"])
@login_required
def edit_mis_entry(mis_key):
    form = MISTrackerForm()
    mis_entry = MisTracker.query.get_or_404(mis_key)
    from extensions import db

    if form.validate_on_submit():
        # mis shared status
        mis_entry.bool_mis_shared = form.data["bool_mis_shared"]

        mis_entry.date_mis_shared = (
            datetime.now() if form.data["bool_mis_shared"] else None
        )
        mis_entry.mis_shared_by = (
            current_user.username if form.data["bool_mis_shared"] else None
        )

        # brs completed status
        mis_entry.bool_brs_completed = form.data["bool_brs_completed"]
        mis_entry.date_brs_completed = (
            datetime.now() if form.data["bool_brs_completed"] else None
        )
        mis_entry.brs_completed_by = (
            current_user.username if form.data["bool_brs_completed"] else None
        )

        # jv passed status
        mis_entry.bool_jv_passed = form.data["bool_jv_passed"]
        mis_entry.date_jv_passed = (
            datetime.now() if form.data["bool_jv_passed"] else None
        )
        mis_entry.jv_passed_by = (
            current_user.username if form.data["bool_jv_passed"] else None
        )

        db.session.commit()
        return redirect(url_for("mis.view_mis_tracker"))
    form.bool_mis_shared.data = mis_entry.bool_mis_shared
    form.bool_brs_completed.data = mis_entry.bool_brs_completed
    form.bool_jv_passed.data = mis_entry.bool_jv_passed
    return render_template("edit_mis_entry.html", form=form, mis_entry=mis_entry)


@mis_bp.route("/view/<int:mis_key>")
@login_required
def view_mis_entry(mis_key):
    mis_entry = MisTracker.query.get_or_404(mis_key)
    return render_template(
        "view_mis_entry.html",
        mis_entry=mis_entry,  # humanize_datetime=humanize_datetime
    )
