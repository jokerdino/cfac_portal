import re

from datetime import datetime, timedelta
from dataclasses import asdict

import requests
import pandas as pd
import numpy as np

from sqlalchemy import func, distinct, select, create_engine, case, String, cast

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from set_view_permissions import admin_required

from app.coinsurance import coinsurance_bp
from app.coinsurance.coinsurance_form import (
    CoinsuranceForm,
    SettlementForm,
    SettlementUTRForm,
    CoinsuranceBalanceQueryForm,
    CoinsurerSelectForm,
    CoinsuranceCashCallForm,
    UploadFileForm,
    QueryForm,
    CoinsuranceBalanceForm,
    CoinsuranceBankMandateForm,
    CoinsuranceReceiptEditForm,
    CoinsuranceReceiptAddForm,
    DeleteCoinsuranceBalanceEntries,
)
from app.coinsurance.coinsurance_model import (
    Coinsurance,
    Coinsurance_log,
    Remarks,
    Settlement,
    CoinsuranceBalances,
    CoinsuranceCashCall,
    CoinsuranceBankMandate,
    CoinsuranceReceipts,
)

from .coinsurance_model_forms import ReceiptForm

from app.funds.funds_model import FundBankStatement

from server import indian_number_format

ro_list = [
    "010000",
    "020000",
    "030000",
    "040000",
    "050000",
    "060000",
    "070000",
    "080000",
    "090000",
    "100000",
    "110000",
    "120000",
    "130000",
    "140000",
    "150000",
    "160000",
    "170000",
    "180000",
    "190000",
    "200000",
    "210000",
    "220000",
    "230000",
    "240000",
    "250000",
    "260000",
    "270000",
    "280000",
    "290000",
    "300000",
    "500100",
    "500200",
    "500300",
    "500400",
    "500500",
    "500700",
    "020051",
    "030051",
    "040051",
    "050051",
    "000100",
]


@coinsurance_bp.route("/")
@login_required
def home_page():
    from server import db

    if current_user.user_type == "ro_user":
        query = (
            Coinsurance.query.filter(
                Coinsurance.uiic_regional_code == current_user.ro_code
            )
            .with_entities(
                Coinsurance.current_status, func.count(Coinsurance.current_status)
            )
            .group_by(Coinsurance.current_status)
            .order_by(Coinsurance.current_status)
            .all()
        )
    elif current_user.user_type == "oo_user":
        query = (
            Coinsurance.query.filter(
                (Coinsurance.uiic_office_code == current_user.oo_code)
                & (Coinsurance.uiic_regional_code == current_user.ro_code)
            )
            .with_entities(
                Coinsurance.current_status, func.count(Coinsurance.current_status)
            )
            .group_by(Coinsurance.current_status)
            .order_by(Coinsurance.current_status)
            .all()
        )
    else:
        query = (
            db.session.query(
                Coinsurance.current_status, func.count(Coinsurance.current_status)
            )
            .group_by(Coinsurance.current_status)
            .order_by(Coinsurance.current_status)
            .all()
        )

    case_paid = case(
        (
            Settlement.type_of_transaction == "Paid",
            Settlement.settled_amount,
        ),
        else_=0,
    ).label("Paid")
    case_received = case(
        (
            Settlement.type_of_transaction == "Received",
            Settlement.settled_amount,
        ),
        else_=0,
    ).label("Received")
    settlement_query = (
        db.session.query(Settlement)
        .with_entities(
            func.date_trunc("month", Settlement.date_of_settlement),
            func.date_trunc("year", Settlement.date_of_settlement),
            func.sum(case_paid),
            func.sum(case_received),
        )
        .group_by(
            func.date_trunc("month", Settlement.date_of_settlement),
            func.date_trunc("year", Settlement.date_of_settlement),
        )
        .order_by(
            func.date_trunc("month", Settlement.date_of_settlement).desc(),
            func.date_trunc("year", Settlement.date_of_settlement).desc(),
        )
    )
    # fund_query = (
    #     FundBankStatement.query.filter(
    #         FundBankStatement.flag_description == "COINSURANCE"
    #     )
    #     .order_by(FundBankStatement.id.desc())
    #     .limit(50)
    # )
    return render_template(
        "coinsurance_home.html",
        dashboard=query,
        settlement_query=settlement_query,
        # fund_query=fund_query,
    )


@coinsurance_bp.route("/fetch_receipts/")
def fetch_receipts():

    current_time = datetime.now()

    prev_time = current_time - timedelta(hours=1)
    response = requests.get(
        f"http://0.0.0.0:8000/coinsurance/api/data/funds/?created_after={prev_time}"
    )

    # response = requests.get(
    #     "http://0.0.0.0:8080/coinsurance/api/data/funds/?after=2024-09-11T15:11:11Z"
    # )

    receipts = response.json()
    from extensions import db

    receipt_entries = []
    for receipt in receipts["data"]:
        receipt["transaction_code"] = re.findall(
            r"UII688COINS[a-zA-Z0-9]{6}", receipt["description"]
        )[0]
        receipt["company_name"] = receipt["description"].split(
            receipt["transaction_code"]
        )[1][1:]

        new_entry = CoinsuranceReceipts(
            **receipt,
            status="Pending",
            created_by="API",
        )
        receipt_entries.append(new_entry)
    db.session.add_all(receipt_entries)
    db.session.commit()
    return response.json()


@coinsurance_bp.route("/api/data/funds/", methods=["GET"])
def get_coinsurance_receipts():
    from extensions import db

    entries = (
        db.session.query(FundBankStatement)
        .filter(FundBankStatement.flag_description == "COINSURANCE")
        .order_by(FundBankStatement.id.desc())
    )

    created_after = request.args.get("created_after")
    if created_after:
        entries = entries.filter(FundBankStatement.date_created_date > created_after)

    entries_count = entries.count()

    # search filter
    search = request.args.get("search[value]")
    if search:
        entries = entries.filter(
            db.or_(
                cast(FundBankStatement.book_date, String).like(f"%{search}%"),
                FundBankStatement.description.ilike(f"%{search}%"),
                cast(FundBankStatement.credit, String).like(f"%{search}%"),
                FundBankStatement.reference_no.ilike(f"%{search}%"),
            )
        )

    total_filtered = entries.count()

    # sorting
    # order = []
    # i = 0
    # while True:
    #     col_index = request.args.get(f"order[{i}][column]")
    #     if col_index is None:
    #         break
    #     col_name = request.args.get(f"columns[{col_index}][data]")
    #     descending = request.args.get(f"order[{i}][dir]") == "desc"
    #     col = getattr(FundBankStatement, col_name)
    #     if descending:
    #         col = col.desc()
    #     order.append(col)
    #     i += 1
    # if order:
    #     entries = entries.order_by(*order)

    # pagination
    start = request.args.get("start", type=int)
    length = request.args.get("length", type=int)
    entries = entries.offset(start).limit(length)

    # response
    return {
        "data": [asdict(entry) for entry in entries],
        "recordsFiltered": total_filtered,
        "recordsTotal": entries_count,
        "draw": request.args.get("draw", type=int),
    }


@coinsurance_bp.route("/receipts/add", methods=["POST", "GET"])
@login_required
@admin_required
def add_coinsurance_receipts():

    from extensions import db

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


