from datetime import datetime
from math import fabs
import zipfile

import pandas as pd
from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    abort,
    current_app,
    request,
    send_from_directory,
)
from flask_login import login_required, current_user

from wtforms.validators import DataRequired

from sqlalchemy import func, create_engine

from app.ho_ro_recon import ho_ro_recon_bp

from app.ho_ro_recon.ho_ro_recon_form import (
    ReconEntriesForm,
    RegionalOfficeAcceptForm,
    HeadOfficeAcceptForm,
    ReconSummaryForm,
    UploadFileForm,
    ConsolUploadForm,
    ReconUploadForm,
    ro_list,
)
from app.ho_ro_recon.ho_ro_recon_model import (
    ReconEntries,
    ReconSummary,
    ReconUpdateBalance,
)

from app.users.user_model import User


@ho_ro_recon_bp.route("/add", methods=["POST", "GET"])
@login_required
def add_ho_ro_recon():

    from extensions import db

    form = ReconEntriesForm()

    if form.str_department_inter_region.data == "RO":
        form.str_ro_code.validators = [DataRequired()]
    elif form.str_department_inter_region.data == "HO":
        form.str_department.validators = [DataRequired()]
    if form.str_ro_code.data == current_user.ro_code:
        flash("Selected RO code cannot be same as the RO code of the user.")
    elif form.validate_on_submit():
        str_period = form.str_period.data
        str_target_ro_code = (
            form.str_ro_code.data
            if form.str_department_inter_region.data == "RO"
            else None
        )
        str_department = (
            form.str_department.data
            if form.str_department_inter_region.data == "HO"
            else None
        )
        text_remarks = form.text_remarks.data
        str_dr_cr = form.str_debit_credit.data
        amount_recon = form.amount_recon.data
        #      print(str_dept)
        entry = ReconEntries(
            str_regional_office_code=current_user.ro_code,
            str_period=str_period,
            str_department=str_department or None,
            str_target_ro_code=str_target_ro_code or None,
            txt_remarks=text_remarks,
            str_debit_credit=str_dr_cr,
            str_head_office_status="Pending",
            amount_recon=amount_recon,
            created_by=current_user.username,
            date_created_date=datetime.now(),
        )
        db.session.add(entry)
        db.session.commit()
        #
        return redirect(url_for("ho_ro_recon.recon_home"))
    return render_template(
        "ho_ro_recon_add.html",
        form=form,
        edit=False,
    )


def check_for_status(recon):
    # update_status = True
    # if recon.str_head_office_status != "Pending":
    #     update_status = False
    # return update_status

    return True if recon.str_head_office_status == "Pending" else False


@ho_ro_recon_bp.route("/edit/<int:key>", methods=["POST", "GET"])
@login_required
def update_source_ro(key):
    from extensions import db

    recon = ReconEntries.query.get_or_404(key)
    if current_user.user_type == "ro_user":
        if not recon.str_regional_office_code == current_user.ro_code:
            abort(404)
    form = ReconEntriesForm()
    if form.str_department_inter_region.data == "RO":
        form.str_ro_code.validators = [DataRequired()]
    elif form.str_department_inter_region.data == "HO":
        form.str_department.validators = [DataRequired()]
    if not check_for_status(recon):
        flash("Cannot edit the entry as the status is no longer pending.")
    elif form.str_ro_code.data == current_user.ro_code:
        flash("Selected RO code cannot be same as the RO code of the user.")
    elif form.validate_on_submit():

        if form.delete_button.data:

            recon.str_head_office_status = "Deleted"
            recon.deleted_by = current_user.username
            recon.date_deleted_date = datetime.now()

        else:
            recon.str_period = form.str_period.data
            if form.str_department_inter_region.data == "HO":
                recon.str_department = form.str_department.data
                recon.str_target_ro_code = None
            elif form.str_department_inter_region.data == "RO":
                recon.str_target_ro_code = form.str_ro_code.data
                recon.str_department = None
            recon.amount_recon = form.amount_recon.data
            recon.txt_remarks = form.text_remarks.data
            recon.str_debit_credit = form.str_debit_credit.data
            recon.updated_by = current_user.username
            recon.date_updated_date = datetime.now()
        db.session.commit()
        return redirect(url_for("ho_ro_recon.recon_home"))

    form.str_period.data = recon.str_period
    if recon.str_department:
        form.str_department_inter_region.data = "HO"
        form.str_department.data = recon.str_department
    elif recon.str_target_ro_code:
        form.str_department_inter_region.data = "RO"
        form.str_ro_code.data = recon.str_target_ro_code
    form.amount_recon.data = recon.amount_recon
    form.text_remarks.data = recon.txt_remarks
    form.str_debit_credit.data = recon.str_debit_credit

    return render_template(
        "ho_ro_recon_add.html",
        form=form,
        edit=True,
        recon=recon,
        check_for_status=check_for_status,
    )


