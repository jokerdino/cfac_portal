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
#    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import create_engine, func
#from werkzeug.utils import secure_filename

from app.brs import brs_bp
from app.brs.models import BRS, BRS_month, Outstanding
from app.brs.forms import BRSForm, BRS_entry


@brs_bp.route("/home", methods=["POST", "GET"])
@login_required
def brs_home_page():
    if current_user.user_type == "ro_user":
        brs_entries = BRS.query.filter(BRS.uiic_regional_code == current_user.ro_code)
    elif current_user.user_type == "oo_user":

        brs_entries = BRS.query.filter(BRS.uiic_office_code == current_user.oo_code)
    else:
        brs_entries = BRS.query.all()
    return render_template(
        "brs_home.html",
        brs_entries=brs_entries,
        colour_check=colour_check,
        percent_completed=percent_completed,
    )

@brs_bp.route("/dashboard", methods=["POST", "GET"])
def brs_home_admin():

    query = BRS.query.with_entities(BRS.uiic_regional_code, BRS.month, func.count(BRS.cash_bank), func.count(BRS.cash_brs_id),
            func.count(BRS.cheque_bank), func.count(BRS.cheque_brs_id), func.count(BRS.pos_bank), func.count(BRS.pos_brs_id), func.count(BRS.pg_bank), func.count(BRS.pg_brs_id)).group_by(BRS.uiic_regional_code, BRS.month).all()

    return render_template("brs_dashboard.html", query=query)

def colour_check(brs_key):
    brs_entry = BRS.query.get_or_404(brs_key)

    bool_cash = bool(brs_entry.cash_brs_id) if brs_entry.cash_bank else True
    bool_cheque = bool(brs_entry.cheque_brs_id) if brs_entry.cheque_bank else True
    bool_pg = bool(brs_entry.pg_brs_id) if brs_entry.pg_bank else True
    bool_pos = bool(brs_entry.pos_brs_id) if brs_entry.pos_bank else True
   # if brs_entry.cash_bank:
    #    bool_cash = bool(brs_entry.cash_brs_id) #True if brs_entry.cash_brs_id else False
        #bool_cash = True if brs_entry.cash_brs_id else False
    #else:
     #   bool_cash = True
   # if brs_entry.cheque_bank:
   #     bool_cheque = bool(brs_entry.cheque_brs_id) #True if brs_entry.cheque_brs_id else False
   # else:
   #     bool_cheque = True
   # if brs_entry.pg_bank:
   #     bool_pg = bool(brs_entry.pg_brs_id) #True if brs_entry.pg_brs_id else False
   # else:
   #     bool_pg = True
   # if brs_entry.pos_bank:
   #     bool_pos = bool(brs_entry.pos_brs_id) #True if brs_entry.pos_brs_id else False
   # else:
   #     bool_pos = True
    colour_code = all([bool_cash, bool_cheque, bool_pg, bool_pos])
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
    try:
        return (numerator / denom) * 100
    except ZeroDivisionError: # as e:
        return 100

@brs_bp.route("/upload", methods=["POST", "GET"])
def bulk_upload_brs():

    #from config import Config

    if request.method == "POST":
        upload_file = request.files.get("file")
        df_user_upload = pd.read_csv(upload_file)
        df_user_upload["timestamp"] = datetime.now()
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
        df_user_upload.to_sql("brs", engine, if_exists="append", index=False)
        flash("BRS records have been uploaded to database.")
    # except IntegrityError:
    #    flash("Upload unique oo_code only.")
    #        convert_input(upload_file)
    # flash("GST invoice data has been received. Processing the input file..")
    # await upload_details(upload_file)

    return render_template("brs_upload.html")


def generate_brs_filenames(office_code, period, brs_type, bank, filename):
    file_extension = filename.rsplit(".", 1)[1]
    generated_filename = f"{office_code} - {period} - {brs_type} - {bank} - {datetime.now()}.{file_extension}"
    return generated_filename