@coinsurance_bp.route("/receipts/model_add", methods=["POST", "GET"])
@login_required
@admin_required
def add_coinsurance_receipts_model_form():
    """Add new pending coinsurance receipts through model form"""
    from extensions import db

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


@coinsurance_bp.route("/receipts/edit/<int:id>", methods=["POST", "GET"])
@login_required
@admin_required
def edit_coinsurance_receipts(id):

    from extensions import db

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
    from extensions import db

    receipts = db.session.scalars(db.select(CoinsuranceReceipts))
    return render_template("coinsurance_receipts_list.html", receipts=receipts)


@coinsurance_bp.route("/add_entry", methods=["POST", "GET"])
@login_required
def add_coinsurance_entry():
    from server import db

    form = CoinsuranceForm()
    if form.data["bool_reinsurance"]:
        from wtforms.validators import DataRequired

        form.ri_confirmation.validators = [DataRequired()]

    if form.validate_on_submit():
        if current_user.user_type == "oo_user":
            regional_office_code = current_user.ro_code
            oo_code = current_user.oo_code
        elif current_user.user_type == "ro_user":
            regional_office_code = current_user.ro_code
            oo_code = form.data["oo_code"]
        else:
            regional_office_code = form.data["regional_office_code"]
            oo_code = form.data["oo_code"]

        str_period = form.data["period_of_settlement"] or None
        type_of_transaction = form.data["type_of_transaction"]
        coinsurer_name = form.data["coinsurer_name"]
        coinsurer_office_code = form.data["coinsurer_office_code"]
        request_id = form.data["request_id"]
        payable_amount = form.data["payable_amount"] or 0
        receivable_amount = form.data["receivable_amount"] or 0
        name_of_insured = form.data["name_of_insured"]

        bool_ri_involved = form.data["bool_reinsurance"]
        ri_payable_amount = form.data["int_ri_payable_amount"] or 0
        ri_receivable_amount = form.data["int_ri_receivable_amount"] or 0

        net_amount = (
            payable_amount
            - receivable_amount
            + ri_payable_amount
            - ri_receivable_amount
        )

        if form.data["statement"]:
            statement_filename_data = secure_filename(form.data["statement"].filename)
            statement_file_extension = statement_filename_data.rsplit(".", 1)[1]
            statement_filename = (
                "statement"
                + datetime.now().strftime("%d%m%Y %H%M%S")
                + "."
                + statement_file_extension
            )
            form.statement.data.save(
                f"{current_app.config.get("UPLOAD_FOLDER")}coinsurance/statements/"
                + statement_filename
            )
        else:
            statement_filename = None
        if form.data["confirmation"]:
            confirmation_filename_data = secure_filename(
                form.data["confirmation"].filename
            )
            confirmation_file_extension = confirmation_filename_data.rsplit(".", 1)[1]
            confirmation_filename = (
                "confirmation"
                + datetime.now().strftime("%d%m%Y %H%M%S")
                + "."
                + confirmation_file_extension
            )
            form.confirmation.data.save(
                f"{current_app.config.get("UPLOAD_FOLDER")}coinsurance/confirmations/"
                + confirmation_filename
            )
        else:
            confirmation_filename = None
        if bool_ri_involved:
            ri_confirmation_filename_data = secure_filename(
                form.data["ri_confirmation"].filename
            )
            ri_confirmation_file_extension = ri_confirmation_filename_data.rsplit(
                ".", 1
            )[1]
            ri_confirmation_filename = (
                "ri_confirmation"
                + datetime.now().strftime("%d%m%Y %H%M%S")
                + "."
                + ri_confirmation_file_extension
            )
            form.ri_confirmation.data.save(
                f"{current_app.config.get("UPLOAD_FOLDER")}coinsurance/ri_confirmations/"
                + ri_confirmation_filename
            )
        else:
            ri_confirmation_filename = None
        if current_user.user_type in ["admin", "coinsurance_hub_user"]:
            current_status = "To be settled"
        else:
            current_status = "To be reviewed by coinsurance hub"
        form_remarks = form.data["remarks"]
        coinsurance = Coinsurance(
            uiic_regional_code=regional_office_code,
            uiic_office_code=oo_code,
            follower_company_name=coinsurer_name,
            follower_office_code=coinsurer_office_code,
            str_period=str_period,
            payable_amount=payable_amount,
            receivable_amount=receivable_amount,
            request_id=request_id,
            current_status=current_status,
            type_of_transaction=type_of_transaction,
            statement=statement_filename,
            confirmation=confirmation_filename,
            net_amount=net_amount,
            ri_confirmation=ri_confirmation_filename,
            boolean_reinsurance_involved=bool_ri_involved,
            int_ri_payable_amount=ri_payable_amount,
            int_ri_receivable_amount=ri_receivable_amount,
            insured_name=name_of_insured,
            created_by=current_user.username,
            date_created_date=datetime.now(),
        )
        db.session.add(coinsurance)
        db.session.commit()
        if form_remarks:
            remarks = Remarks(
                coinsurance_id=coinsurance.id,
                user=current_user.username,
                remarks=form_remarks,
                time_of_remark=datetime.now(),
            )
            db.session.add(remarks)
            db.session.commit()
        coinsurance_log = Coinsurance_log(
            coinsurance_id=coinsurance.id,
            user=current_user.username,
            time_of_update=datetime.now(),
            uiic_regional_code=regional_office_code,
            uiic_office_code=oo_code,
            follower_company_name=coinsurer_name,
            follower_office_code=coinsurer_office_code,
            payable_amount=payable_amount,
            receivable_amount=receivable_amount,
            request_id=request_id,
            current_status=current_status,
            type_of_transaction=type_of_transaction,
            statement=statement_filename,
            confirmation=confirmation_filename,
            net_amount=net_amount,
            ri_confirmation=ri_confirmation_filename,
            boolean_reinsurance_involved=bool_ri_involved,
            int_ri_payable_amount=ri_payable_amount,
            int_ri_receivable_amount=ri_receivable_amount,
            str_period=str_period,
        )
        db.session.add(coinsurance_log)
        db.session.commit()
        return redirect(
            url_for("coinsurance.view_coinsurance_entry", coinsurance_id=coinsurance.id)
        )

    if current_user.user_type == "oo_user":
        form.regional_office_code.data = current_user.ro_code
        form.oo_code.data = current_user.oo_code
    elif current_user.user_type == "ro_user":
        form.regional_office_code.data = current_user.ro_code

    return render_template(
        "edit_coinsurance_entry.html",
        form=form,
        #  change_status=False,
        enable_save_button=True,
        ro_list=ro_list,
        # update_settlement=False,
    )


def enable_button(current_user, coinsurance_entry) -> bool:
    bool_enable_button: bool = False
    settlement = Settlement.query.filter(
        Settlement.utr_number == coinsurance_entry.utr_number
    ).first()

    if current_user.user_type in ["admin", "coinsurance_hub_user"]:
        if not coinsurance_entry.current_status == "Settled":
            bool_enable_button = True
        elif not settlement:
            bool_enable_button = True

    elif current_user.user_type in ["ro_user", "oo_user"]:
        if coinsurance_entry.current_status == "Needs clarification from RO or OO":
            bool_enable_button = True
    return bool_enable_button