@ho_ro_recon_bp.route("/accept/<int:key>", methods=["POST", "GET"])
@login_required
def update_target_ro(key):
    recon = ReconEntries.query.get_or_404(key)
    form = RegionalOfficeAcceptForm()
    if not recon.str_target_ro_code == current_user.ro_code:
        abort(404)
    from extensions import db

    if not check_for_status(recon):
        flash("Cannot edit the entry as the status is no longer pending.")

    elif form.validate_on_submit():
        recon.str_head_office_status = form.str_accept.data
        recon.txt_head_office_remarks = f"{form.text_remarks.data}; {form.str_accept.data} by {current_user.ro_code}"
        recon.updated_by = current_user.username
        recon.date_updated_date = datetime.now()

        # create contra entry if accepted
        if form.str_accept.data == "Accepted":
            str_debit_credit = "DR" if recon.str_debit_credit == "CR" else "CR"
            recon = ReconEntries(
                str_regional_office_code=current_user.ro_code,
                str_period=recon.str_period,
                str_target_ro_code=recon.str_regional_office_code,
                str_debit_credit=str_debit_credit,
                txt_remarks=recon.txt_remarks,
                amount_recon=recon.amount_recon,
                str_head_office_status="Accepted",
                txt_head_office_remarks=f"Accepted original entry of {recon.str_regional_office_code} by {current_user.ro_code}",
                created_by=current_user.username,
                date_created_date=datetime.now(),
            )
            db.session.add(recon)
        db.session.commit()
        return redirect(url_for("ho_ro_recon.recon_home"))
    form.text_remarks.data = recon.txt_head_office_remarks
    form.str_accept.data = recon.str_head_office_status
    return render_template(
        "target_ro_accept.html",
        form=form,
        recon=recon,
        check_for_status=check_for_status,
    )


@ho_ro_recon_bp.route("/ho/<int:key>", methods=["POST", "GET"])
@login_required
def update_ho(key):
    if not current_user.user_type == "admin":
        abort(404)
    from extensions import db

    recon = ReconEntries.query.get_or_404(key)

    form = HeadOfficeAcceptForm()

    if current_user.username in ["bar44515", "hem27596", "jan27629", "ush25768"]:
        ho_staff = User.query.filter(User.user_type == "admin").order_by(User.username)
        form.str_assigned_to.choices = [
            person.username.upper()
            for person in ho_staff
            if "admin" not in person.username
        ]
    elif current_user.username not in ["bar44515", "hem27596", "jan27629", "ush25768"]:
        form.str_assigned_to.choices = [current_user.username.upper()]

    if form.validate_on_submit():

        recon.str_assigned_to = (
            form.str_assigned_to.data
            if form.str_assigned_to.data
            else recon.str_assigned_to
        )
        recon.str_head_office_status = form.str_head_office_status.data
        recon.txt_head_office_remarks = form.text_head_office_remarks.data or None
        recon.str_head_office_voucher = form.str_head_office_voucher_number.data or None
        recon.date_head_office_voucher = form.date_head_office_voucher.data or None

        recon.updated_by = current_user.username
        recon.date_updated_date = datetime.now()
        db.session.commit()
        return redirect(url_for("ho_ro_recon.recon_home"))

    form.str_assigned_to.data = recon.str_assigned_to
    form.str_head_office_status.data = recon.str_head_office_status
    form.text_head_office_remarks.data = recon.txt_head_office_remarks
    form.str_head_office_voucher_number.data = recon.str_head_office_voucher
    form.date_head_office_voucher.data = recon.date_head_office_voucher
    return render_template(
        "ho_accept.html", recon=recon, form=form, check_for_status=check_for_status
    )


