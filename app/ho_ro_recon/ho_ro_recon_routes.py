from datetime import datetime
from decimal import Decimal
from math import fabs
import zipfile

import pandas as pd
from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    request,
    send_from_directory,
)
from flask_login import login_required, current_user


from . import ho_ro_recon_bp

from .ho_ro_recon_form import (
    ReconEntriesForm,
    RegionalOfficeAcceptForm,
    HeadOfficeAcceptForm,
    ReconSummaryForm,
    UploadFileForm,
    ConsolUploadForm,
    ReconUploadForm,
)
from .ho_ro_recon_model import (
    ReconEntries,
    ReconSummary,
    ReconUpdateBalance,
)

from app.users.user_model import User
from extensions import db

from set_view_permissions import ro_user_only, admin_required


@ho_ro_recon_bp.route("/add", methods=["POST", "GET"])
@login_required
@ro_user_only
def add_ho_ro_recon():
    form = ReconEntriesForm()
    form.str_regional_office_code.data = current_user.ro_code

    if form.validate_on_submit():
        entry = ReconEntries()
        form.populate_obj(entry)
        db.session.add(entry)
        db.session.commit()

        return redirect(url_for("ho_ro_recon.recon_home"))
    return render_template(
        "ho_ro_recon_add.html",
        form=form,
    )


def check_for_status(recon):
    return True if recon.str_head_office_status == "Pending" else False


@ho_ro_recon_bp.route("/edit/<int:key>/", methods=["POST", "GET"])
@login_required
@ro_user_only
def update_source_ro(key):
    recon = db.get_or_404(ReconEntries, key)
    recon.require_access(current_user)

    form = ReconEntriesForm(obj=recon)

    if not check_for_status(recon):
        flash("Cannot edit the entry as the status is no longer pending.")

    if form.validate_on_submit():
        if form.delete_button.data:
            recon.str_head_office_status = "Deleted"
            recon.deleted_by = current_user.username
            recon.date_deleted_date = datetime.now()

        else:
            form.populate_obj(recon)
            if form.str_department_inter_region.data == "HO":
                recon.str_department = form.str_department.data
                recon.str_target_ro_code = None
            elif form.str_department_inter_region.data == "RO":
                recon.str_target_ro_code = form.str_target_ro_code.data
                recon.str_department = None

        db.session.commit()
        return redirect(url_for("ho_ro_recon.recon_home"))

    if recon.str_department:
        form.str_department_inter_region.data = "HO"

    elif recon.str_target_ro_code:
        form.str_department_inter_region.data = "RO"

    return render_template(
        "ho_ro_recon_add.html",
        form=form,
        recon=recon,
        check_for_status=check_for_status,
    )


@ho_ro_recon_bp.route("/accept/<int:key>/", methods=["POST", "GET"])
@login_required
@ro_user_only
def update_target_ro(key):
    recon = db.get_or_404(ReconEntries, key)
    recon.require_access(current_user)
    form = RegionalOfficeAcceptForm(obj=recon)

    if not check_for_status(recon):
        flash("Cannot edit the entry as the status is no longer pending.")

    elif form.validate_on_submit():
        recon.str_head_office_status = form.str_accept.data
        recon.txt_head_office_remarks = f"{form.text_remarks.data}; {form.str_accept.data} by {current_user.ro_code}"

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


@ho_ro_recon_bp.route("/ho/<int:key>/", methods=["POST", "GET"])
@login_required
@admin_required
def update_ho(key):
    recon = db.get_or_404(ReconEntries, key)

    form = HeadOfficeAcceptForm(obj=recon)
    if current_user.role and "chief_manager" in current_user.role:
        ho_staff = db.session.scalars(
            db.select(db.func.upper(User.username).label("username"))
            .where(User.user_type == "admin", db.not_(User.username.contains("admin")))
            .order_by(User.username)
        ).all()
        form.str_assigned_to.choices = ho_staff
    elif current_user.role and "chief_manager" not in current_user.role:
        form.str_assigned_to.choices = [current_user.username.upper()]

    if form.validate_on_submit():
        form.populate_obj(recon)

        db.session.commit()
        return redirect(url_for("ho_ro_recon.recon_home"))

    return render_template(
        "ho_accept.html", recon=recon, form=form, check_for_status=check_for_status
    )