@coinsurance_bp.route("/view/<int:coinsurance_id>")
@login_required
def view_coinsurance_entry(coinsurance_id):
    coinsurance = Coinsurance.query.get_or_404(coinsurance_id)
    remarks = Remarks.query.filter(Remarks.coinsurance_id == coinsurance_id)
    settlement = Settlement.query.filter(
        Settlement.utr_number == coinsurance.utr_number
    ).all()

    enable_edit_button = enable_button(current_user, coinsurance)

    return render_template(
        "view_coinsurance_entry.html",
        coinsurance=coinsurance,
        remarks=remarks,
        settlement=settlement,
        enable_edit_button=enable_edit_button,
    )


@coinsurance_bp.route(
    "/<string:requirement>/<int:coinsurance_id>", methods=["POST", "GET"]
)
@login_required
def download_document(requirement, coinsurance_id):
    coinsurance = Coinsurance.query.get_or_404(coinsurance_id)

    if requirement == "confirmation":
        file_extension = coinsurance.confirmation.rsplit(".", 1)[1]
        path = coinsurance.confirmation
    elif requirement == "statement":
        file_extension = coinsurance.statement.rsplit(".", 1)[1]
        path = coinsurance.statement
    elif requirement == "ri_confirmation":
        file_extension = coinsurance.ri_confirmation.rsplit(".", 1)[1]
        path = coinsurance.ri_confirmation
    else:
        return "No such requirement"
    if coinsurance.net_amount < 0:
        amount_string = f"receivable {coinsurance.net_amount * -1}"
    else:
        amount_string = f"payable {coinsurance.net_amount}"
    filename = f"{coinsurance.type_of_transaction} {requirement} - {coinsurance.uiic_office_code} - {coinsurance.follower_company_name} {amount_string}.{file_extension}"
    return send_from_directory(
        directory=f"{current_app.config.get("UPLOAD_FOLDER")}coinsurance/{requirement}s/",
        path=path,
        as_attachment=True,
        download_name=filename,
    )


@coinsurance_bp.route("/settlements/<int:settlement_id>", methods=["POST", "GET"])
@login_required
def download_settlements(settlement_id):
    settlement = Settlement.query.get_or_404(settlement_id)

    file_extension = settlement.file_settlement_file.rsplit(".", 1)[1]
    path = settlement.file_settlement_file
    filename = f"{settlement.name_of_company} - {settlement.type_of_transaction} - {settlement.utr_number}.{file_extension}"
    return send_from_directory(
        directory=f"{current_app.config.get("UPLOAD_FOLDER")}coinsurance/settlements/",
        path=path,
        as_attachment=True,
        download_name=filename,
    )


def update_utr_choices(coinsurance, form):
    utr_list = (
        Settlement.query.filter(
            coinsurance.follower_company_name == Settlement.name_of_company
        )
        .with_entities(
            Settlement.name_of_company,
            Settlement.utr_number,
            Settlement.date_of_settlement,
            Settlement.settled_amount,
            Settlement.notes,
        )
        .distinct()
    ).order_by(Settlement.date_of_settlement.desc())
    form.settlement.choices = [
        (
            utr_number,
            f"{name_of_company}-{utr_number} Rs. {indian_number_format(settled_amount)} on {date_of_settlement.strftime('%d/%m/%Y')} ({notes})",
        )
        for name_of_company, utr_number, date_of_settlement, settled_amount, notes in utr_list
    ]