@ho_ro_recon_bp.route("/", methods=["POST", "GET"])
@login_required
def recon_home():
    from extensions import db

    form = HeadOfficeAcceptForm()
    # initialize form
    if current_user.user_type == "admin":

        if current_user.username in ["bar44515", "hem27596", "jan27629", "ush25768"]:
            ho_staff = User.query.filter(User.user_type == "admin").order_by(
                User.username
            )
            form.str_assigned_to.choices = [
                person.username.upper()
                for person in ho_staff
                if "admin" not in person.username
            ]
        elif current_user.username not in [
            "bar44515",
            "hem27596",
            "jan27629",
            "ush25768",
        ]:
            form.str_assigned_to.choices = [current_user.username.upper()]

    query = ReconEntries.query.filter(
        ReconEntries.str_head_office_status != "Deleted"
    ).order_by(ReconEntries.id)
    if current_user.user_type == "ro_user":
        query = query.filter(
            ReconEntries.str_regional_office_code == current_user.ro_code
        )

    if form.validate_on_submit():

        list_recon_keys = request.form.getlist("recon_keys")
        updated_time = datetime.now()
        for key in list_recon_keys:
            recon_entry = ReconEntries.query.get_or_404(key)

            recon_entry.str_head_office_voucher = (
                form.str_head_office_voucher_number.data
                if form.str_head_office_voucher_number.data
                else recon_entry.str_head_office_voucher
            )

            # if recon entry is already assigned to someone, dont assign it in bulk update
            # if recon entry is not assigned to anyone, assign to self in bulk update
            if not recon_entry.str_assigned_to:
                recon_entry.str_assigned_to = (
                    form.str_assigned_to.data
                    if form.str_assigned_to.data
                    else recon_entry.str_assigned_to
                )
            recon_entry.str_head_office_status = (
                form.str_head_office_status.data
                if form.str_head_office_status.data
                else recon_entry.str_head_office_status
            )
            recon_entry.date_head_office_voucher = (
                form.date_head_office_voucher.data
                if form.date_head_office_voucher.data
                else recon_entry.date_head_office_voucher
            )
            recon_entry.updated_by = current_user.username
            recon_entry.date_updated_date = updated_time
            db.session.commit()
        return redirect(url_for("ho_ro_recon.recon_home"))

    return render_template(
        "ho_ro_recon_home.html",
        query=query,
        form=form,
    )


@ho_ro_recon_bp.route("/pending_voucher", methods=["POST", "GET"])
@login_required
def recon_pending_for_voucher():
    query = ReconEntries.query.filter(
        (ReconEntries.str_head_office_status == "Accepted")
        & (ReconEntries.str_head_office_voucher.is_(None))
    ).order_by(ReconEntries.id)
    if current_user.user_type == "ro_user":
        query = query.filter(ReconEntries.str_target_ro_code == current_user.ro_code)
    return render_template(
        "ho_ro_recon_home.html",
        query=query,
    )


@ho_ro_recon_bp.route("/pending", methods=["POST", "GET"])
@login_required
def recon_pending_at_ro():
    query = ReconEntries.query.filter(
        ReconEntries.str_head_office_status == "Pending"
    ).order_by(ReconEntries.id)
    if current_user.user_type == "ro_user":
        query = query.filter(ReconEntries.str_target_ro_code == current_user.ro_code)
    return render_template(
        "ho_ro_recon_home.html",
        query=query,
    )


