from datetime import datetime
import calendar
import pandas as pd

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_weasyprint import HTML, render_pdf
from flask_login import current_user, login_required
from sqlalchemy import create_engine, func

from app.brs import brs_bp
from app.brs.models import BRS, BRS_month, Outstanding
from app.brs.forms import BRSForm, BRS_entry, DashboardForm


@brs_bp.route("/home", methods=["POST", "GET"])
@login_required
def brs_home_page():

    if current_user.user_type == "oo_user":
        brs_entries = BRS.query.filter(BRS.uiic_office_code == current_user.oo_code)
    elif current_user.user_type in ["admin","ro_user"]:
        return redirect(url_for("brs.brs_dashboard"))
    else:
        return "No permission"
    return render_template(
        "brs_home.html",
        brs_entries=brs_entries,
        colour_check=colour_check,
        percent_completed=percent_completed,
    )


@brs_bp.route("/<string:ro_code>/<string:month>", methods=["POST", "GET"])
@login_required
def brs_ro_wise(ro_code, month):
    if current_user.user_type == "admin" or (current_user.user_type =="ro_user" and current_user.ro_code == ro_code):
        brs_entries = BRS.query.filter(
            BRS.uiic_regional_code == ro_code, BRS.month == month
        )
    else:
        return "Not permitted"
    return render_template(
        "brs_home.html",
        brs_entries=brs_entries,
        colour_check=colour_check,
        percent_completed=percent_completed,
    )


@brs_bp.route("/dashboard", methods=["POST", "GET"])
@login_required
def brs_dashboard():

    form = DashboardForm()

    month_choices = BRS.query.with_entities(BRS.month).distinct()
    form.month.choices = ["View all"] + [x.month for x in month_choices]

    query = BRS.query.with_entities(
        BRS.uiic_regional_code,
        BRS.month,
        func.count(BRS.cash_bank),
        func.count(BRS.cash_brs_id),
        func.count(BRS.cheque_bank),
        func.count(BRS.cheque_brs_id),
        func.count(BRS.pos_bank),
        func.count(BRS.pos_brs_id),
        func.count(BRS.pg_bank),
        func.count(BRS.pg_brs_id),
        func.count(BRS.bbps_bank),
        func.count(BRS.bbps_brs_id),
    ).group_by(BRS.uiic_regional_code, BRS.month)

    if current_user.user_type == "ro_user":
        query = query.filter(BRS.uiic_regional_code == current_user.ro_code)

    if form.validate_on_submit():
        month = form.data["month"]
        if month != "View all":
            query = query.filter(BRS.month == month)
        return render_template("brs_dashboard.html", query=query, form=form)

    return render_template("brs_dashboard.html", query=query, form=form)


def colour_check(brs_key):
    brs_entry = BRS.query.get_or_404(brs_key)

    bool_cash = bool(brs_entry.cash_brs_id) if brs_entry.cash_bank else True
    bool_cheque = bool(brs_entry.cheque_brs_id) if brs_entry.cheque_bank else True
    bool_pg = bool(brs_entry.pg_brs_id) if brs_entry.pg_bank else True
    bool_pos = bool(brs_entry.pos_brs_id) if brs_entry.pos_bank else True
    bool_bbps = bool(brs_entry.bbps_brs_id) if brs_entry.bbps_bank else True

    colour_code = all([bool_cash, bool_cheque, bool_pg, bool_pos, bool_bbps])
    return colour_code


def percent_completed(brs_key):
    brs_entry = BRS.query.get_or_404(brs_key)

    denom = 0
    numerator = 0

    if brs_entry.cash_bank:
        denom += 1
        if brs_entry.cash_brs_id:
            numerator += 1

    if brs_entry.cheque_bank:
        denom += 1
        if brs_entry.cheque_brs_id:
            numerator += 1

    if brs_entry.pg_bank:
        denom += 1
        if brs_entry.pg_brs_id:
            numerator += 1

    if brs_entry.pos_bank:
        denom += 1
        if brs_entry.pos_brs_id:
            numerator += 1

    if brs_entry.bbps_bank:
        denom += 1
        if brs_entry.bbps_brs_id:
            numerator += 1
    try:
        return (numerator / denom) * 100
    except ZeroDivisionError:
        return 100