@coinsurance_bp.route("/edit/<int:coinsurance_id>", methods=["POST", "GET"])
@login_required
def edit_coinsurance_entry(coinsurance_id):
    from server import db

    form = CoinsuranceForm()
    coinsurance = Coinsurance.query.get_or_404(coinsurance_id)
    if form.data["bool_reinsurance"]:
        from wtforms.validators import DataRequired

        if not coinsurance.ri_confirmation:
            form.ri_confirmation.validators = [DataRequired()]

    if not enable_button(current_user, coinsurance):
        flash("Unable to submit data. Please try again later.")
    elif form.validate_on_submit():
        if current_user.user_type == "oo_user":
            regional_office_code = current_user.ro_code
            oo_code = current_user.oo_code
        elif current_user.user_type == "ro_user":
            regional_office_code = current_user.ro_code
            oo_code = form.data["oo_code"]
        else:
            regional_office_code = form.data["regional_office_code"]
            oo_code = form.data["oo_code"]
        coinsurer_name = form.data["coinsurer_name"]
        coinsurer_office_code = form.data["coinsurer_office_code"]
        payable_amount = form.data["payable_amount"] or 0
        receivable_amount = form.data["receivable_amount"] or 0

        request_id = form.data["request_id"]
        current_status = "To be reviewed by coinsurance hub"
        if current_user.user_type in ["coinsurance_hub_user", "admin"]:
            current_status = form.data["current_status"]

        type_of_transaction = form.data["type_of_transaction"]
        name_of_insured = form.data["name_of_insured"]

        str_period = form.data["period_of_settlement"]
        bool_ri_involved = form.data["bool_reinsurance"]
        ri_payable_amount = form.data["int_ri_payable_amount"] or 0
        ri_receivable_amount = form.data["int_ri_receivable_amount"] or 0

        net_amount = (
            payable_amount
            - receivable_amount
            + ri_payable_amount
            - ri_receivable_amount
        )
        statement_filename = coinsurance.statement
        if form.data["statement"]:
            statement_filename_data = secure_filename(form.data["statement"].filename)
            statement_file_extension = statement_filename_data.rsplit(".", 1)[1]
            statement_filename = (
                "statement"
                + datetime.now().strftime("%d%m%Y %H%M%S")
                + "."
                + statement_file_extension
            )
            form.statement.data.save(
                f"{current_app.config.get("UPLOAD_FOLDER")}coinsurance/statements/"
                + statement_filename
            )
            coinsurance.statement = statement_filename

        confirmation_filename = coinsurance.confirmation

        if form.data["confirmation"]:
            confirmation_filename_data = secure_filename(
                form.data["confirmation"].filename
            )
            confirmation_file_extension = confirmation_filename_data.rsplit(".", 1)[1]
            confirmation_filename = (
                "confirmation"
                + datetime.now().strftime("%d%m%Y %H%M%S")
                + "."
                + confirmation_file_extension
            )
            form.confirmation.data.save(
                f"{current_app.config.get("UPLOAD_FOLDER")}coinsurance/confirmations/"
                + confirmation_filename
            )
            coinsurance.confirmation = confirmation_filename

        ri_confirmation_filename = coinsurance.ri_confirmation

        if bool_ri_involved and form.data["ri_confirmation"]:
            ri_confirmation_filename_data = secure_filename(
                form.data["ri_confirmation"].filename
            )
            ri_confirmation_file_extension = ri_confirmation_filename_data.rsplit(
                ".", 1
            )[1]
            ri_confirmation_filename = (
                "ri_confirmation"
                + datetime.now().strftime("%d%m%Y %H%M%S")
                + "."
                + ri_confirmation_file_extension
            )
            form.ri_confirmation.data.save(
                f"{current_app.config.get("UPLOAD_FOLDER")}coinsurance/ri_confirmations/"
                + ri_confirmation_filename
            )
            coinsurance.ri_confirmation = ri_confirmation_filename

        if form.data["current_status"] == "Settled" and form.data["settlement"]:
            utr_number = form.data["settlement"]
            coinsurance.utr_number = utr_number

        coinsurance.uiic_regional_code = regional_office_code
        coinsurance.uiic_office_code = oo_code
        coinsurance.follower_company_name = coinsurer_name
        coinsurance.follower_office_code = coinsurer_office_code

        coinsurance.str_period = str_period
        coinsurance.type_of_transaction = type_of_transaction
        coinsurance.payable_amount = payable_amount
        coinsurance.receivable_amount = receivable_amount
        coinsurance.net_amount = net_amount
        coinsurance.request_id = request_id

        coinsurance.boolean_reinsurance_involved = bool_ri_involved
        coinsurance.int_ri_payable_amount = ri_payable_amount
        coinsurance.int_ri_receivable_amount = ri_receivable_amount

        coinsurance.current_status = current_status
        coinsurance.insured_name = name_of_insured

        db.session.commit()

        if form.data["remarks"]:
            remarks = Remarks(
                coinsurance_id=coinsurance.id,
                user=current_user.username,
                remarks=form.data["remarks"],
                time_of_remark=datetime.now(),
            )
            db.session.add(remarks)
            db.session.commit()

        coinsurance_log = Coinsurance_log(
            coinsurance_id=coinsurance.id,
            user=current_user.username,
            time_of_update=datetime.now(),
            uiic_regional_code=regional_office_code,
            uiic_office_code=oo_code,
            follower_company_name=coinsurer_name,
            follower_office_code=coinsurer_office_code,
            payable_amount=payable_amount,
            receivable_amount=receivable_amount,
            request_id=request_id,
            current_status=current_status,
            type_of_transaction=type_of_transaction,
            statement=statement_filename,
            confirmation=confirmation_filename,
            net_amount=net_amount,
            ri_confirmation=ri_confirmation_filename,
            boolean_reinsurance_involved=bool_ri_involved,
            int_ri_payable_amount=ri_payable_amount,
            int_ri_receivable_amount=ri_receivable_amount,
            utr_number=form.data["settlement"],
            str_period=str_period,
        )
        db.session.add(coinsurance_log)
        db.session.commit()

        return redirect(
            url_for("coinsurance.view_coinsurance_entry", coinsurance_id=coinsurance_id)
        )
    remarks = Remarks.query.filter(Remarks.coinsurance_id == coinsurance_id)

    form.regional_office_code.data = coinsurance.uiic_regional_code
    form.oo_code.data = coinsurance.uiic_office_code
    form.coinsurer_name.data = coinsurance.follower_company_name
    form.coinsurer_office_code.data = coinsurance.follower_office_code

    form.payable_amount.data = coinsurance.payable_amount
    form.receivable_amount.data = coinsurance.receivable_amount
    form.type_of_transaction.data = coinsurance.type_of_transaction
    form.request_id.data = coinsurance.request_id
    form.current_status.data = coinsurance.current_status

    form.period_of_settlement.data = coinsurance.str_period
    form.bool_reinsurance.data = coinsurance.boolean_reinsurance_involved
    form.name_of_insured.data = coinsurance.insured_name

    if coinsurance.boolean_reinsurance_involved:
        form.int_ri_payable_amount.data = coinsurance.int_ri_payable_amount
        form.int_ri_receivable_amount.data = coinsurance.int_ri_receivable_amount

    change_status = (
        True if current_user.user_type in ["admin", "coinsurance_hub_user"] else False
    )
    update_settlement = False

    enable_save_button = enable_button(current_user, coinsurance)
    if current_user.user_type in ["admin", "coinsurance_hub_user"]:
        if coinsurance.current_status == "Settled":
            if not Settlement.query.filter(
                Settlement.utr_number == coinsurance.utr_number
            ).first():
                update_settlement = True
                update_utr_choices(coinsurance, form)
    return render_template(
        "edit_coinsurance_entry.html",
        form=form,
        coinsurance=coinsurance,
        remarks=remarks,
        change_status=change_status,
        enable_save_button=enable_save_button,
        update_settlement=update_settlement,
        edit=True,
        ro_list=ro_list,
    )


def select_coinsurers(query, form):
    coinsurer_choices = query.order_by(
        Coinsurance.follower_company_name.asc()
    ).distinct(Coinsurance.follower_company_name)
    form.coinsurer_name.choices = ["View all"] + [
        x.follower_company_name for x in coinsurer_choices
    ]

    if form.validate_on_submit() and form.filter_coinsurer.data:
        coinsurer_choice: str = form.data["coinsurer_name"]
        if coinsurer_choice != "View all":
            query = query.filter(Coinsurance.follower_company_name == coinsurer_choice)
    return query


@coinsurance_bp.route("/list/Settled/exception", methods=["POST", "GET"])
@login_required
def list_settled_entries_without_utr():
    form_select_coinsurer = CoinsurerSelectForm()
    coinsurance_entries = (
        Coinsurance.query.order_by(Coinsurance.follower_company_name.desc())
        .filter(Coinsurance.utr_number.is_(None))
        .filter(Coinsurance.current_status == "Settled")
    )

    if current_user.user_type == "ro_user":
        coinsurance_entries = Coinsurance.query.filter(
            Coinsurance.uiic_regional_code == current_user.ro_code
        )

    elif current_user.user_type == "oo_user":
        coinsurance_entries = Coinsurance.query.filter(
            (Coinsurance.uiic_office_code == current_user.oo_code)
            & (Coinsurance.uiic_regional_code == current_user.ro_code)
        )

    coinsurance_entries = select_coinsurers(coinsurance_entries, form_select_coinsurer)

    return render_template(
        "view_all_coinsurance_entries.html",
        coinsurance_entries=coinsurance_entries,
        update_settlement=False,
        form_select_coinsurer=form_select_coinsurer,
        title="Settled entries without UTR number",
        # show_zones=show_zones,
    )


@coinsurance_bp.route("/list/<string:coinsurer_name>/", methods=["POST", "GET"])
@login_required
def list_coinsurance_entries_by_coinsurer_name(coinsurer_name):
    form_select_coinsurer = CoinsurerSelectForm()

    from extensions import db

    coinsurance_entries = db.session.query(Coinsurance).filter(
        Coinsurance.follower_company_name == coinsurer_name
    )  # Coinsurance.query.filter()

    coinsurance_entries = coinsurance_entries.filter(
        Coinsurance.current_status != "No longer valid"
    ).order_by(Coinsurance.follower_company_name.asc())
    if current_user.user_type == "ro_user":
        coinsurance_entries = Coinsurance.query.filter(
            Coinsurance.uiic_regional_code == current_user.ro_code
        )

    elif current_user.user_type == "oo_user":
        coinsurance_entries = Coinsurance.query.filter(
            (Coinsurance.uiic_office_code == current_user.oo_code)
            & (Coinsurance.uiic_regional_code == current_user.ro_code)
        )

    coinsurance_entries = select_coinsurers(coinsurance_entries, form_select_coinsurer)

    if current_user.user_type == "ro_user":
        custom_title = f" uploaded by RO {current_user.ro_code}"
    elif current_user.user_type == "oo_user":
        custom_title = f" uploaded by OO {current_user.oo_code}"
    else:
        custom_title = ""

    return render_template(
        "view_all_coinsurance_entries.html",
        coinsurance_entries=coinsurance_entries,
        update_settlement=False,
        form_select_coinsurer=form_select_coinsurer,
        title=f"List of all coinsurance confirmations of {coinsurer_name} {custom_title}",
        # show_zones=show_zones,
    )