@ho_ro_recon_bp.route("/summary/")
@login_required
def list_recon_summary():
    query = ReconSummary.query.filter(ReconSummary.str_period == "Jun-24").order_by(
        ReconSummary.id
    )
    if current_user.user_type == "ro_user":
        query = query.filter(
            ReconSummary.str_regional_office_code == current_user.ro_code
        )

    return render_template("ho_ro_recon_summary_list.html", query=query)


def calculate_amount(ro_code):

    query = (
        ReconEntries.query.with_entities(func.sum(ReconEntries.amount_recon))
        .filter(ReconEntries.str_regional_office_code == ro_code)
        .group_by(ReconEntries.str_head_office_status)
    )

    pending_amount = query.filter(ReconEntries.str_head_office_status == "Pending")
    pending_amount_dr = pending_amount.filter(
        ReconEntries.str_debit_credit == "DR"
    ).first() or [0]
    pending_amount_cr = pending_amount.filter(
        ReconEntries.str_debit_credit == "CR"
    ).first() or [0]

    not_passed = query.filter(
        (ReconEntries.str_head_office_status == "Accepted")
        & (ReconEntries.str_head_office_voucher.is_(None))
    )

    not_passed_dr = not_passed.filter(
        ReconEntries.str_debit_credit == "DR"
    ).first() or [0]
    not_passed_cr = not_passed.filter(
        ReconEntries.str_debit_credit == "CR"
    ).first() or [0]

    return (
        pending_amount_dr[0]
        - pending_amount_cr[0]
        + not_passed_dr[0]
        - not_passed_cr[0]
    )


@ho_ro_recon_bp.route("/summary/edit/<int:id>", methods=["POST", "GET"])
@login_required
def update_recon_summary(id):
    from extensions import db

    summary = ReconSummary.query.get_or_404(id)
    if current_user.user_type == "ro_user":
        if current_user.ro_code != summary.str_regional_office_code:
            abort(404)

    recon_entries = ReconEntries.query.filter(
        ReconEntries.str_regional_office_code == summary.str_regional_office_code
    ).order_by(ReconEntries.id)
    pending_entries = recon_entries.filter(
        ReconEntries.str_head_office_status == "Pending"
    )
    pending_entries_debit = pending_entries.filter(
        ReconEntries.str_debit_credit == "DR"
    )
    pending_entries_credit = pending_entries.filter(
        ReconEntries.str_debit_credit == "CR"
    )
    accepted_but_not_passed_entries = recon_entries.filter(
        (ReconEntries.str_head_office_status == "Accepted")
        & (ReconEntries.str_head_office_voucher.is_(None))
    )
    accepted_but_not_passed_entries_dr = accepted_but_not_passed_entries.filter(
        ReconEntries.str_debit_credit == "DR"
    )
    accepted_but_not_passed_entries_cr = accepted_but_not_passed_entries.filter(
        ReconEntries.str_debit_credit == "CR"
    )
    form = ReconSummaryForm()

    if request.method == "POST":
        if form.str_ro_balance_dr_cr.data == "CR":
            ro_balance = form.float_ro_balance.data or 0
        elif form.str_ro_balance_dr_cr.data == "DR":
            ro_balance = -(form.float_ro_balance.data) or 0
        if form.str_ho_balance_dr_cr.data == "DR":
            ho_balance = form.float_ho_balance.data or 0
        elif form.str_ho_balance_dr_cr.data == "CR":
            ho_balance = -(form.float_ho_balance.data) or 0

        if (
            fabs(
                int_diff := (
                    (ro_balance)
                    - calculate_amount(summary.str_regional_office_code)
                    - (ho_balance)
                )
            )
            > 0.001
        ):
            flash(f"Amount mismatch {int_diff}.")
        elif form.validate_on_submit():
            summary.input_ro_balance_dr_cr = form.str_ro_balance_dr_cr.data
            summary.input_float_ro_balance = form.float_ro_balance.data
            summary.input_ho_balance_dr_cr = form.str_ho_balance_dr_cr.data
            summary.input_float_ho_balance = form.float_ho_balance.data
            summary.updated_by = current_user.username
            summary.date_updated_date = datetime.now()

            db.session.commit()
            return redirect(url_for("ho_ro_recon.list_recon_summary"))

    form.str_ro_balance_dr_cr.data = summary.input_ro_balance_dr_cr
    form.float_ro_balance.data = summary.input_float_ro_balance or 0
    form.str_ho_balance_dr_cr.data = summary.input_ho_balance_dr_cr
    form.float_ho_balance.data = summary.input_float_ho_balance or 0

    return render_template(
        "recon_summary_edit.html",
        form=form,
        summary=summary,
        pending_dr=pending_entries_debit,
        pending_cr=pending_entries_credit,
        not_passed_dr=accepted_but_not_passed_entries_dr,
        not_passed_cr=accepted_but_not_passed_entries_cr,
    )


