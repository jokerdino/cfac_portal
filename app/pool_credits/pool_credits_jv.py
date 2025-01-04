from datetime import datetime
from io import BytesIO

import pandas as pd
from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    url_for,
    send_file,
)
from flask_login import current_user, login_required

from sqlalchemy import (
    func,
    literal,
    create_engine,
)
from sqlalchemy.exc import IntegrityError

from extensions import db
from set_view_permissions import admin_required

from . import pool_credits_bp
from .pool_credits_form import JVUploadForm, PoolCreditsJVForm
from .pool_credits_model import PoolCreditsJournalVoucher, PoolCredits


@pool_credits_bp.route("/jv/")
@login_required
@admin_required
def jv_list():
    jv_list = db.session.scalars(db.select(PoolCreditsJournalVoucher))

    return render_template("jv_list.html", jv_list=jv_list)


@pool_credits_bp.route("/jv/add/", methods=["GET", "POST"])
@login_required
@admin_required
def jv_add():
    form = PoolCreditsJVForm()
    if form.validate_on_submit():
        jv = PoolCreditsJournalVoucher()
        form.populate_obj(jv)

        try:
            db.session.add(jv)
            db.session.commit()
            return redirect(url_for("pool_credits.jv_list"))
        except IntegrityError as e:
            db.session.rollback()
            flash("RO code already exists.")

    return render_template("jv_edit.html", form=form, title="Add new JV mapping")


@pool_credits_bp.route("/jv/edit/<jv_id>", methods=["GET", "POST"])
@login_required
@admin_required
def jv_edit(jv_id):
    jv = db.get_or_404(PoolCreditsJournalVoucher, jv_id)
    form = PoolCreditsJVForm(obj=jv)
    if form.validate_on_submit():
        form.populate_obj(jv)

        try:
            db.session.commit()
            return redirect(url_for("pool_credits.jv_list"))
        except IntegrityError as e:
            db.session.rollback()
            flash("RO code already exists.")
    return render_template("jv_edit.html", form=form, jv=jv, title="Edit JV mapping")


@pool_credits_bp.route("/jv/bulk_upload", methods=["GET", "POST"])
@login_required
@admin_required
def jv_bulk_upload():
    form = JVUploadForm()
    if form.validate_on_submit():
        jv_file = form.jv_file.data
        df_jv = pd.read_excel(
            jv_file,
            dtype={"str_regional_office_code": str},
        )
        df_jv["created_on"] = datetime.now()
        df_jv["created_by"] = current_user.username
        df_jv.to_sql(
            "pool_credits_journal_voucher",
            create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI")),
            if_exists="append",
            index=False,
        )

        return redirect(url_for("pool_credits.jv_list"))
    return render_template("jv_bulk_upload.html", form=form)


@pool_credits_bp.route("/download_jv/")
@login_required
@admin_required
def download_jv_confirmed_entries():
    query = (
        db.session.query(
            literal("000100").label("Office Location"),
            PoolCreditsJournalVoucher.gl_code.label("GL Code"),
            PoolCreditsJournalVoucher.sl_code.label("SL Code"),
            literal("CR").label("DR/CR"),
            func.sum(PoolCredits.credit).label("Amount"),
            PoolCredits.month_string.label("Month"),
            PoolCredits.str_regional_office_code,
        )
        .outerjoin(
            PoolCreditsJournalVoucher,
            PoolCreditsJournalVoucher.str_regional_office_code
            == PoolCredits.str_regional_office_code,
        )
        .filter(
            (PoolCredits.str_regional_office_code.is_not(None))
            & (PoolCredits.bool_jv_passed.is_(False))
        )
        .group_by(
            PoolCredits.month_string,
            PoolCredits.str_regional_office_code,
            PoolCreditsJournalVoucher.gl_code,
            PoolCreditsJournalVoucher.sl_code,
        )
    )
    START_DATE = datetime(2024, 10, 1)
    query = query.filter(PoolCredits.value_date >= START_DATE)

    engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
    conn = engine.connect()
    df_confirmed_entries = pd.read_sql(query.statement, conn)

    df_confirmed_entries["Remarks"] = (
        "HDFC Pool account - "
        + df_confirmed_entries["Month"]
        + " - "
        + df_confirmed_entries["str_regional_office_code"]
    )
    df_confirmed_entries_copy = df_confirmed_entries.copy()
    df_confirmed_entries_copy["DR/CR"] = "DR"
    df_confirmed_entries_copy["GL Code"] = 5131405950
    df_confirmed_entries_copy["SL Code"] = 0

    df_concat = pd.concat([df_confirmed_entries, df_confirmed_entries_copy])
    df_concat["Office Location"] = "000100"
    df_concat = df_concat[
        ["Office Location", "GL Code", "SL Code", "DR/CR", "Amount", "Remarks"]
    ]
    output = BytesIO()

    df_concat.to_excel(output, index=False)

    # Set the buffer position to the beginning
    output.seek(0)

    filename = f"pool_credits_jv_{datetime.now().strftime("%Y%m%d%H%M%S")}.xlsx"

    return send_file(output, as_attachment=True, download_name=filename)