@coinsurance_bp.route("/list/all", methods=["POST", "GET"])
@login_required
def list_coinsurance_entries():
    form_select_coinsurer = CoinsurerSelectForm()

    coinsurance_entries = Coinsurance.query.filter(
        Coinsurance.current_status != "No longer valid"
    ).order_by(Coinsurance.follower_company_name.asc())
    if current_user.user_type == "ro_user":
        coinsurance_entries = Coinsurance.query.filter(
            Coinsurance.uiic_regional_code == current_user.ro_code
        )

    elif current_user.user_type == "oo_user":
        coinsurance_entries = Coinsurance.query.filter(
            (Coinsurance.uiic_office_code == current_user.oo_code)
            & (Coinsurance.uiic_regional_code == current_user.ro_code)
        )

    coinsurance_entries = select_coinsurers(coinsurance_entries, form_select_coinsurer)

    if current_user.user_type == "ro_user":
        custom_title = f" uploaded by RO {current_user.ro_code}"
    elif current_user.user_type == "oo_user":
        custom_title = f" uploaded by OO {current_user.oo_code}"
    else:
        custom_title = ""

    return render_template(
        "view_all_coinsurance_entries.html",
        coinsurance_entries=coinsurance_entries,
        update_settlement=False,
        form_select_coinsurer=form_select_coinsurer,
        title=f"List of all coinsurance confirmations{custom_title}",
        # show_zones=show_zones,
    )


@coinsurance_bp.route("/list/<string:status>", methods=["POST", "GET"])
@login_required
def list_coinsurance_entries_by_status(status):
    form_select_coinsurer = CoinsurerSelectForm()

    coinsurance_entries = Coinsurance.query.filter(
        Coinsurance.current_status == status
    ).order_by(Coinsurance.follower_company_name.asc())
    if current_user.user_type == "ro_user":
        coinsurance_entries = coinsurance_entries.filter(
            Coinsurance.uiic_regional_code == current_user.ro_code
        )

    elif current_user.user_type == "oo_user":
        coinsurance_entries = coinsurance_entries.filter(
            (Coinsurance.uiic_office_code == current_user.oo_code)
            & (Coinsurance.uiic_regional_code == current_user.ro_code)
        )

    coinsurance_entries = select_coinsurers(coinsurance_entries, form_select_coinsurer)

    if current_user.user_type in ["admin", "coinsurance_hub_user"]:
        if status in ["To be settled"]:  # , "To be considered for settlement"]:
            coinsurer_choices = coinsurance_entries.distinct(
                Coinsurance.follower_company_name
            )
            list_coinsurer_choices = [
                x.follower_company_name for x in coinsurer_choices
            ]

            from server import db

            form = SettlementUTRForm()

            utr_list = (
                Settlement.query.with_entities(
                    Settlement.name_of_company,
                    Settlement.utr_number,
                    Settlement.settled_amount,
                    Settlement.date_of_settlement,
                    Settlement.notes,
                )
                .order_by(Settlement.date_of_settlement.desc())
                .distinct()
            )
            form.utr_number.choices = [
                (
                    utr_number,
                    f"{name_of_company}-{utr_number}: Rs. {indian_number_format(settled_amount)} on {date_of_settlement.strftime('%d/%m/%Y')} ({notes})",
                )
                for name_of_company, utr_number, settled_amount, date_of_settlement, notes in utr_list
                if name_of_company in list_coinsurer_choices
            ]

            # update_settlement = True
            if (
                form.validate_on_submit() and form.update_settlement.data
            ):  # request.method == "POST":
                form_coinsurance_keys = request.form.getlist("coinsurance_keys")
                form_utr_number = form.data["utr_number"]
                settlement_company_check = Settlement.query.filter(
                    Settlement.utr_number == form_utr_number
                ).first()
                for key in form_coinsurance_keys:
                    coinsurance = Coinsurance.query.get_or_404(key)
                    if (
                        coinsurance.follower_company_name
                        == settlement_company_check.name_of_company
                    ):
                        coinsurance.utr_number = form_utr_number
                        coinsurance.current_status = "Settled"

                        coinsurance_log = Coinsurance_log(
                            coinsurance_id=coinsurance.id,
                            user=current_user.username,
                            time_of_update=datetime.now(),
                            uiic_regional_code=coinsurance.uiic_regional_code,
                            uiic_office_code=coinsurance.uiic_office_code,
                            follower_company_name=coinsurance.follower_company_name,
                            follower_office_code=coinsurance.follower_office_code,
                            payable_amount=coinsurance.payable_amount,
                            receivable_amount=coinsurance.receivable_amount,
                            request_id=coinsurance.request_id,
                            current_status="Settled",
                            type_of_transaction=coinsurance.type_of_transaction,
                            statement=coinsurance.statement,
                            confirmation=coinsurance.confirmation,
                            net_amount=coinsurance.net_amount,
                            ri_confirmation=coinsurance.ri_confirmation,
                            boolean_reinsurance_involved=coinsurance.boolean_reinsurance_involved,
                            int_ri_payable_amount=coinsurance.int_ri_payable_amount,
                            int_ri_receivable_amount=coinsurance.int_ri_receivable_amount,
                            utr_number=form_utr_number,
                        )
                        db.session.add(coinsurance_log)
                db.session.commit()
                return redirect(
                    url_for(
                        "coinsurance.list_settled_coinsurance_entries",
                        utr_number=form_utr_number,
                    )
                )

            return render_template(
                "view_all_coinsurance_entries.html",
                coinsurance_entries=coinsurance_entries,
                update_settlement=True,
                status=status,
                form=form,
                form_select_coinsurer=form_select_coinsurer,
                # show_zones=show_zones,
            )
        else:
            return render_template(
                "view_all_coinsurance_entries.html",
                coinsurance_entries=coinsurance_entries,
                update_settlement=True,
                status=status,
                form_select_coinsurer=form_select_coinsurer,
                # show_zones=show_zones,
            )
    else:
        return render_template(
            "view_all_coinsurance_entries.html",
            coinsurance_entries=coinsurance_entries,
            update_settlement=False,
            status=status,
            form_select_coinsurer=form_select_coinsurer,
            # show_zones=show_zones,
        )


@coinsurance_bp.route("/list/settlements/<string:utr_number>", methods=["POST", "GET"])
@login_required
def list_settled_coinsurance_entries(utr_number):
    form_select_coinsurer = CoinsurerSelectForm()
    coinsurance_entries = Coinsurance.query.filter(Coinsurance.utr_number == utr_number)
    coinsurance_entries = select_coinsurers(coinsurance_entries, form_select_coinsurer)

    return render_template(
        "view_all_coinsurance_entries.html",
        coinsurance_entries=coinsurance_entries,
        update_settlement=False,
        form_select_coinsurer=form_select_coinsurer,
        # show_zones=show_zones,
    )


@coinsurance_bp.route("/settlements/list")
@login_required
def list_settlement_entries():
    from extensions import db

    settlement_entries = db.session.scalars(db.select(Settlement))  # .query.all()

    return render_template(
        "list_settlement_entries.html", settlement_entries=settlement_entries
    )