@ho_ro_recon_bp.route("/upload_summary_template", methods=["GET", "POST"])
@login_required
def upload_summary_template():

    form = UploadFileForm()

    if form.validate_on_submit():
        summary_template = form.data["file_upload"]
        df_summary_template = pd.read_excel(
            summary_template,
            dtype={
                "str_period": str,
                "str_regional_office_code": str,
            },
        )
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))

        df_summary_template["date_created_date"] = datetime.now()
        df_summary_template["created_by"] = current_user.username

        df_summary_template.to_sql(
            "recon_summary",
            engine,
            if_exists="append",
            index=False,
        )
        flash("HO RO recon summary has been uploaded successfully.")
    return render_template(
        "ho_ro_upload_file_template.html",
        form=form,
        title="Upload HO RO recon summary",
    )


@ho_ro_recon_bp.route("/upload_updated_summary_balance", methods=["GET", "POST"])
@login_required
def upload_new_ho_balance_summary():
    from extensions import db

    form = UploadFileForm()
    if form.validate_on_submit():
        db.session.query(ReconUpdateBalance).delete()
        db.session.commit()
        summary_template = form.data["file_upload"]
        df_summary_template = pd.read_excel(
            summary_template,
            dtype={
                "str_period": str,
                "str_regional_office_code": str,
            },
        )
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))

        #  df_summary_template["date_created_date"] = datetime.now()
        #  df_summary_template["created_by"] = current_user.username

        df_summary_template.to_sql(
            "recon_update_balance",
            engine,
            if_exists="append",
            index=False,
        )
        # flash("HO RO recon summary has been uploaded successfully.")
        str_period = (
            db.session.query(ReconUpdateBalance)
            .with_entities(ReconUpdateBalance.str_period)
            .distinct()
        )
        for regional_office in ro_list:
            recon_summary = ReconSummary.query.filter(
                (ReconSummary.str_regional_office_code == regional_office)
                & (ReconSummary.str_period == str_period.scalar_subquery())
            ).first()
            updated_recon_summary_balance = ReconUpdateBalance.query.filter(
                (ReconUpdateBalance.str_regional_office_code == regional_office)
                & (ReconUpdateBalance.str_period == str_period.scalar_subquery())
            ).first()
            if updated_recon_summary_balance:

                recon_summary.input_ro_balance_dr_cr = (
                    updated_recon_summary_balance.ro_dr_cr
                )
                recon_summary.input_float_ro_balance = (
                    updated_recon_summary_balance.ro_balance
                )

                recon_summary.input_ho_balance_dr_cr = (
                    updated_recon_summary_balance.ho_dr_cr
                )
                recon_summary.input_float_ho_balance = (
                    updated_recon_summary_balance.ho_balance
                )

                recon_summary.updated_by = current_user.username
                recon_summary.date_updated_date = datetime.now()
        db.session.commit()
        flash("Balances have been updated.")
    return render_template(
        "ho_ro_upload_file_template.html",
        form=form,
        title="Upload fresh HO balances",
    )


