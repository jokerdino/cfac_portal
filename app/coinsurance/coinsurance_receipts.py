from io import BytesIO
from datetime import datetime, timedelta

import pandas as pd

from flask import (
    flash,
    redirect,
    request,
    render_template,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import literal, insert
from set_view_permissions import admin_required

from . import coinsurance_bp
from .coinsurance_form import (
    UploadFileForm,
    FilterMonthForm,
    CoinsuranceReceiptAddForm,
    CoinsuranceReceiptEditForm,
)
from .coinsurance_model_forms import ReceiptForm
from .coinsurance_model import (
    CoinsuranceReceipts,
    CoinsuranceReceiptsJournalVoucher,
    Settlement,
)


from extensions import db


@coinsurance_bp.route("/receipts/jv/bulk_upload/", methods=["GET", "POST"])
@login_required
@admin_required
def jv_bulk_upload():
    form = UploadFileForm()

    if form.validate_on_submit():
        jv_file = form.file_upload.data
        df_jv = pd.read_excel(
            jv_file,
        )
        df_jv["created_on"] = datetime.now()
        df_jv["created_by"] = current_user.username

        df_jv.to_sql(
            "coinsurance_receipts_journal_voucher",
            db.engine,
            if_exists="append",
            index=False,
        )
        flash("Uploaded JV file.")

    return render_template(
        "coinsurance_upload_file_template.html",
        form=form,
        title="Upload coinsurance receipts JV pattern",
    )


@coinsurance_bp.route("/receipts/jv/download/", methods=["POST", "GET"])
@login_required
@admin_required
def coinsurance_receipts_jv_download_monthly():
    # START_DATE = datetime(2024, 10, 1)
    receipts_jvs = db.session.query(
        CoinsuranceReceipts, CoinsuranceReceiptsJournalVoucher
    ).join(
        CoinsuranceReceiptsJournalVoucher,
        CoinsuranceReceipts.description.like(
            "%" + CoinsuranceReceiptsJournalVoucher.pattern + "%"
        ),
    )
    filter_month = receipts_jvs.with_entities(CoinsuranceReceipts.period).distinct()

    form = FilterMonthForm()
    list_period = [datetime.strptime(item[0], "%b-%y") for item in filter_month]
    list_period.sort(reverse=True)
    form.period.choices = [month.strftime("%b-%y") for month in list_period]

    if form.validate_on_submit():
        entries = receipts_jvs.filter(CoinsuranceReceipts.period == form.period.data)
        df_receipts = pd.read_sql(entries.statement, db.engine)
        output = BytesIO()
        df_receipts_concat = prepare_coinsurance_receipts_jv(df_receipts)

        df_receipts_concat.to_excel(output, index=False)

        # Set the buffer position to the beginning
        output.seek(0)

        filename = f"coinsurance_receipts_jv_{form.period.data}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"

        return send_file(output, as_attachment=True, download_name=filename)
    return render_template("coinsurance_receipts_download_jv_monthly.html", form=form)


def prepare_coinsurance_receipts_jv(df) -> pd.DataFrame:
    df_receipts = df[
        [
            "gl_code",
            "value_date",
            "company_name_1",
            "credit",
            "transaction_code",
            "reference_no",
        ]
    ].copy()
    df_receipts["value_date"] = pd.to_datetime(
        df_receipts["value_date"], format="%Y-%m-%d"
    ).dt.strftime("%d/%m/%y")
    df_receipts["Remarks"] = df_receipts["transaction_code"].str.cat(
        df_receipts[["value_date", "company_name_1", "reference_no"]], sep=" "
    )
    df_receipts.rename(columns={"gl_code": "GL Code", "credit": "Amount"}, inplace=True)
    df_receipts["Office Location"] = "000100"
    df_receipts["SL Code"] = 0
    df_receipts["DR/CR"] = "CR"
    df_receipts = df_receipts[
        ["Office Location", "GL Code", "SL Code", "DR/CR", "Amount", "Remarks"]
    ]

    df_receipts_copy = df_receipts.copy()
    df_receipts_copy["DR/CR"] = "DR"
    df_receipts_copy["GL Code"] = 5121910000
    df_receipts_concat = pd.concat([df_receipts, df_receipts_copy])
    return df_receipts_concat


@coinsurance_bp.route("/receipts/add/", methods=["POST", "GET"])
@login_required
@admin_required
def add_coinsurance_receipts():
    form = CoinsuranceReceiptAddForm()
    if form.validate_on_submit():
        receipt = CoinsuranceReceipts(status="Pending")
        form.populate_obj(receipt)
        db.session.add(receipt)
        db.session.commit()
        return redirect(url_for("coinsurance.list_coinsurance_receipts"))
    return render_template(
        "coinsurance_receipts_add.html",
        form=form,
    )


@coinsurance_bp.route("/receipts/model_add/", methods=["POST", "GET"])
@login_required
@admin_required
def add_coinsurance_receipts_model_form():
    """Add new pending coinsurance receipts through model form"""

    receipt = CoinsuranceReceipts(status="Pending")

    if request.method == "POST":
        form = ReceiptForm(request.form, obj=receipt)
        if form.validate():
            form.populate_obj(receipt)
            db.session.add(receipt)
            db.session.commit()
            return redirect(url_for("coinsurance.list_coinsurance_receipts"))
    else:
        form = ReceiptForm()

    return render_template(
        "coinsurance_receipts_add.html",
        form=form,
    )


@coinsurance_bp.route("/receipts/edit/<int:id>/", methods=["POST", "GET"])
@login_required
@admin_required
def edit_coinsurance_receipts(id):
    receipt = db.get_or_404(CoinsuranceReceipts, id)
    form = CoinsuranceReceiptEditForm(obj=receipt)

    if form.validate_on_submit():
        form.populate_obj(receipt)
        db.session.commit()
        return redirect(url_for("coinsurance.list_coinsurance_receipts"))
    return render_template(
        "coinsurance_receipts_edit_macro.html", form=form, receipt=receipt
    )


@coinsurance_bp.route("/receipts/")
@login_required
@admin_required
def list_coinsurance_receipts():
    receipts = db.session.scalars(db.select(CoinsuranceReceipts))
    pending_receipts = db.session.scalars(
        db.select(CoinsuranceReceipts).filter(CoinsuranceReceipts.status == "Pending")
    )
    return render_template(
        "coinsurance_receipts_list.html",
        receipts=receipts,
        pending_receipts=pending_receipts,
    )


@coinsurance_bp.route("/fetch_settlements/")
def fetch_settlements():
    current_time = datetime.now()

    prev_time = current_time - timedelta(hours=1)

    stmt = (
        db.select(
            CoinsuranceReceiptsJournalVoucher.company_name.label("name_of_company"),
            CoinsuranceReceipts.value_date.label("date_of_settlement"),
            CoinsuranceReceipts.credit.label("settled_amount"),
            CoinsuranceReceipts.reference_no.label("utr_number"),
            CoinsuranceReceipts.transaction_code.label("notes"),
            literal("Received").label("type_of_transaction"),
            literal("API").label("created_by"),
        )
        .join(
            CoinsuranceReceiptsJournalVoucher,
            CoinsuranceReceipts.description.like(
                "%" + CoinsuranceReceiptsJournalVoucher.pattern + "%"
            ),
        )
        .where(CoinsuranceReceipts.created_on > prev_time)
    )

    insert_stmt = insert(Settlement).from_select(
        [
            Settlement.name_of_company,
            Settlement.date_of_settlement,
            Settlement.settled_amount,
            Settlement.utr_number,
            Settlement.notes,
            Settlement.type_of_transaction,
            Settlement.created_by,
        ],
        stmt,
    )
    db.session.execute(insert_stmt)
    db.session.commit()

    return "Success"