@coinsurance_bp.route("/settlements/view/<int:settlement_id>/")
@login_required
def view_settlement_entry(settlement_id):
    from extensions import db

    settlement = db.get_or_404(Settlement, settlement_id)
    return render_template("view_settlement_entry.html", settlement=settlement)


@coinsurance_bp.route("/settlements/add_settlement_data/", methods=["POST", "GET"])
@login_required
def add_settlement_data():
    from extensions import db

    form = SettlementForm()
    if form.validate_on_submit():

        settlement = Settlement()
        form.populate_obj(settlement)
        db.session.add(settlement)
        if form.data["settlement_file"]:
            settlement_filename_data = secure_filename(
                form.data["settlement_file"].filename
            )
            settlement_file_extension = settlement_filename_data.rsplit(".", 1)[1]
            settlement_filename = (
                "settlement"
                + datetime.now().strftime("%d%m%Y %H%M%S")
                + "."
                + settlement_file_extension
            )
            form.settlement_file.data.save(
                f"{current_app.config.get("UPLOAD_FOLDER")}coinsurance/settlements/"
                + settlement_filename
            )

            settlement.file_settlement_file = settlement_filename

        db.session.commit()

        return redirect(
            url_for("coinsurance.view_settlement_entry", settlement_id=settlement.id)
        )
    return render_template("add_settlement_entry.html", form=form)


@coinsurance_bp.route("/settlements/edit/<int:settlement_id>/", methods=["POST", "GET"])
@login_required
@admin_required
def edit_settlement_entry(settlement_id):
    from extensions import db

    settlement = db.get_or_404(Settlement, settlement_id)
    form = SettlementForm(obj=settlement)
    if form.validate_on_submit():

        form.populate_obj(settlement)
        if form.data["settlement_file"]:
            settlement_filename_data = secure_filename(
                form.data["settlement_file"].filename
            )
            settlement_file_extension = settlement_filename_data.rsplit(".", 1)[1]
            settlement_filename = (
                "settlement"
                + datetime.now().strftime("%d%m%Y %H%M%S")
                + "."
                + settlement_file_extension
            )
            form.settlement_file.data.save(
                f"{current_app.config.get("UPLOAD_FOLDER")}coinsurance/settlements/"
                + settlement_filename
            )
            settlement.file_settlement_file = settlement_filename

        db.session.commit()
        return redirect(
            url_for("coinsurance.view_settlement_entry", settlement_id=settlement.id)
        )

    return render_template(
        "add_settlement_entry.html", form=form, edit=True, settlement=settlement
    )


@coinsurance_bp.route("/log/<int:coinsurance_id>")
@login_required
def view_coinsurance_log(coinsurance_id):
    log = Coinsurance_log.query.filter(
        Coinsurance_log.coinsurance_id == coinsurance_id
    ).order_by(Coinsurance_log.id)
    column_names = Coinsurance_log.query.statement.columns.keys()
    return render_template(
        "view_coinsurance_log.html", log=log, column_names=column_names
    )


@coinsurance_bp.route("/coinsurance_balance/upload", methods=["POST", "GET"])
@login_required
@admin_required
def upload_coinsurance_balance():
    if request.method == "POST":
        file_upload_coinsurance_balance = request.files.get("file")
        df_coinsurance_balance = pd.read_excel(
            file_upload_coinsurance_balance,
            sheet_name="office_wise",
            dtype={
                "Office Code": str,
                "Company name": str,
                "Hub Due from Claims": float,
                "Hub Due from Premium": float,
                "Hub Due to Claims": float,
                "Hub Due to Premium": float,
                "OO Due to": float,
                "OO Due from": float,
                "Net": float,
                "Period": str,
                "Regional Code": str,
                "Zone": str,
            },
        )
        df_coinsurance_balance.rename(
            columns={
                "Office Code": "office_code",
                "Company name": "company_name",
                "Hub Due from Claims": "hub_due_from_claims",
                "Hub Due from Premium": "hub_due_from_premium",
                "Hub Due to Claims": "hub_due_to_claims",
                "Hub Due to Premium": "hub_due_to_premium",
                "OO Due to": "oo_due_to",
                "OO Due from": "oo_due_from",
                "Net": "net_amount",
                "Period": "period",
                "Regional Code": "str_regional_office_code",
                "Zone": "str_zone",
            },
            inplace=True,
        )
        df_coinsurance_balance["created_by"] = current_user.username
        df_coinsurance_balance["created_on"] = datetime.now()
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
        df_coinsurance_balance.to_sql(
            "coinsurance_balances", engine, if_exists="append", index=False
        )
        flash("Coinsurance balance has been uploaded to database.")
    return render_template("coinsurance_balance_upload.html")


@coinsurance_bp.route("/coinsurance_balance/", methods=["POST", "GET"])
@login_required
def query_view_coinsurance_balance():

    form = CoinsuranceBalanceQueryForm()

    # Querying distinct list of periods from the table
    period_list_query = CoinsuranceBalances.query.with_entities(
        CoinsuranceBalances.period
    ).distinct()

    # converting the period from string to datetime object
    list_period = [datetime.strptime(item[0], "%b-%y") for item in period_list_query]

    # sorting the items of list_period in reverse order
    # newer months will be above
    list_period.sort(reverse=True)

    # list_period is now dynamically added as dropdown choice list to the SelectField
    form.period.choices = [
        (item.strftime("%b-%y"), item.strftime("%B-%Y")) for item in list_period
    ]

    # default choice is set from the top most option in form.period.choices
    period = form.period.choices[0][0]

    if form.validate_on_submit():
        period = form.data["period"]
    coinsurance_balance = CoinsuranceBalances.query.filter(
        CoinsuranceBalances.period == period
    )

    summary = (
        CoinsuranceBalances.query.with_entities(
            CoinsuranceBalances.company_name,
            func.sum(CoinsuranceBalances.hub_due_to_claims),
            func.sum(CoinsuranceBalances.hub_due_to_premium),
            func.sum(CoinsuranceBalances.oo_due_to),
            func.sum(CoinsuranceBalances.hub_due_from_claims),
            func.sum(CoinsuranceBalances.hub_due_from_premium),
            func.sum(CoinsuranceBalances.oo_due_from),
            func.sum(CoinsuranceBalances.net_amount),
        )
        .filter(CoinsuranceBalances.period == period)
        .group_by(CoinsuranceBalances.company_name)
        .order_by(CoinsuranceBalances.company_name)
    )

    if form.data["head_office_balance"] == False:
        summary = summary.filter(
            CoinsuranceBalances.office_code.not_in(("000100", "660000", "001900"))
        )
        coinsurance_balance = coinsurance_balance.filter(
            CoinsuranceBalances.office_code.not_in(("000100", "660000", "001900"))
        )

    if current_user.user_type == "ro_user":
        summary = summary.filter(
            CoinsuranceBalances.str_regional_office_code == current_user.ro_code
        )
        coinsurance_balance = coinsurance_balance.filter(
            CoinsuranceBalances.str_regional_office_code == current_user.ro_code
        )
    return render_template(
        "view_coinsurance_balance.html",
        coinsurance_balance=coinsurance_balance,
        summary=summary,
        form=form,
        period=period,
    )