@ho_ro_recon_bp.context_processor
def recon_count():
    def recon_pending_count(status: str) -> int:
        count = ReconEntries.query.with_entities(func.count(ReconEntries.id))

        if status == "pending":
            count = count.filter(ReconEntries.str_head_office_status == "Pending")
        elif status == "voucher_pending":
            count = count.filter(
                (ReconEntries.str_head_office_status == "Accepted")
                & (ReconEntries.str_head_office_voucher.is_(None))
            )
        else:
            return 0

        if current_user.user_type == "ro_user":
            count = count.filter(
                ReconEntries.str_target_ro_code == current_user.ro_code
            )
        elif current_user.user_type != "admin":
            return 0

        return count.scalar()

    return dict(recon_pending_count=recon_pending_count)


@ho_ro_recon_bp.route("/upload_csv/", methods=["POST", "GET"])
def upload_csv_files():
    form = ReconUploadForm()
    if form.validate_on_submit():
        ro_csv = form.data["ro_csv_file"]
        ho_csv = form.data["ho_csv_file"]
        flag_file = form.data["flag_file"]
        df_ro = pd.read_csv(ro_csv)
        df_ro["Source"] = "RO"
        df_ho = pd.read_csv(ho_csv)
        df_ho["Source"] = "HO"
        df_flags = pd.read_excel(flag_file)
        consol_file, pivot_file = generate_consol_dataframe(df_ro, df_ho, df_flags)

        zip_file = compress_files([consol_file, pivot_file])
        return send_from_directory(
            directory="download_data/ho_ro_recon/",
            path=zip_file,
            download_name=zip_file,
            as_attachment=True,
        )

    return render_template("ho_ro_recon_upload_csv.html", form=form)


def compress_files(file_list):

    zip_file_name = f"zip_{datetime.now().strftime('%Y%m%d_%H%M_%S')}.zip"
    zipf = zipfile.ZipFile(
        f"download_data/ho_ro_recon/{zip_file_name}", "w", zipfile.ZIP_DEFLATED
    )

    for file in file_list:
        zipf.write(f"download_data/ho_ro_recon/{file}")
    zipf.close()
    return zip_file_name


def generate_consol_dataframe(df_ro, df_ho, df_flags):

    df_consol = pd.concat([df_ro, df_ho])
    df_consol = df_consol[
        ~df_consol["Description Of Accounting"].str.contains(
            "Opening Balance", na=False
        )
    ]

    df_consol["Credit Amount"] = (
        df_consol["Opeining Balance Credit"] + df_consol["Credit Amount"]
    )
    df_consol["Debit Amount"] = (
        df_consol["Opeining Balance Debit"] + df_consol["Debit Amount"]
    )
    df_consol["Voucher Date"] = pd.to_datetime(
        df_consol["Voucher Date"], format="mixed"
    )
    df_consol["Month"] = df_consol["Voucher Date"].dt.strftime("%m-%Y")

    df_consol["Net Credit"] = df_consol["Credit Amount"] - df_consol["Debit Amount"]
    df_consol = df_consol[
        [
            "Description Of Accounting",
            "Voucher Number",
            "Voucher Date",
            "Debit Amount",
            "Credit Amount",
            "Net Credit",
            "Source",
            "Month",
        ]
    ]

    reg_exp: list[str] = df_flags["PATTERN"].str.upper().unique().tolist()

    df_flags["HEAD"] = df_flags["HEAD"].str.upper().str.strip()
    df_flags["PATTERN"] = df_flags["PATTERN"].str.upper().str.strip()

    df_consol["PATTERN"] = (
        df_consol["Description Of Accounting"]
        .str.upper()
        .str.replace("_", " ")
        .apply(lambda x: "".join([part for part in reg_exp if part in str(x)]))
    )
    df_consol = df_consol.merge(df_flags, on="PATTERN", how="left")

    df_consol.loc[
        df_consol["Description Of Accounting"] == "Closing Balance", "HEAD"
    ] = "Closing Balance"
    df_consol["HEAD"] = df_consol["HEAD"].fillna("OTHERS")

    current_date_file = f"consol_{datetime.now().strftime('%Y%m%d_%H%M_%S')}.xlsx"
    with pd.ExcelWriter(
        f"download_data/ho_ro_recon/{current_date_file}", datetime_format="dd/mm/yyyy"
    ) as writer:
        df_consol.sort_values(
            ["Voucher Date", "Voucher Number"],
            ascending=[True, True],
        ).to_excel(writer, sheet_name="consolidated", index=False)
        worksheet_formatter(writer, "consolidated")
    pivot_file = prepare_pivot(df_consol)
    return current_date_file, pivot_file


