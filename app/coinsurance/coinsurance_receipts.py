from io import BytesIO
from datetime import datetime, timedelta
import zipfile

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
        CoinsuranceReceipts.description.contains(
            CoinsuranceReceiptsJournalVoucher.pattern
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
            CoinsuranceReceipts.description.contains(
                CoinsuranceReceiptsJournalVoucher.pattern
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


@coinsurance_bp.route("/receipts/download_hub_jv/", methods=["POST", "GET"])
@login_required
@admin_required
def download_receipts_jv_hubs():
    form = UploadFileForm()
    if form.validate_on_submit():
        df = pd.read_csv(
            form.file_upload.data,
            usecols=["NUM_OFFICE_CD", "NUM_AMOUNT", "TXT_INSTRUMENT_NO"],
            dtype={
                "NUM_OFFICE_CD": str,
                "NUM_AMOUNT": int,
                "TXT_INSTRUMENT_NO": str,
            },
        )

        reference_number = df["TXT_INSTRUMENT_NO"].tolist()
        receipts_stmt = (
            db.select(
                CoinsuranceReceipts.transaction_code,
                CoinsuranceReceipts.value_date,
                CoinsuranceReceiptsJournalVoucher.company_name,
                CoinsuranceReceiptsJournalVoucher.gl_code,
                CoinsuranceReceipts.reference_no,
            )
            .join(
                CoinsuranceReceiptsJournalVoucher,
                CoinsuranceReceipts.description.contains(
                    CoinsuranceReceiptsJournalVoucher.pattern
                ),
            )
            .where(CoinsuranceReceipts.reference_no.in_(reference_number))
        )
        df_hub_receipts_jv = pd.read_sql_query(receipts_stmt, db.engine)
        df_hub_receipts_jv["value_date"] = pd.to_datetime(
            df_hub_receipts_jv["value_date"], format="%Y-%m-%d"
        ).dt.strftime("%d/%m/%y")
        df_hub_receipts_jv["Remarks"] = (
            df_hub_receipts_jv["transaction_code"]
            .str.cat(
                df_hub_receipts_jv[
                    [
                        "value_date",
                        "company_name",
                        "reference_no",
                    ]
                ],
                sep=" ",
            )
            .str.strip()
        )
        df_ho = df.merge(
            df_hub_receipts_jv[
                [
                    "reference_no",
                    "Remarks",
                    "gl_code",
                ]
            ],
            left_on="TXT_INSTRUMENT_NO",
            right_on="reference_no",
            how="left",
        )
        df_ho["Office Location"] = "000100"
        df_ho["Remarks"] = df_ho["Remarks"].fillna(df_ho["TXT_INSTRUMENT_NO"])
        df_ho["GL Code"] = df_ho["gl_code"]
        df_ho["SL Code"] = 0
        df_ho["DR/CR"] = "DR"
        df_ho["Amount"] = df_ho["NUM_AMOUNT"]
        df_ho = df_ho[
            [
                "Office Location",
                "GL Code",
                "SL Code",
                "DR/CR",
                "Amount",
                "Remarks",
                "NUM_OFFICE_CD",
            ]
        ]
        df_ho_cr = df_ho.copy()
        df_ho_cr["DR/CR"] = "CR"
        df_ho_cr["GL Code"] = 5121901000
        df_ho_cr["SL Code"] = df_ho_cr["NUM_OFFICE_CD"].astype(int)
        df_ho_final = pd.concat([df_ho, df_ho_cr])
        df_ho_final = df_ho_final[
            ["Office Location", "GL Code", "SL Code", "DR/CR", "Amount", "Remarks"]
        ]

        df_hub = df.merge(
            df_hub_receipts_jv[["reference_no", "Remarks"]],
            left_on="TXT_INSTRUMENT_NO",
            right_on="reference_no",
            how="left",
        )
        df_hub["Office Location"] = df_hub["NUM_OFFICE_CD"].str[1:]
        df_hub["GL Code"] = 9111310000
        df_hub["SL Code"] = 12402233
        df_hub["DR/CR"] = "CR"
        df_hub["Amount"] = df_hub["NUM_AMOUNT"]
        df_hub["Remarks"] = df_hub["Remarks"].fillna(df_hub["TXT_INSTRUMENT_NO"])
        df_hub = df_hub[
            [
                "Office Location",
                "GL Code",
                "SL Code",
                "DR/CR",
                "Amount",
                "Remarks",
            ]
        ]
        df_hub_dr = df_hub.copy()
        df_hub_dr["DR/CR"] = "DR"
        df_hub_dr["GL Code"] = 5121901000
        df_hub_dr["SL Code"] = 0
        df_hub_final = pd.concat([df_hub, df_hub_dr])
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            ho_bytes = BytesIO()
            with pd.ExcelWriter(ho_bytes, engine="xlsxwriter") as writer:
                df_ho_final.to_excel(writer, index=False)
            ho_bytes.seek(0)
            zipf.writestr("HO.xlsx", ho_bytes.read())

            # Write one Excel per Office Location
            for office in df_hub_final["Office Location"].unique():
                df_office = df_hub_final[df_hub_final["Office Location"] == office]
                excel_bytes = BytesIO()
                with pd.ExcelWriter(excel_bytes, engine="xlsxwriter") as writer:
                    df_office.to_excel(writer, index=False)
                excel_bytes.seek(0)
                zipf.writestr(f"{office}.xlsx", excel_bytes.read())

        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="hub_receipts.zip",
        )

    return render_template(
        "coinsurance_upload_file_template.html", form=form, title="Upload file"
    )