@coinsurance_bp.route("/cash_call/add", methods=["POST", "GET"])
@login_required
def add_cash_call():
    form = CoinsuranceCashCallForm()
    from extensions import db

    if form.validate_on_submit():
        cash_call = CoinsuranceCashCall()
        form.populate_obj(cash_call)

        db.session.add(cash_call)

        db.session.commit()
        return redirect(
            url_for("coinsurance.view_cash_call", cash_call_key=cash_call.id)
        )

    return render_template("cash_call_add.html", form=form, title="Add new cash call")


@coinsurance_bp.route("/cash_call/view/<int:cash_call_key>")
@login_required
def view_cash_call(cash_call_key):
    from extensions import db

    cash_call = db.get_or_404(CoinsuranceCashCall, cash_call_key)
    return render_template("cash_call_view.html", cash_call=cash_call)


@coinsurance_bp.route("/cash_call/list/<string:status>")
@login_required
def list_cash_calls(status="all"):
    from extensions import db

    list = db.session.scalars(db.select(CoinsuranceCashCall))

    return render_template("cash_call_list.html", list=list)


@coinsurance_bp.route("/cash_call/edit/<int:cash_call_key>", methods=["POST", "GET"])
@login_required
def edit_cash_call(cash_call_key):
    from extensions import db

    cash_call = db.get_or_404(CoinsuranceCashCall, cash_call_key)

    form = CoinsuranceCashCallForm(obj=cash_call)
    if form.validate_on_submit():
        form.populate_obj(cash_call)

        db.session.commit()
        return redirect(
            url_for("coinsurance.view_cash_call", cash_call_key=cash_call.id)
        )

    return render_template(
        "cash_call_add.html", form=form, title="Edit cash call details"
    )


# bulk upload cash calls
@coinsurance_bp.route("/cash_call/bulk_upload", methods=["POST", "GET"])
@login_required
def bulk_upload_cash_call():
    form = UploadFileForm()
    if form.validate_on_submit():
        df_cash_call = pd.read_excel(form.data["file_upload"])
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))

        df_cash_call["created_on"] = datetime.now()
        df_cash_call["created_by"] = current_user.username

        df_cash_call.to_sql(
            "coinsurance_cash_call",
            engine,
            if_exists="append",
            index=False,
        )
        flash("Coinsurance cash call details have been uploaded successfully.")
    return render_template(
        "coinsurance_upload_file_template.html",
        form=form,
        title="Bulk upload cash call details",
    )


# bulk upload settlements
@coinsurance_bp.route("/settlements/bulk_upload", methods=["POST", "GET"])
@login_required
def bulk_upload_settlements():
    form = UploadFileForm()
    if form.validate_on_submit():
        df_settlement = pd.read_excel(form.data["file_upload"])
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))

        df_settlement["created_on"] = datetime.now()
        df_settlement["created_by"] = current_user.username

        df_settlement.to_sql(
            "settlement",
            engine,
            if_exists="append",
            index=False,
        )
        flash("Settlement details have been uploaded successfully.")
    return render_template(
        "coinsurance_upload_file_template.html",
        form=form,
        title="Bulk upload settlement details",
    )


@coinsurance_bp.route("/query/", methods=["POST", "GET"])
@login_required
def query_coinsurance_entries():
    form = QueryForm()
    if form.validate_on_submit():
        from extensions import db

        status_list = form.status.data
        coinsurers_list = form.coinsurer_name.data
        # coinsurance_entries = Coinsurance.query.order_by(
        #     Coinsurance.follower_company_name.desc
        # )
        coinsurance_entries = db.session.query(Coinsurance)
        # zone = form.zone.data
        if status_list:
            coinsurance_entries = coinsurance_entries.filter(
                Coinsurance.current_status.in_(status_list)
            )
        if coinsurers_list:
            coinsurance_entries = coinsurance_entries.filter(
                Coinsurance.follower_company_name.in_(coinsurers_list)
            )
        # coinsurance_entries = coinsurance_entries.filter(Coinsurance.get_zone.in_(zone))

        form_select_coinsurer = CoinsurerSelectForm()
        coinsurance_entries = select_coinsurers(
            coinsurance_entries, form_select_coinsurer
        )
        #        custom_title = ""

        return render_template(
            "view_all_coinsurance_entries.html",
            coinsurance_entries=coinsurance_entries,
            update_settlement=False,
            form_select_coinsurer=form_select_coinsurer,
            title="Results of query",
            # show_zones=show_zones,
        )

    return render_template("query_coinsurance_entries.html", form=form)


@coinsurance_bp.route("/coinsurance_balance/generate", methods=["POST", "GET"])
@login_required
@admin_required
def generate_coinsurance_balance():

    form = CoinsuranceBalanceForm()

    if form.validate_on_submit():
        period = form.period.data
        flag_sheet = form.flag_sheet_file.data

        list_df = [pd.read_csv(file) for file in form.csv_files_upload.data]

        # Concatenate all DataFrames into a single DataFrame
        df_concat = pd.concat(list_df, ignore_index=True)

        # Adjust credit and debit by dividing by 2 where the office code is 100
        df_concat.loc[df_concat["Office Code"] == 100, "Credit"] = (
            df_concat["Credit"] / 2
        )
        df_concat.loc[df_concat["Office Code"] == 100, "Debit"] = df_concat["Debit"] / 2

        # Calculate the net amount by subtracting debits from credits
        df_concat["Net amount"] = df_concat["Credit"] - df_concat["Debit"]

        # Remove rows where the net amount is zero
        df_concat = df_concat[df_concat["Net amount"] != 0]

        # Load additional data for GL codes and zones from an Excel file
        df_flag_sheet = pd.read_excel(flag_sheet, sheet_name="GLCodes")
        df_zones = pd.read_excel(
            flag_sheet, sheet_name="Zones", dtype={"Regional Code": str}
        )

        # Merge the concatenated data with the flag sheet on GLCode
        df_merged = df_concat.merge(df_flag_sheet, on="GLCode", how="left")

        # Generate office-wise and company-wise pivot tables
        pivot_df_merged_office = prepare_pivot(
            df_merged, df_zones, ["Office Code", "Company name"], period
        )
        pivot_df_merged = prepare_pivot(
            df_merged, df_zones, ["Company name", "Office Code"], period
        )

        # Generate a company-wise summary
        pivot_companywise = pivot_df_merged.pivot_table(
            index="Company name", values="Net", aggfunc="sum"
        )
        pivot_companywise.reset_index(inplace=True)

        # Write the pivot tables and summary to an Excel file
        with pd.ExcelWriter(
            f"coinsurance_balances/coinsurance_balance_{period}.xlsx"
        ) as writer:
            pivot_df_merged_office.to_excel(
                writer, sheet_name="office_wise", index=False
            )
            pivot_df_merged.to_excel(writer, sheet_name="company_wise", index=False)
            pivot_companywise.to_excel(writer, sheet_name="summary", index=False)

            # Apply formatting to the Excel sheets
            format_workbook = writer.book
            format_currency = format_workbook.add_format({"num_format": "##,##,#0.00"})

            format_worksheet_oo = writer.sheets["office_wise"]
            format_worksheet_oo.set_column("C:I", 11, format_currency)
            format_worksheet_oo.autofit()

            format_worksheet_company = writer.sheets["company_wise"]
            format_worksheet_company.set_column("C:I", 11, format_currency)
            format_worksheet_company.autofit()

            format_worksheet_summary = writer.sheets["summary"]
            format_worksheet_summary.set_column("B:B", 11, format_currency)
            format_worksheet_summary.autofit()

        return send_from_directory(
            directory="coinsurance_balances/",
            path=f"coinsurance_balance_{period}.xlsx",
            download_name=f"coinsurance_balance_{period}.xlsx",
            as_attachment=True,
        )

    return render_template("generate_coinsurance_balance.html", form=form)