def worksheet_formatter(writer, sheet_name):

    format_workbook = writer.book
    format_currency = format_workbook.add_format({"num_format": "##,##,#0.00"})

    format_worksheet = writer.sheets[sheet_name]

    if sheet_name == "pivot":
        format_worksheet.set_column("B:Z", 11, format_currency)
    elif sheet_name == "consolidated":
        format_worksheet.freeze_panes(1, 0)
        format_worksheet.autofilter("A1:J2")
    elif sheet_name == "recon":
        format_worksheet.set_column("B:B", 11, format_currency)

    format_worksheet.autofit()


def prepare_pivot(df_consol):

    df_consol_closing_balance = df_consol[df_consol["HEAD"] == "Closing Balance"]
    int_closing_balance_ro = df_consol_closing_balance[
        df_consol_closing_balance["Source"] == "RO"
    ]["Net Credit"].sum()
    int_closing_balance_ho = df_consol_closing_balance[
        df_consol_closing_balance["Source"] == "HO"
    ]["Net Credit"].sum()

    df_consol = df_consol[df_consol["HEAD"] != "Closing Balance"]
    df_pivot = df_consol.pivot_table(
        values="Net Credit",
        columns=["Month"],
        index=["HEAD"],
        aggfunc="sum",
        fill_value=0,
        margins=True,
        margins_name="Total",
        # add source if required to index
    )
    df_recon = pd.DataFrame(
        [
            {
                "Particulars": "Closing balance as per RO",
                "Net Credit": int_closing_balance_ro,
            }
        ]
    )
    df_recon_2 = pd.DataFrame(
        [
            {
                "Particulars": "Closing balance as per HO",
                "Net Credit": int_closing_balance_ho,
            }
        ]
    )

    df_pivot_flat = df_pivot.copy().reset_index()
    df_pivot_flat = df_pivot_flat[["HEAD", "Total"]]
    df_pivot_flat = df_pivot_flat[df_pivot_flat["HEAD"] != "Total"]
    df_pivot_flat.columns = ["Particulars", "Net Credit"]
    df_pivot_flat["Net Credit"] = df_pivot_flat["Net Credit"] * -1
    df_combined = pd.concat([df_recon, df_pivot_flat, df_recon_2], ignore_index=True)

    current_date_file = f"summary_{datetime.now().strftime('%Y%m%d_%H%M_%S')}.xlsx"
    with pd.ExcelWriter(f"download_data/ho_ro_recon/{current_date_file}") as writer:
        df_pivot.to_excel(writer, sheet_name="pivot")
        df_combined.to_excel(writer, sheet_name="recon", index=False)
        worksheet_formatter(writer, "pivot")
        worksheet_formatter(writer, "recon")
    return current_date_file


@ho_ro_recon_bp.route("/upload_consol/", methods=["POST", "GET"])
def upload_consol_file():
    form = ConsolUploadForm()
    if form.validate_on_submit():
        consol_file = form.data["consol_file"]
        df_consol = pd.read_excel(consol_file)
        pivot_file = prepare_pivot(df_consol)
        return send_from_directory(
            directory="download_data/ho_ro_recon/",
            path=pivot_file,
            download_name=pivot_file,
            as_attachment=True,
        )
    return render_template("ho_ro_recon_upload_consol.html", form=form)
