import pandas as pd

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user
import jinja2
from sqlalchemy import create_engine
from werkzeug.utils import secure_filename

from app.brs import brs_bp
from app.brs.models import BRS

from app.brs.forms import BRSForm


@brs_bp.route("/home", methods=["POST", "GET"])
def brs_home_page():
    if current_user.user_type == "ro_user":
        brs_entries = BRS.query.filter(BRS.uiic_regional_code == current_user.ro_code)
    elif current_user.user_type == "oo_user":

        brs_entries = BRS.query.filter(BRS.uiic_office_code == current_user.oo_code)
    else:
        brs_entries = BRS.query.all()
    return render_template("brs_home.html", brs_entries=brs_entries, colour_check = colour_check)

#@jinja2.pass_eval_context()
#@brs_bp.app_template_filter()
def colour_check(brs_key):
    brs_entry = BRS.query.get_or_404(brs_key)

    bool_cash = True if brs_entry.cash_brs_file else False
 #   print(brs_key, bool_cash)
    bool_cheque = True if brs_entry.cheque_brs_file else False
    if brs_entry.pg_bank:
        bool_pg = True if brs_entry.pg_brs_file else False
    else:
        bool_pg = True
    if brs_entry.pos_bank:
        bool_pos = True if brs_entry.pos_brs_file else False
    else:
        bool_pos = True
    colour_code = all([bool_cash, bool_cheque, bool_pg, bool_pos])
    return colour_code
  #  if colour_code:
  #      return "YES"#
  #  else:
  #      return "NO"#colour_code



@brs_bp.route("/upload", methods=["POST", "GET"])
def bulk_upload_brs():
    if request.method == "POST":
        upload_file = request.files.get("file")
        df_user_upload = pd.read_csv(upload_file)
        engine = create_engine(
            "postgresql://barneedhar:barneedhar@localhost:5432/coinsurance"
        )
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
    generated_filename = (
        f"{office_code} - {period} - {brs_type} - {bank}.{file_extension}"
    )
    return generated_filename


@brs_bp.route("/upload_brs/<int:brs_key>", methods=["POST", "GET"])
def upload_brs(brs_key):
    from server import db

    brs_entry = BRS.query.get_or_404(brs_key)
    form = BRSForm()
    if form.validate_on_submit():
        if form.data["cash_brs_file"]:
            filename = generate_brs_filenames(
                brs_entry.uiic_office_code,
                brs_entry.month,
                "Cash",
                brs_entry.cash_bank,
                secure_filename(form.data["cash_brs_file"].filename),
            )
            form.cash_brs_file.data.save("brs/cash/" + filename)
            brs_entry.cash_brs_file = filename
        if form.data["cheque_brs_file"]:
            filename = generate_brs_filenames(
                brs_entry.uiic_office_code,
                brs_entry.month,
                "Cheque",
                brs_entry.cheque_bank,
                secure_filename(form.data["cheque_brs_file"].filename),
            )
            form.cheque_brs_file.data.save("brs/cheque/" + filename)
            brs_entry.cheque_brs_file = filename
        if form.data["pg_brs_file"]:
            filename = generate_brs_filenames(
                brs_entry.uiic_office_code,
                brs_entry.month,
                "PG",
                brs_entry.pg_bank,
                secure_filename(form.data["pg_brs_file"].filename),
            )
            form.pg_brs_file.data.save("brs/pg/" + filename)
            brs_entry.pg_brs_file = filename
        if form.data["pos_brs_file"]:
            filename = generate_brs_filenames(
                brs_entry.uiic_office_code,
                brs_entry.month,
                "POS",
                brs_entry.pos_bank,
                secure_filename(form.data["pos_brs_file"].filename),
            )
            form.pos_brs_file.data.save("brs/pos/" + filename)
            brs_entry.pos_brs_file = filename
        db.session.commit()
        return redirect(url_for("brs.brs_home_page"))
    return render_template("upload_brs.html", brs_entry=brs_entry, form=form)