def prepare_pivot(df_merged, df_zones, index_list, period):
    """
    Prepares a pivot table summarizing the net amounts.

    Parameters:
        df_merged (DataFrame): The merged DataFrame containing financial data.
        index_list (list): List of columns to group by in the pivot table.
        period (str): The accounting period.

    Returns:
        DataFrame: A pivot table summarizing net amounts by the specified indices.
    """

    # Create a pivot table based on the specified index columns and descriptions
    pivot_df_merged_office = df_merged.pivot_table(
        index=index_list,
        columns="Description",
        values="Net amount",
        aggfunc="sum",
    )

    # Replace NaN values with 0 and calculate the net amount
    pivot_df_merged_office.fillna(0, inplace=True)
    pivot_df_merged_office["Net"] = (
        pivot_df_merged_office["OO Due to"]
        + pivot_df_merged_office["Hub Due to Premium"]
        + pivot_df_merged_office["Hub Due to Claims"]
        + pivot_df_merged_office["OO Due from"]
        + pivot_df_merged_office["Hub Due from Premium"]
        + pivot_df_merged_office["Hub Due from Claims"]
    )

    pivot_df_merged_office.reset_index(inplace=True)

    # Derive the regional code by dividing the office code by 10000 and rounding
    pivot_df_merged_office["Regional Code"] = np.where(
        pivot_df_merged_office["Office Code"].between(10000, 310000),
        (pivot_df_merged_office["Office Code"] // 10000) * 10000,
        pivot_df_merged_office["Office Code"],
    )
    pivot_df_merged_office["Regional Code"] = (
        pivot_df_merged_office["Regional Code"].astype(int).astype(str).str.zfill(6)
    )
    pivot_df_merged_office["Office Code"] = (
        pivot_df_merged_office["Office Code"].astype(str).str.zfill(6)
    )

    # Merge the calculated regional codes with the zones data from the flag sheet
    pivot_df_merged_office = pivot_df_merged_office.merge(
        df_zones, on="Regional Code", how="left"
    )

    # Add the period to the pivot table
    pivot_df_merged_office["Period"] = period

    return pivot_df_merged_office


@coinsurance_bp.route("/bank_mandate/add/", methods=["POST", "GET"])
@login_required
@admin_required
def add_bank_mandate():
    from extensions import db

    form = CoinsuranceBankMandateForm()
    if form.validate_on_submit():
        bank_mandate = CoinsuranceBankMandate()
        form.populate_obj(bank_mandate)
        if form.data["bank_mandate_file"]:

            bank_mandate_data = secure_filename(form.data["bank_mandate_file"].filename)
            bank_mandate_file_extension = bank_mandate_data.rsplit(".", 1)[1]
            bank_mandate_filename = (
                "bank_mandate_"
                + datetime.now().strftime("%d%m%Y %H%M%S")
                + "."
                + bank_mandate_file_extension
            )

            form.bank_mandate_file.data.save(
                current_app.config.get("UPLOAD_FOLDER")
                + "coinsurance/bank_mandates/"
                + bank_mandate_filename
            )
            bank_mandate.bank_mandate = bank_mandate_filename

        db.session.add(bank_mandate)
        db.session.commit()

        return redirect(url_for("coinsurance.list_bank_mandates"))
    return render_template("bank_mandate_add.html", form=form, title="Add bank mandate")


@coinsurance_bp.route("/bank_mandate/edit/<int:key>/", methods=["POST", "GET"])
@login_required
@admin_required
def edit_bank_mandate(key):
    from extensions import db

    bank_mandate = db.get_or_404(CoinsuranceBankMandate, key)
    form = CoinsuranceBankMandateForm(obj=bank_mandate)

    if form.validate_on_submit():
        form.populate_obj(bank_mandate)

        if form.data["bank_mandate_file"]:

            bank_mandate_data = secure_filename(form.data["bank_mandate_file"].filename)
            bank_mandate_file_extension = bank_mandate_data.rsplit(".", 1)[1]
            bank_mandate_filename = (
                "bank_mandate_"
                + datetime.now().strftime("%d%m%Y %H%M%S")
                + "."
                + bank_mandate_file_extension
            )
            form.bank_mandate_file.data.save(
                current_app.config.get("UPLOAD_FOLDER")
                + "coinsurance/bank_mandates/"
                + bank_mandate_filename
            )
            bank_mandate.bank_mandate = bank_mandate_filename

        db.session.commit()
        return redirect(url_for("coinsurance.list_bank_mandates"))
    return render_template(
        "bank_mandate_add.html",
        form=form,
        bank_mandate=bank_mandate,
        title="Edit bank mandate",
    )


@coinsurance_bp.route("/bank_mandate/download/<int:key>/")
@login_required
def download_bank_mandate(key):
    from extensions import db

    bank_mandate = db.get_or_404(CoinsuranceBankMandate, key)
    return send_from_directory(
        directory=f"{current_app.config.get("UPLOAD_FOLDER")}coinsurance/bank_mandates/",
        path=bank_mandate.bank_mandate,
        download_name=f"{bank_mandate.company_name}_{bank_mandate.office_code}_{bank_mandate.bank_name}_{bank_mandate.bank_account_number [-5:]}.pdf",
        as_attachment=True,
    )


@coinsurance_bp.route("/bank_mandate/")
@login_required
def list_bank_mandates():
    from extensions import db

    bank_mandates = db.session.scalars(
        db.select(
            CoinsuranceBankMandate
        )  # .order_by(CoinsuranceBankMandate.company_name)
    )  # .scalars()

    return render_template("bank_mandate_list.html", bank_mandates=bank_mandates)


@coinsurance_bp.route("/coinsurance_balance/delete/", methods=["GET", "POST"])
@login_required
@admin_required
def delete_coinsurance_balance():
    from extensions import db

    form = DeleteCoinsuranceBalanceEntries()

    # Querying distinct list of periods from the table
    period_list_query = CoinsuranceBalances.query.with_entities(
        CoinsuranceBalances.period
    ).distinct()

    # converting the period from string to datetime object
    list_period = [datetime.strptime(item[0], "%b-%y") for item in period_list_query]

    # sorting the items of list_period in reverse order
    # newer months will be above
    list_period.sort(reverse=True)

    # list_period is now dynamically added as dropdown choice list to the SelectField
    form.period.choices = [item.strftime("%b-%y") for item in list_period]

    if form.validate_on_submit():
        period = form.period.data
        result = db.session.scalars(
            db.select(CoinsuranceBalances).filter(CoinsuranceBalances.period == period)
        )
        for item in result:
            db.session.delete(item)
        db.session.commit()
        flash(f"{period} has been deleted.")

    return render_template("coinsurance_balance_delete.html", form=form)