@ho_ro_recon_bp.route("/", methods=["POST", "GET"])
@login_required
@ro_user_only
def recon_home():
    form = HeadOfficeAcceptForm()
    # initialize form
    if current_user.user_type == "admin":
        if current_user.role and "chief_manager" in current_user.role:
            ho_staff = db.session.scalars(
                db.select(db.func.upper(User.username).label("username"))
                .where(
                    User.user_type == "admin", db.not_(User.username.contains("admin"))
                )
                .order_by(User.username)
            ).all()
            form.str_assigned_to.choices = ho_staff
        elif current_user.role and "chief_manager" not in current_user.role:
            form.str_assigned_to.choices = [current_user.username.upper()]

    stmt = (
        db.select(ReconEntries)
        .where(ReconEntries.str_head_office_status != "Deleted")
        .order_by(ReconEntries.id)
    )
    if current_user.user_type == "ro_user":
        stmt = stmt.where(ReconEntries.str_regional_office_code == current_user.ro_code)
    query = db.session.scalars(stmt)
    if form.validate_on_submit():
        list_recon_keys = request.form.getlist("recon_keys")
        list_recon_keys = [int(key) for key in list_recon_keys]
        updated_time = datetime.now()

        update_stmt = (
            db.update(ReconEntries)
            .where(ReconEntries.id.in_(list_recon_keys))
            .values(
                str_head_office_voucher=form.str_head_office_voucher.data,
                str_assigned_to=form.str_assigned_to.data,
                str_head_office_status=form.str_head_office_status.data,
                date_head_office_voucher=form.date_head_office_voucher.data,
                updated_by=current_user.username,
                date_updated_date=updated_time,
            )
        )
        db.session.execute(update_stmt)
        db.session.commit()

        return redirect(url_for("ho_ro_recon.recon_home"))

    return render_template(
        "ho_ro_recon_home.html",
        query=query,
        form=form,
    )


@ho_ro_recon_bp.route("/pending_voucher", methods=["POST", "GET"])
@login_required
@ro_user_only
def recon_pending_for_voucher():
    stmt = (
        db.select(ReconEntries)
        .where(
            ReconEntries.str_head_office_status == "Accepted",
            ReconEntries.str_head_office_voucher.is_(None),
        )
        .order_by(ReconEntries.id)
    )
    if current_user.user_type == "ro_user":
        stmt = stmt.where(ReconEntries.str_target_ro_code == current_user.ro_code)
    query = db.session.scalars(stmt)
    return render_template(
        "ho_ro_recon_home.html",
        query=query,
    )


@ho_ro_recon_bp.route("/pending", methods=["POST", "GET"])
@login_required
@ro_user_only
def recon_pending_at_ro():
    stmt = (
        db.select(ReconEntries)
        .where(ReconEntries.str_head_office_status == "Pending")
        .order_by(ReconEntries.id)
    )
    if current_user.user_type == "ro_user":
        stmt = stmt.where(ReconEntries.str_target_ro_code == current_user.ro_code)
    query = db.session.scalars(stmt)
    return render_template(
        "ho_ro_recon_home.html",
        query=query,
    )


@ho_ro_recon_bp.route("/summary/")
@login_required
@ro_user_only
def list_recon_summary():
    stmt = (
        db.select(ReconSummary)
        .where(ReconSummary.str_period == "Jun-24")
        .order_by(ReconSummary.id)
    )
    if current_user.user_type == "ro_user":
        stmt = stmt.where(ReconSummary.str_regional_office_code == current_user.ro_code)
    query = db.session.scalars(stmt)
    return render_template("ho_ro_recon_summary_list.html", query=query)


def calculate_amount(ro_code: str) -> Decimal:
    # Define CASE expressions once
    is_pending = ReconEntries.str_head_office_status == "Pending"
    is_not_passed = (ReconEntries.str_head_office_status == "Accepted") & (
        ReconEntries.str_head_office_voucher.is_(None)
    )

    is_dr = ReconEntries.str_debit_credit == "DR"
    is_cr = ReconEntries.str_debit_credit == "CR"

    amount_col = db.func.coalesce(ReconEntries.amount_recon, 0)

    stmt = db.select(
        db.func.sum(db.case((is_pending & is_dr, amount_col), else_=0)).label(
            "pending_dr"
        ),
        db.func.sum(db.case((is_pending & is_cr, amount_col), else_=0)).label(
            "pending_cr"
        ),
        db.func.sum(db.case((is_not_passed & is_dr, amount_col), else_=0)).label(
            "not_passed_dr"
        ),
        db.func.sum(db.case((is_not_passed & is_cr, amount_col), else_=0)).label(
            "not_passed_cr"
        ),
    ).where(ReconEntries.str_regional_office_code == ro_code)

    row = db.session.execute(stmt).one()

    pending_dr, pending_cr, not_passed_dr, not_passed_cr = (
        r or Decimal(0) for r in row
    )

    return pending_dr - pending_cr + not_passed_dr - not_passed_cr


def pending_items(ro_code: str) -> tuple[list, list, list, list]:
    rows = db.session.scalars(
        db.select(ReconEntries)
        .where(ReconEntries.str_regional_office_code == ro_code)
        .order_by(ReconEntries.id)
    ).all()

    pending_dr = []
    pending_cr = []
    not_passed_dr = []
    not_passed_cr = []

    for row in rows:
        if row.str_head_office_status == "Pending":
            if row.str_debit_credit == "DR":
                pending_dr.append(row)
            else:
                pending_cr.append(row)
        elif (
            row.str_head_office_status == "Accepted"
            and row.str_head_office_voucher is None
        ):
            if row.str_debit_credit == "DR":
                not_passed_dr.append(row)
            else:
                not_passed_cr.append(row)

    return pending_dr, pending_cr, not_passed_dr, not_passed_cr