@brs_bp.route("/upload_brs/<int:brs_key>", methods=["POST", "GET"])
def upload_brs(brs_key):
    from server import db

    brs_entry = BRS.query.get_or_404(brs_key)
    form = BRSForm()
    if form.validate_on_submit():
        #        if form.data["cash_brs_file"]:
        #            filename = generate_brs_filenames(
        #                brs_entry.uiic_office_code,
        #                brs_entry.month,
        #                "Cash",
        #                brs_entry.cash_bank,
        #                secure_filename(form.data["cash_brs_file"].filename),
        #            )
        #            form.cash_brs_file.data.save("brs/cash/" + filename)
        #            brs_entry.cash_brs_file = filename
        #        if form.data["cheque_brs_file"]:
        #            filename = generate_brs_filenames(
        #                brs_entry.uiic_office_code,
        #                brs_entry.month,
        #                "Cheque",
        #                brs_entry.cheque_bank,
        #                secure_filename(form.data["cheque_brs_file"].filename),
        #            )
        #            form.cheque_brs_file.data.save("brs/cheque/" + filename)
        #            brs_entry.cheque_brs_file = filename
        #        if form.data["pg_brs_file"]:
        #            filename = generate_brs_filenames(
        #                brs_entry.uiic_office_code,
        #                brs_entry.month,
        #                "PG",
        #                brs_entry.pg_bank,
        #                secure_filename(form.data["pg_brs_file"].filename),
        #            )
        #            form.pg_brs_file.data.save("brs/pg/" + filename)
        #            brs_entry.pg_brs_file = filename
        #        if form.data["pos_brs_file"]:
        #            filename = generate_brs_filenames(
        #                brs_entry.uiic_office_code,
        #                brs_entry.month,
        #                "POS",
        #                brs_entry.pos_bank,
        #                secure_filename(form.data["pos_brs_file"].filename),
        #            )
        #            form.pos_brs_file.data.save("brs/pos/" + filename)
        #            brs_entry.pos_brs_file = filename
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
        brs_month = BRS_month.query.get_or_404(current_id)
        brs_month.status = "Deleted"
        db.session.commit()
        return redirect(url_for("brs.upload_brs", brs_key=brs_key))#brs_home_page"))
    return render_template("upload_brs.html", brs_entry=brs_entry, form=form)


#@brs_bp.route("/<string:requirement>/<int:brs_id>", methods=["POST", "GET"])
#def download_document(requirement, brs_id):
#    brs_entry = BRS.query.get_or_404(brs_id)
#
#    if requirement == "cash":
#        #   file_extension = brs_entry.cash_brs_file.rsplit(".", 1)[1]
#        path = brs_entry.cash_brs_file
#    elif requirement == "cheque":
#        #  file_extension = brs_entry.statement.rsplit(".", 1)[1]
#        path = brs_entry.cheque_brs_file
#    elif requirement == "pg":
#        # file_extension = brs_entry.ri_confirmation.rsplit(".", 1)[1]
#        path = brs_entry.pg_brs_file
#    elif requirement == "pos":
#        path = brs_entry.pos_brs_file
#    else:
#        return "No such requirement"
#
#    return send_from_directory(
#        directory=f"brs/{requirement}/",
#        path=path,
#        as_attachment=True,
#    )


@brs_bp.route("/download_format")
def download_format():
    return send_file(
            "outstanding_cheques_upload_format.csv"
            #path=path,
            )

@brs_bp.route("/view/<int:brs_key>")
def view_brs(brs_key):
    brs_entry = BRS_month.query.get_or_404(brs_key)
    brs_month = BRS.query.get_or_404(brs_entry.brs_id)
    brs_outstanding_entries = Outstanding.query.filter(Outstanding.brs_month_id == brs_key)
    #total = brs_outstanding_entries
    return render_template(
        "view_brs_entry.html", brs_month=brs_month, brs_entry=brs_entry, outstanding = brs_outstanding_entries
    )


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
        if brs_entry_id:
            prev_brs = BRS_month.query.get_or_404(brs_entry_id)
            return (prev_brs.int_closing_balance, prev_brs.int_closing_on_hand)
        else:
            return (0, 0)
    else:
        return (0, 0)


@brs_bp.route("/<int:brs_id>/<string:requirement>/add_brs", methods=["POST", "GET"])
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
                    df_outstanding_entries = pd.read_csv(form.data['outstanding_entries'])
                    try:
                        sum_os_entries = df_outstanding_entries['cheque_amount'].sum()
                        if not sum_os_entries == closing_balance:
                            flash(f"Closing balance {closing_balance} is not matching with sum of outstanding entries {sum_os_entries}.")
                        else:
                            db.session.add(brs)
                            db.session.commit()
                            brs_entry.cheque_brs_id = brs.id

                            df_outstanding_entries['brs_month_id'] = brs.id
                            engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))

                            df_outstanding_entries.to_sql("outstanding", engine, if_exists="append", index=False)
                            db.session.commit()
                            return redirect(url_for("brs.upload_brs", brs_key=brs_id))
                   # else:
                    except Exception as e:

                        flash(f"Please upload in prescribed format.")
                except pd.errors.EmptyDataError:
                    flash("Please upload details of outstanding cheque entries.")
                except Exception as e: #KeyError:
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

                db.session.commit()

                return redirect(url_for("brs.upload_brs", brs_key=brs_id))

    form.opening_balance.data = get_prev_month_amount(requirement, brs_id)[0]
    form.opening_on_hand.data = get_prev_month_amount(requirement, brs_id)[1]

    return render_template(
        "brs_entry.html", form=form, brs_entry=brs_entry, requirement=requirement
    )


@brs_bp.route("/view_all")
def list_brs_entries():
    list_all_brs_entries = BRS_month.query.join(BRS, BRS.id == BRS_month.brs_id).all()
    return render_template("view_all_brs.html", brs_entries=list_all_brs_entries)