@brs_bp.route("/bulk_upload", methods=["POST", "GET"])
@login_required
def bulk_upload_brs():

    if request.method == "POST":
        upload_file = request.files.get("file")
        df_user_upload = pd.read_csv(upload_file)
        df_user_upload["timestamp"] = datetime.now()
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
        df_user_upload.to_sql("brs", engine, if_exists="append", index=False)
        flash("BRS records have been uploaded to database.")

    return render_template("brs_upload.html")


@brs_bp.route("/upload_brs/<int:brs_key>", methods=["POST", "GET"])
@login_required
def upload_brs(brs_key):
    from server import db

    brs_entry = BRS.query.get_or_404(brs_key)
    form = BRSForm()
    if form.validate_on_submit():

        if form.data["delete_cash_brs"]:
            current_id = brs_entry.cash_brs_id
            brs_entry.cash_brs_id = None
        if form.data["delete_cheque_brs"]:
            current_id = brs_entry.cheque_brs_id
            brs_entry.cheque_brs_id = None
        if form.data["delete_pos_brs"]:
            current_id = brs_entry.pos_brs_id
            brs_entry.pos_brs_id = None
        if form.data["delete_pg_brs"]:
            current_id = brs_entry.pg_brs_id
            brs_entry.pg_brs_id = None
        if form.data["delete_bbps_brs"]:
            current_id = brs_entry.bbps_brs_id
            brs_entry.bbps_brs_id = None
        brs_month = BRS_month.query.get_or_404(current_id)
        brs_month.status = "Deleted"
        db.session.commit()
        return redirect(url_for("brs.upload_brs", brs_key=brs_key))
    return render_template("upload_brs.html", brs_entry=brs_entry, form=form)


@brs_bp.route("/download_format")
@login_required
def download_format():
    return send_file("outstanding_cheques_upload_format.csv")


@brs_bp.route("/view/<int:brs_key>")
@login_required
def view_brs(brs_key):
    brs_entry = BRS_month.query.get_or_404(brs_key)
    brs_month = BRS.query.get_or_404(brs_entry.brs_id)
    brs_outstanding_entries = Outstanding.query.filter(
        Outstanding.brs_month_id == brs_key
    )
    return render_template(
        "view_brs_entry.html",
        brs_month=brs_month,
        brs_entry=brs_entry,
        outstanding=brs_outstanding_entries,
    )


@brs_bp.route("/pdf/<int:brs_key>")
@login_required
def view_brs_pdf(brs_key):
    brs_entry = BRS_month.query.get_or_404(brs_key)
    brs_month = BRS.query.get_or_404(brs_entry.brs_id)
    brs_outstanding_entries = Outstanding.query.filter(
        Outstanding.brs_month_id == brs_key
    )
    html = render_template(
        "view_brs_entry_pdf.html",
        brs_month=brs_month,
        brs_entry=brs_entry,
        outstanding=brs_outstanding_entries,
    )
    return render_pdf(HTML(string=html))


def get_prev_month_amount(requirement, brs_id):
    brs_entry = BRS.query.get_or_404(brs_id)

    datetime_object = datetime.strptime(brs_entry.month, "%B-%Y")
    if datetime_object.month - 1 > 1:
        month_number = datetime_object.month - 1
        year = datetime_object.year
    else:
        month_number = 12
        year = datetime_object.year - 1
    prev_month = f"{calendar.month_name[month_number]}-{year}"
    prev_brs_entry = (
        BRS.query.filter(BRS.uiic_office_code == brs_entry.uiic_office_code)
        .filter(BRS.month == prev_month)
        .first()
    )
    if prev_brs_entry:
        if requirement == "cash":
            brs_entry_id = prev_brs_entry.cash_brs_id
        elif requirement == "cheque":
            brs_entry_id = prev_brs_entry.cheque_brs_id
        elif requirement == "pg":
            brs_entry_id = prev_brs_entry.pg_brs_id
        elif requirement == "pos":
            brs_entry_id = prev_brs_entry.pos_brs_id
        elif requirement == "bbps":
            brs_entry_id = prev_brs_entry.bbps_brs_id
        if brs_entry_id:
            prev_brs = BRS_month.query.get_or_404(brs_entry_id)
            return (prev_brs.int_closing_balance, prev_brs.int_closing_on_hand)
        else:
            return (0, 0)
    else:
        return (0, 0)


