from datetime import datetime

import pandas as pd
from flask import current_app, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import create_engine

from app.pg_tieup import pg_tieup_bp
from app.pg_tieup.pg_tieup_form import PaymentGatewayTieupAddForm, UploadFileForm
from app.pg_tieup.pg_tieup_model import PaymentGatewayTieup
from set_view_permissions import admin_required


@pg_tieup_bp.route("/add/", methods=["POST", "GET"])
@login_required
@admin_required
def add_pg_tieup():
    from extensions import db

    form = PaymentGatewayTieupAddForm()
    if form.validate_on_submit():

        pg_tieup = PaymentGatewayTieup(
            created_by=current_user.username, date_created_date=datetime.now()
        )
        form.populate_obj(pg_tieup)

        db.session.add(pg_tieup)
        db.session.commit()

        return redirect(url_for("pg_tieup.view_pg_tieup", key=pg_tieup.id))
    return render_template("add_pg_tieup.html", form=form)


@pg_tieup_bp.route("/edit/<int:key>/", methods=["POST", "GET"])
@login_required
@admin_required
def edit_pg_tieup(key):
    from extensions import db

    pg_tieup = db.session.query(PaymentGatewayTieup).get_or_404(key)
    form = PaymentGatewayTieupAddForm(obj=pg_tieup)

    if form.validate_on_submit():

        form.populate_obj(pg_tieup)
        pg_tieup.date_updated_date = datetime.now()
        pg_tieup.updated_by = current_user.username

        db.session.commit()
        return redirect(url_for("pg_tieup.view_pg_tieup", key=pg_tieup.id))

    return render_template("add_pg_tieup.html", form=form)


@pg_tieup_bp.route("/view/<int:key>/")
@login_required
@admin_required
def view_pg_tieup(key):
    from extensions import db

    pg_tieup = db.session.query(PaymentGatewayTieup).get_or_404(key)
    return render_template("view_pg_tieup.html", pg_tieup=pg_tieup)


@pg_tieup_bp.route("/list/")
@login_required
@admin_required
def list_pg_tieup():
    from extensions import db

    column_names = db.session.query(PaymentGatewayTieup).statement.columns.keys()

    meta_columns = [
        "id",
        "current_status",
        "created_by",
        "updated_by",
        "deleted_by",
        "date_created_date",
        "date_updated_date",
        "date_deleted_date",
    ]
    column_names = [col for col in column_names if col not in meta_columns]
    query = db.session.query(PaymentGatewayTieup).order_by(PaymentGatewayTieup.id)
    return render_template("list_pg_tieup.html", query=query, column_names=column_names)


@pg_tieup_bp.route("/bulk_upload", methods=["POST", "GET"])
@login_required
@admin_required
def bulk_upload_pg_tieup():

    form = UploadFileForm()
    if form.validate_on_submit():
        df_cash_call = pd.read_excel(form.data["file_upload"])
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
        df_cash_call.columns = df_cash_call.columns.str.lower()

        df_cash_call["date_created_date"] = datetime.now()
        df_cash_call["created_by"] = current_user.username

        df_cash_call.to_sql(
            "payment_gateway_tieup",
            engine,
            if_exists="append",
            index=False,
        )
        flash("Coinsurance cash call details have been uploaded successfully.")

    return render_template("bulk_upload_pg_tieup.html", form=form)
