import os
import re

from datetime import datetime, timedelta
from dataclasses import asdict

import requests
import pandas as pd

from sqlalchemy import func, create_engine, case, String, cast

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

from utils import indian_number_format

from . import coinsurance_bp
from .coinsurance_form import (
    CoinsuranceForm,
    SettlementForm,
    SettlementUTRForm,
    CoinsurerSelectForm,
    CoinsuranceCashCallForm,
    UploadFileForm,
    QueryForm,
    CoinsuranceBankMandateForm,
    CoinsuranceTokenRequestIdForm,
)
from .coinsurance_model import (
    Coinsurance,
    CoinsuranceLog,
    Remarks,
    Settlement,
    CoinsuranceCashCall,
    CoinsuranceBankMandate,
    CoinsuranceReceipts,
    CoinsuranceTokenRequestId,
)


from app.funds.funds_model import FundBankStatement

from extensions import db

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
            Settlement.month,
            func.sum(case_paid),
            func.sum(case_received),
        )
        .group_by(
            Settlement.month,
        )
        .order_by(Settlement.month.desc())
    )

    return render_template(
        "coinsurance_home.html",
        dashboard=query,
        settlement_query=settlement_query,
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

    receipt_entries = []
    for receipt in receipts["data"]:
        receipt["transaction_code"] = re.findall(
            r"UII688COINS[a-zA-Z0-9]{1,6}\b", receipt["description"]
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
    # from extensions import db

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


def upload_document(model_object, form, field, document_type, folder_name):
    """
    Uploads a document to the folder specified by folder_name and saves the filename to the object.

    :param object: The object to save the filename to
    :param form: The form containing the file to upload
    :param field: The name of the field in the form containing the file to upload
    :param document_type: The type of document being uploaded (e.g. "statement", "confirmation")
    :param folder_name: The folder to save the document in
    """
    folder_path = os.path.join(
        current_app.config.get("UPLOAD_FOLDER"), "coinsurance", folder_name
    )
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    filename = secure_filename(form.data[field].filename)
    file_extension = filename.rsplit(".", 1)[1]
    document_filename = (
        f"{document_type}_{datetime.now().strftime('%d%m%Y %H%M%S')}.{file_extension}"
    )

    form.data[field].save(os.path.join(folder_path, document_filename))

    setattr(model_object, document_type, document_filename)


@coinsurance_bp.route("/add_entry", methods=["POST", "GET"])
@login_required
def add_coinsurance_entry():
    form = CoinsuranceForm()

    if form.validate_on_submit():
        coinsurance = Coinsurance()
        form.populate_obj(coinsurance)
        if current_user.user_type == "oo_user":
            coinsurance.uiic_regional_code = current_user.ro_code
            coinsurance.uiic_office_code = current_user.oo_code
        elif current_user.user_type == "ro_user":
            coinsurance.uiic_regional_code = current_user.ro_code

        if form.data["statement_file"]:
            upload_document(
                coinsurance, form, "statement_file", "statement", "statements"
            )
        if form.data["confirmation_file"]:
            upload_document(
                coinsurance, form, "confirmation_file", "confirmation", "confirmations"
            )
        if form["ri_confirmation_file"].data:
            upload_document(
                coinsurance,
                form,
                "ri_confirmation_file",
                "ri_confirmation",
                "ri_confirmations",
            )
        if current_user.user_type in ["admin", "coinsurance_hub_user"]:
            coinsurance.current_status = "To be settled"
        else:
            coinsurance.current_status = "To be reviewed by coinsurance hub"
        form_remarks = form.data["remarks"]
        db.session.add(coinsurance)
        db.session.commit()
        if form_remarks:
            remarks = Remarks(
                coinsurance_id=coinsurance.id,
                remarks=form_remarks,
            )
            db.session.add(remarks)
            db.session.commit()
        coinsurance_log = CoinsuranceLog(
            **asdict(coinsurance),
            coinsurance_id=coinsurance.id,
        )
        db.session.add(coinsurance_log)
        db.session.commit()
        return redirect(
            url_for("coinsurance.view_coinsurance_entry", coinsurance_id=coinsurance.id)
        )

    if current_user.user_type == "oo_user":
        form.uiic_regional_code.data = current_user.ro_code
        form.uiic_office_code.data = current_user.oo_code
    elif current_user.user_type == "ro_user":
        form.uiic_regional_code.data = current_user.ro_code

    return render_template(
        "edit_coinsurance_entry.html",
        form=form,
        enable_save_button=True,
        ro_list=ro_list,
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
        directory=f"{current_app.config.get('UPLOAD_FOLDER')}coinsurance/{requirement}s/",
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
        directory=f"{current_app.config.get('UPLOAD_FOLDER')}coinsurance/settlements/",
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
    form.utr_number.choices = [
        (
            utr_number,
            f"{name_of_company}-{utr_number} Rs. {indian_number_format(settled_amount)} on {date_of_settlement.strftime('%d/%m/%Y')} ({notes})",
        )
        for name_of_company, utr_number, date_of_settlement, settled_amount, notes in utr_list
    ]


@coinsurance_bp.route("/edit/<int:coinsurance_id>", methods=["POST", "GET"])
@login_required
def edit_coinsurance_entry(coinsurance_id):
    coinsurance = Coinsurance.query.get_or_404(coinsurance_id)
    form = CoinsuranceForm(obj=coinsurance)

    if form.data["boolean_reinsurance_involved"]:
        from wtforms.validators import Optional

        if coinsurance.ri_confirmation:
            form.ri_confirmation_file.validators = [Optional()]

    if not enable_button(current_user, coinsurance):
        flash("Unable to submit data. Please try again later.")
    elif form.validate_on_submit():
        form.populate_obj(coinsurance)
        if current_user.user_type == "oo_user":
            coinsurance.uiic_regional_code = current_user.ro_code
            coinsurance.uiic_office_code = current_user.oo_code
        elif current_user.user_type == "ro_user":
            coinsurance.uiic_regional_code = current_user.ro_code

        coinsurance.current_status = "To be reviewed by coinsurance hub"
        if current_user.user_type in ["coinsurance_hub_user", "admin"]:
            coinsurance.current_status = form.data["current_status"]

        if form.data["statement_file"]:
            upload_document(
                coinsurance, form, "statement_file", "statement", "statements"
            )

        if form.data["confirmation_file"]:
            upload_document(
                coinsurance, form, "confirmation_file", "confirmation", "confirmations"
            )

        if form.data["ri_confirmation_file"]:
            upload_document(
                coinsurance,
                form,
                "ri_confirmation_file",
                "ri_confirmation",
                "ri_confirmations",
            )

        if form.data["current_status"] == "Settled" and form.data["utr_number"]:
            coinsurance.utr_number = form.data["utr_number"]

        db.session.commit()

        if form.data["remarks"]:
            remarks = Remarks(
                coinsurance_id=coinsurance.id,
                remarks=form.data["remarks"],
            )
            db.session.add(remarks)
            db.session.commit()

        coinsurance_log = CoinsuranceLog(
            **asdict(coinsurance),
            coinsurance_id=coinsurance.id,
        )
        db.session.add(coinsurance_log)
        db.session.commit()

        return redirect(
            url_for("coinsurance.view_coinsurance_entry", coinsurance_id=coinsurance_id)
        )
    remarks = Remarks.query.filter(Remarks.coinsurance_id == coinsurance_id)

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
    )


@coinsurance_bp.route("/list/<string:coinsurer_name>/", methods=["POST", "GET"])
@login_required
def list_coinsurance_entries_by_coinsurer_name(coinsurer_name):
    form_select_coinsurer = CoinsurerSelectForm()

    coinsurance_entries = db.session.query(Coinsurance).filter(
        Coinsurance.follower_company_name == coinsurer_name
    )

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
        if status in ["To be settled"]:
            coinsurer_choices = coinsurance_entries.distinct(
                Coinsurance.follower_company_name
            )
            list_coinsurer_choices = [
                x.follower_company_name for x in coinsurer_choices
            ]

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

            if form.validate_on_submit() and form.update_settlement.data:
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

                        coinsurance_log = CoinsuranceLog(
                            **asdict(coinsurance), coinsurance_id=coinsurance.id
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
            )
        else:
            return render_template(
                "view_all_coinsurance_entries.html",
                coinsurance_entries=coinsurance_entries,
                update_settlement=True,
                status=status,
                form_select_coinsurer=form_select_coinsurer,
            )
    else:
        return render_template(
            "view_all_coinsurance_entries.html",
            coinsurance_entries=coinsurance_entries,
            update_settlement=False,
            status=status,
            form_select_coinsurer=form_select_coinsurer,
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
    )


@coinsurance_bp.route("/settlements/list")
@login_required
def list_settlement_entries():
    settlement_entries = db.session.scalars(db.select(Settlement))

    return render_template(
        "list_settlement_entries.html", settlement_entries=settlement_entries
    )


@coinsurance_bp.route("/settlements/view/<int:settlement_id>/")
@login_required
def view_settlement_entry(settlement_id):
    settlement = db.get_or_404(Settlement, settlement_id)
    return render_template("view_settlement_entry.html", settlement=settlement)


@coinsurance_bp.route("/settlements/add_settlement_data/", methods=["POST", "GET"])
@login_required
def add_settlement_data():
    form = SettlementForm()
    if form.validate_on_submit():
        settlement = Settlement()
        form.populate_obj(settlement)
        db.session.add(settlement)
        if form.data["settlement_file"]:
            upload_document(
                settlement,
                form,
                "settlement_file",
                "file_settlement_file",
                "settlements",
            )

        db.session.commit()

        return redirect(
            url_for("coinsurance.view_settlement_entry", settlement_id=settlement.id)
        )
    return render_template("add_settlement_entry.html", form=form)


@coinsurance_bp.route("/settlements/edit/<int:settlement_id>/", methods=["POST", "GET"])
@login_required
@admin_required
def edit_settlement_entry(settlement_id):
    settlement = db.get_or_404(Settlement, settlement_id)
    form = SettlementForm(obj=settlement)
    if form.validate_on_submit():
        form.populate_obj(settlement)
        if form.data["settlement_file"]:
            upload_document(
                settlement,
                form,
                "settlement_file",
                "file_settlement_file",
                "settlements",
            )

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
    log = CoinsuranceLog.query.filter(
        CoinsuranceLog.coinsurance_id == coinsurance_id
    ).order_by(CoinsuranceLog.id)
    column_names = CoinsuranceLog.query.statement.columns.keys()
    return render_template(
        "view_coinsurance_log.html", log=log, column_names=column_names
    )


@coinsurance_bp.route("/cash_call/add", methods=["POST", "GET"])
@login_required
def add_cash_call():
    form = CoinsuranceCashCallForm()

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
    cash_call = db.get_or_404(CoinsuranceCashCall, cash_call_key)
    return render_template("cash_call_view.html", cash_call=cash_call)


@coinsurance_bp.route("/cash_call/list/<string:status>")
@login_required
def list_cash_calls(status="all"):
    list = db.session.scalars(db.select(CoinsuranceCashCall))

    return render_template("cash_call_list.html", list=list)


@coinsurance_bp.route("/cash_call/edit/<int:cash_call_key>", methods=["POST", "GET"])
@login_required
def edit_cash_call(cash_call_key):
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
        status_list = form.status.data
        coinsurers_list = form.coinsurer_name.data
        coinsurance_entries = db.session.query(Coinsurance)
        if status_list:
            coinsurance_entries = coinsurance_entries.filter(
                Coinsurance.current_status.in_(status_list)
            )
        if coinsurers_list:
            coinsurance_entries = coinsurance_entries.filter(
                Coinsurance.follower_company_name.in_(coinsurers_list)
            )

        form_select_coinsurer = CoinsurerSelectForm()
        coinsurance_entries = select_coinsurers(
            coinsurance_entries, form_select_coinsurer
        )

        return render_template(
            "view_all_coinsurance_entries.html",
            coinsurance_entries=coinsurance_entries,
            update_settlement=False,
            form_select_coinsurer=form_select_coinsurer,
            title="Results of query",
        )

    return render_template("query_coinsurance_entries.html", form=form)


@coinsurance_bp.route("/bank_mandate/add/", methods=["POST", "GET"])
@login_required
@admin_required
def add_bank_mandate():
    form = CoinsuranceBankMandateForm()
    if form.validate_on_submit():
        bank_mandate = CoinsuranceBankMandate()
        form.populate_obj(bank_mandate)
        if form.data["bank_mandate_file"]:
            upload_document(
                bank_mandate, form, "bank_mandate_file", "bank_mandate", "bank_mandates"
            )

        db.session.add(bank_mandate)
        db.session.commit()

        return redirect(url_for("coinsurance.list_bank_mandates"))
    return render_template("bank_mandate_add.html", form=form, title="Add bank mandate")


@coinsurance_bp.route("/bank_mandate/edit/<int:key>/", methods=["POST", "GET"])
@login_required
@admin_required
def edit_bank_mandate(key):
    bank_mandate = db.get_or_404(CoinsuranceBankMandate, key)
    form = CoinsuranceBankMandateForm(obj=bank_mandate)

    if form.validate_on_submit():
        form.populate_obj(bank_mandate)

        if form.data["bank_mandate_file"]:
            upload_document(
                bank_mandate, form, "bank_mandate_file", "bank_mandate", "bank_mandates"
            )

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
    bank_mandate = db.get_or_404(CoinsuranceBankMandate, key)
    return send_from_directory(
        directory=f"{current_app.config.get('UPLOAD_FOLDER')}coinsurance/bank_mandates/",
        path=bank_mandate.bank_mandate,
        download_name=f"{bank_mandate.company_name}_{bank_mandate.office_code}_{bank_mandate.bank_name}_{bank_mandate.bank_account_number[-5:]}.pdf",
        as_attachment=True,
    )


@coinsurance_bp.route("/bank_mandate/")
@login_required
def list_bank_mandates():
    bank_mandates = db.session.scalars(db.select(CoinsuranceBankMandate))

    return render_template("bank_mandate_list.html", bank_mandates=bank_mandates)


@coinsurance_bp.route("/token_id/add/", methods=["POST", "GET"])
@login_required
@admin_required
def token_id_add():
    form = CoinsuranceTokenRequestIdForm()
    if form.validate_on_submit():
        token_id = CoinsuranceTokenRequestId()
        form.populate_obj(token_id)
        db.session.add(token_id)
        if form.data["upload_document_file"]:
            upload_document(
                token_id,
                form,
                "upload_document_file",
                "upload_document",
                "token_request_id",
            )
        db.session.commit()
        return redirect(url_for("coinsurance.token_id_list"))
    return render_template(
        "token_id_edit.html", form=form, title="Add new token request ID details"
    )


@coinsurance_bp.route("/token_id/edit/<int:key>/", methods=["POST", "GET"])
@login_required
@admin_required
def token_id_edit(key):
    token_id = db.get_or_404(CoinsuranceTokenRequestId, key)
    form = CoinsuranceTokenRequestIdForm(obj=token_id)
    if form.validate_on_submit():
        form.populate_obj(token_id)
        if form.data["upload_document_file"]:
            upload_document(
                token_id,
                form,
                "upload_document_file",
                "upload_document",
                "token_request_id",
            )
        db.session.commit()
        return redirect(url_for("coinsurance.token_id_list"))
    return render_template(
        "token_id_edit.html",
        form=form,
        token_id=token_id,
        title="Edit token request ID details",
    )


@coinsurance_bp.route("/token_id/")
@login_required
@admin_required
def token_id_list():
    token_ids = db.session.scalars(db.select(CoinsuranceTokenRequestId))
    return render_template("token_id_list.html", token_ids=token_ids)


@coinsurance_bp.route("/token_id/download/<int:key>/")
@login_required
def download_token_id_document(key):
    token_id = db.get_or_404(CoinsuranceTokenRequestId, key)
    return send_from_directory(
        directory=f"{current_app.config.get('UPLOAD_FOLDER')}coinsurance/token_request_id/",
        path=token_id.upload_document,
        download_name=f"{token_id.company_name}_{token_id.type_of_amount}_{token_id.amount}.pdf",
        as_attachment=True,
    )