@brs_bp.route("/<int:brs_id>/<string:requirement>/add_brs", methods=["POST", "GET"])
@login_required
def enter_brs(requirement, brs_id):
    brs_entry = BRS.query.get_or_404(brs_id)
    form = BRS_entry()
    from server import db

    if form.validate_on_submit():
        opening_balance = form.data["opening_balance"] or 0
        opening_on_hand = form.data["opening_on_hand"] or 0
        transactions = form.data["transactions"] or 0
        cancellations = form.data["cancellations"] or 0
        fund_transfer = form.data["fund_transfer"] or 0
        bank_charges = form.data["bank_charges"] or 0
        closing_on_hand = form.data["closing_on_hand"] or 0
        closing_balance = (
            opening_balance
            + opening_on_hand
            + transactions
            - cancellations
            - fund_transfer
            - bank_charges
            - closing_on_hand
        )

        if closing_balance < 0:
            flash("Closing balance cannot be less than 0.")
        else:
            brs = BRS_month(
                brs_id=brs_id,
                brs_type=requirement,
                int_opening_balance=opening_balance,
                int_opening_on_hand=opening_on_hand,
                int_transactions=transactions,
                int_cancellations=cancellations,
                int_fund_transfer=fund_transfer,
                int_bank_charges=bank_charges,
                int_closing_on_hand=closing_on_hand,
                int_closing_balance=closing_balance,
                timestamp=datetime.now(),
            )

            if requirement == "cheque" and closing_balance > 0:
                try:
                    df_outstanding_entries = pd.read_csv(
                        form.data["outstanding_entries"]
                    )
                    try:
                        sum_os_entries = df_outstanding_entries["cheque_amount"].sum()
                        if not sum_os_entries == closing_balance:
                            flash(
                                f"Closing balance {closing_balance} is not matching with sum of outstanding entries {sum_os_entries}."
                            )
                        else:
                            db.session.add(brs)
                            db.session.commit()
                            brs_entry.cheque_brs_id = brs.id

                            df_outstanding_entries["brs_month_id"] = brs.id
                            engine = create_engine(
                                current_app.config.get("SQLALCHEMY_DATABASE_URI")
                            )

                            df_outstanding_entries.to_sql(
                                "outstanding", engine, if_exists="append", index=False
                            )
                            db.session.commit()
                            return redirect(url_for("brs.upload_brs", brs_key=brs_id))
                    except Exception as e:

                        flash(f"Please upload in prescribed format.")
                except pd.errors.EmptyDataError:
                    flash("Please upload details of outstanding cheque entries.")
                except Exception as e:
                    flash(f"Please upload in prescribed format.")
            else:
                db.session.add(brs)
                db.session.commit()

                if requirement == "cash":
                    brs_entry.cash_brs_id = brs.id
                elif requirement == "cheque":
                    brs_entry.cheque_brs_id = brs.id
                elif requirement == "pg":
                    brs_entry.pg_brs_id = brs.id
                elif requirement == "pos":
                    brs_entry.pos_brs_id = brs.id
                elif requirement == "bbps":
                    brs_entry.bbps_brs_id = brs.id

                db.session.commit()

                return redirect(url_for("brs.upload_brs", brs_key=brs_id))

    form.opening_balance.data = get_prev_month_amount(requirement, brs_id)[0]
    form.opening_on_hand.data = get_prev_month_amount(requirement, brs_id)[1]

    return render_template(
        "brs_entry.html", form=form, brs_entry=brs_entry, requirement=requirement
    )


@brs_bp.route("/dashboard/view_all")
@login_required
def list_brs_entries():
    list_all_brs_entries = BRS_month.query.join(BRS, BRS.id == BRS_month.brs_id).all()
    return render_template("view_all_brs.html", brs_entries=list_all_brs_entries)