@ho_ro_recon_bp.route("/summary/edit/<int:id>/", methods=["POST", "GET"])
@login_required
@ro_user_only
def update_recon_summary(id):
    summary = db.get_or_404(ReconSummary, id)
    summary.require_access(current_user)

    pending_dr, pending_cr, not_passed_dr, not_passed_cr = pending_items(
        summary.str_regional_office_code
    )
    form = ReconSummaryForm(obj=summary)

    def signed(value, dr_cr):
        """Return value with correct sign: DR = +value, CR = -value."""
        if value is None:
            return 0
        return value if dr_cr == "DR" else -value

    if request.method == "POST":
        ro_balance = signed(
            form.input_float_ro_balance.data, form.input_ro_balance_dr_cr.data
        )
        ho_balance = signed(
            form.input_float_ho_balance.data, form.input_ho_balance_dr_cr.data
        )

        int_diff = (
            ro_balance + ho_balance + calculate_amount(summary.str_regional_office_code)
        )
        if fabs(int_diff) > 0.001:
            flash(f"Amount mismatch {int_diff}.")
        elif form.validate_on_submit():
            form.populate_obj(summary)

            db.session.commit()
            return redirect(url_for("ho_ro_recon.list_recon_summary"))

    return render_template(
        "recon_summary_edit.html",
        form=form,
        summary=summary,
        pending_dr=pending_dr,
        pending_cr=pending_cr,
        not_passed_dr=not_passed_dr,
        not_passed_cr=not_passed_cr,
    )


@ho_ro_recon_bp.route("/upload_summary_template", methods=["GET", "POST"])
@login_required
@admin_required
def upload_summary_template():
    form = UploadFileForm()

    if form.validate_on_submit():
        summary_template = form.data["file_upload"]
        df = pd.read_excel(
            summary_template,
            dtype={
                "str_period": str,
                "str_regional_office_code": str,
            },
        )
        db.session.execute(db.insert(ReconSummary), df.to_dict(orient="records"))
        db.session.commit()

        # df["date_created_date"] = datetime.now()
        # df["created_by"] = current_user.username

        # df.to_sql(
        #     "recon_summary",
        #     db.engine,
        #     if_exists="append",
        #     index=False,
        # )
        flash("HO RO recon summary has been uploaded successfully.")
    return render_template(
        "ho_ro_upload_file_template.html",
        form=form,
        title="Upload HO RO recon summary",
    )


@ho_ro_recon_bp.route("/upload_updated_summary_balance", methods=["GET", "POST"])
@login_required
@admin_required
def upload_new_ho_balance_summary():
    form = UploadFileForm()
    if form.validate_on_submit():
        delete_stmt = db.delete(ReconUpdateBalance)
        db.session.execute(delete_stmt)
        db.session.commit()
        summary_template = form.data["file_upload"]
        df = pd.read_excel(
            summary_template,
            dtype={
                "str_period": str,
                "str_regional_office_code": str,
            },
        )

        db.session.execute(db.insert(ReconUpdateBalance), df.to_dict(orient="records"))
        db.session.commit()

        # df.to_sql(
        #     "recon_update_balance",
        #     db.engine,
        #     if_exists="append",
        #     index=False,
        # )

        update_stmt = (
            db.update(ReconSummary)
            .where(
                db.and_(
                    ReconSummary.str_regional_office_code
                    == ReconUpdateBalance.str_regional_office_code,
                    ReconSummary.str_period == ReconUpdateBalance.str_period,
                )
            )
            .values(
                input_float_ro_balance=ReconUpdateBalance.ro_balance,
                input_ro_balance_dr_cr=ReconUpdateBalance.ro_dr_cr,
                input_float_ho_balance=ReconUpdateBalance.ho_balance,
                input_ho_balance_dr_cr=ReconUpdateBalance.ho_dr_cr,
            )
        )
        db.session.execute(update_stmt)
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
        count = db.select(db.func.count(ReconEntries.id))

        if status == "pending":
            count = count.where(ReconEntries.str_head_office_status == "Pending")
        elif status == "voucher_pending":
            count = count.where(
                (ReconEntries.str_head_office_status == "Accepted")
                & (ReconEntries.str_head_office_voucher.is_(None))
            )
        else:
            return 0

        if current_user.user_type == "ro_user":
            count = count.where(ReconEntries.str_target_ro_code == current_user.ro_code)
        elif current_user.user_type != "admin":
            return 0

        return db.session.scalar(count)

    return dict(recon_pending_count=recon_pending_count)


@ho_ro_recon_bp.route("/upload_csv/", methods=["POST", "GET"])
@login_required
@ro_user_only
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
@login_required
@ro_user_only
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
