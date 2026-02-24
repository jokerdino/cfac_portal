import re
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests
from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import String
from sqlalchemy_continuum import version_class
from werkzeug.utils import secure_filename

from app.funds.funds_model import FundBankStatement
from extensions import db
from set_view_permissions import admin_required

from . import coinsurance_bp
from .coinsurance_form import (
    CoinsuranceBankMandateForm,
    CoinsuranceCashCallForm,
    CoinsuranceForm,
    CoinsuranceTokenRequestIdForm,
    CoinsurerSelectForm,
    QueryForm,
    SettlementForm,
    SettlementUTRForm,
    UploadFileForm,
)
from .coinsurance_model import (
    Coinsurance,
    CoinsuranceBankMandate,
    CoinsuranceCashCall,
    CoinsuranceLog,
    CoinsuranceReceipts,
    CoinsuranceTokenRequestId,
    Remarks,
    Settlement,
)

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
    stmt = (
        db.select(Coinsurance.current_status, db.func.count(Coinsurance.current_status))
        .group_by(Coinsurance.current_status)
        .order_by(Coinsurance.current_status)
    )

    if current_user.user_type == "ro_user":
        stmt = stmt.where(Coinsurance.uiic_regional_code == current_user.ro_code)

    elif current_user.user_type == "oo_user":
        stmt = stmt.where(
            (Coinsurance.uiic_office_code == current_user.oo_code)
            & (Coinsurance.uiic_regional_code == current_user.ro_code)
        )

    elif current_user.user_type in ["admin", "coinsurance_hub_user"]:
        stmt = stmt
    else:
        abort(404)

    query = db.session.execute(stmt)
    case_paid = db.case(
        (
            Settlement.type_of_transaction == "Paid",
            Settlement.settled_amount,
        ),
        else_=0,
    ).label("Paid")
    case_received = db.case(
        (
            Settlement.type_of_transaction == "Received",
            Settlement.settled_amount,
        ),
        else_=0,
    ).label("Received")
    settlement_query = db.session.execute(
        db.select(
            Settlement.month,
            db.func.sum(case_paid),
            db.func.sum(case_received),
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
    def apply_filters(stmt, created_after=None, search=None):
        stmt = stmt.where(FundBankStatement.flag_description == "COINSURANCE")
        if created_after:
            created_after = datetime.fromisoformat(created_after)
            stmt = stmt.where(FundBankStatement.date_created_date > created_after)

        if search:
            search_terms = search.strip().split()  # split by spaces
            for term in search_terms:
                stmt = stmt.where(
                    db.or_(
                        db.cast(FundBankStatement.book_date, String).like(f"%{term}%"),
                        FundBankStatement.description.ilike(f"%{term}%"),
                        db.cast(FundBankStatement.credit, String).like(f"%{term}%"),
                        FundBankStatement.reference_no.ilike(f"%{term}%"),
                    )
                )
        return stmt

    created_after = request.args.get("created_after")

    entries_count = db.session.scalar(
        apply_filters(
            db.select(db.func.count(FundBankStatement.id)), created_after, None
        )
    )

    # search filter
    search = request.args.get("search[value]")

    stmt = apply_filters(
        db.select(
            db.func.to_char(FundBankStatement.value_date, "YYYY-MM-DD").label(
                "value_date"
            ),
            FundBankStatement.description,
            FundBankStatement.credit,
            FundBankStatement.reference_no,
        ).order_by(FundBankStatement.id.desc()),
        created_after,
        search,
    )
    total_filtered = db.session.scalar(
        apply_filters(
            db.select(db.func.count(FundBankStatement.id)), created_after, search
        )
    )

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
    entries = stmt.offset(start).limit(length)

    result = db.session.execute(entries).mappings()
    # response
    return {
        "data": [dict(entry) for entry in result],
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
    upload_root = current_app.config.get("UPLOAD_FOLDER_PATH")
    folder_path = upload_root / "coinsurance" / folder_name

    folder_path.mkdir(parents=True, exist_ok=True)
    file = form.data.get(field)

    if file:
        filename = secure_filename(file.filename)
        file_extension = Path(filename).suffix
        document_filename = f"{document_type}_{datetime.now().strftime('%d%m%Y %H%M%S')}{file_extension}"

        file.save(folder_path / document_filename)

        setattr(model_object, document_type, document_filename)


@coinsurance_bp.route("/add_entry", methods=["POST", "GET"])
@login_required
def add_coinsurance_entry():
    form = CoinsuranceForm()
    if current_user.user_type == "oo_user":
        form.uiic_regional_code.data = current_user.ro_code
        form.uiic_office_code.data = current_user.oo_code
    elif current_user.user_type == "ro_user":
        form.uiic_regional_code.data = current_user.ro_code

    if form.validate_on_submit():
        coinsurance = Coinsurance()
        form.populate_obj(coinsurance)

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

        # committing now to generate coinsurance.id for remarks object
        db.session.commit()

        if form_remarks:
            remarks = Remarks(
                coinsurance_id=coinsurance.id,
                remarks=form_remarks,
            )
            db.session.add(remarks)
        db.session.commit()

        return redirect(
            url_for("coinsurance.view_coinsurance_entry", coinsurance_id=coinsurance.id)
        )

    return render_template(
        "edit_coinsurance_entry.html",
        form=form,
        enable_save_button=True,
        ro_list=ro_list,
    )


def enable_button(current_user, coinsurance_entry) -> bool:
    bool_enable_button: bool = False
    settlement = db.session.scalar(
        db.select(Settlement).where(
            Settlement.utr_number == coinsurance_entry.utr_number
        )
    )

    if current_user.user_type in ["admin", "coinsurance_hub_user"]:
        if not coinsurance_entry.current_status == "Settled":
            bool_enable_button = True
        elif not settlement:
            bool_enable_button = True

    elif current_user.user_type in ["ro_user", "oo_user"]:
        if coinsurance_entry.current_status == "Needs clarification from RO or OO":
            bool_enable_button = True
    return bool_enable_button


@coinsurance_bp.route("/view/<int:coinsurance_id>/")
@login_required
def view_coinsurance_entry(coinsurance_id):
    coinsurance = db.get_or_404(Coinsurance, coinsurance_id)
    coinsurance.require_access(current_user)
    remarks = db.session.scalars(
        db.select(Remarks)
        .where(Remarks.coinsurance_id == coinsurance_id)
        .order_by(Remarks.time_of_remark)
    ).all()
    settlement = db.session.scalars(
        db.select(Settlement).where(Settlement.utr_number == coinsurance.utr_number)
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
    "/<string:requirement>/<int:coinsurance_id>/", methods=["POST", "GET"]
)
@login_required
def download_document(requirement, coinsurance_id):
    coinsurance = db.get_or_404(Coinsurance, coinsurance_id)
    coinsurance.require_access(current_user)
    if requirement == "confirmation":
        stored_filename = coinsurance.confirmation
    elif requirement == "statement":
        stored_filename = coinsurance.statement
    elif requirement == "ri_confirmation":
        stored_filename = coinsurance.ri_confirmation
    else:
        return "No such requirement"
    stored_path = Path(stored_filename)
    file_extension = stored_path.suffix
    if coinsurance.net_amount < 0:
        amount_string = f"receivable {coinsurance.net_amount * -1}"
    else:
        amount_string = f"payable {coinsurance.net_amount}"
    download_name = f"{coinsurance.type_of_transaction} {requirement} - {coinsurance.uiic_office_code} - {coinsurance.follower_company_name} {amount_string}{file_extension}"

    folder_name = f"{requirement}s"
    base_directory = (
        current_app.config.get("UPLOAD_FOLDER_PATH") / "coinsurance" / folder_name
    )
    return send_from_directory(
        directory=base_directory,
        path=stored_path.name,
        as_attachment=True,
        download_name=download_name,
    )


@coinsurance_bp.route("/settlements/<int:settlement_id>/", methods=["POST", "GET"])
@login_required
def download_settlements(settlement_id):
    settlement = db.get_or_404(Settlement, settlement_id)

    file_extension = settlement.file_settlement_file.rsplit(".", 1)[1]
    path = settlement.file_settlement_file
    filename = f"{settlement.name_of_company} - {settlement.type_of_transaction} - {settlement.utr_number}.{file_extension}"
    base_directory = (
        current_app.config.get("UPLOAD_FOLDER_PATH") / "coinsurance" / "settlements"
    )
    return send_from_directory(
        directory=base_directory,
        path=path,
        as_attachment=True,
        download_name=filename,
    )


def update_utr_choices(coinsurance, form):
    utr_list = db.session.scalars(
        db.select(Settlement)
        .where(coinsurance.follower_company_name == Settlement.name_of_company)
        .order_by(Settlement.date_of_settlement.desc())
    ).all()

    form.utr_number.choices = [(utr.utr_number, str(utr)) for utr in utr_list]


@coinsurance_bp.route("/edit/<int:coinsurance_id>/", methods=["POST", "GET"])
@login_required
def edit_coinsurance_entry(coinsurance_id):
    coinsurance = db.get_or_404(Coinsurance, coinsurance_id)
    coinsurance.require_access(current_user)
    form = CoinsuranceForm(obj=coinsurance)

    if form.data["boolean_reinsurance_involved"]:
        from wtforms.validators import Optional

        if coinsurance.ri_confirmation:
            form.ri_confirmation_file.validators = [Optional()]

    if not enable_button(current_user, coinsurance):
        flash("Unable to submit data. Please try again later.")
    elif form.validate_on_submit():
        form.populate_obj(coinsurance)

        if current_user.user_type in ["oo_user", "ro_user"]:
            coinsurance.current_status = "To be reviewed by coinsurance hub"
        if current_user.user_type in ["coinsurance_hub_user", "admin"]:
            coinsurance.current_status = form.data["current_status"]

        if coinsurance.current_status != "Settled":
            coinsurance.utr_number = None

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

        # db.session.commit()

        if form.data["remarks"]:
            remarks = Remarks(
                coinsurance_id=coinsurance.id,
                remarks=form.data["remarks"],
            )
            db.session.add(remarks)
        db.session.commit()

        # coinsurance_log = CoinsuranceLog(
        #     **asdict(coinsurance),
        #     coinsurance_id=coinsurance.id,
        # )
        # db.session.add(coinsurance_log)
        # db.session.commit()

        return redirect(
            url_for("coinsurance.view_coinsurance_entry", coinsurance_id=coinsurance_id)
        )
    remarks = db.session.scalars(
        db.select(Remarks)
        .where(Remarks.coinsurance_id == coinsurance_id)
        .order_by(Remarks.time_of_remark.asc())
    ).all()

    change_status = (
        True if current_user.user_type in ["admin", "coinsurance_hub_user"] else False
    )
    update_settlement = False

    enable_save_button = enable_button(current_user, coinsurance)
    if (
        current_user.user_type in ["admin", "coinsurance_hub_user"]
        and coinsurance.current_status == "Settled"
    ):
        # if coinsurance.current_status == "Settled":
        if not coinsurance.utr_number:
            # if not Settlement.query.filter(
            #     Settlement.utr_number == coinsurance.utr_number
            # ).first():
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
        # edit=True,
        ro_list=ro_list,
    )


# def select_coinsurers(query, form):
#     """Obsolete function. Use select_coinsurers_v2 instead."""
#     coinsurer_choices = query.order_by(
#         Coinsurance.follower_company_name.asc()
#     ).distinct(Coinsurance.follower_company_name)
#     form.coinsurer_name.choices = ["View all"] + [
#         x.follower_company_name for x in coinsurer_choices
#     ]

#     if form.validate_on_submit() and form.filter_coinsurer.data:
#         coinsurer_choice: str = form.data["coinsurer_name"]
#         if coinsurer_choice != "View all":
#             query = query.filter(Coinsurance.follower_company_name == coinsurer_choice)
#     return query


def select_coinsurers_v2(stmt, form):
    subq = stmt.subquery()
    coinsurer_choices = db.session.scalars(
        db.select(db.func.distinct(subq.c.follower_company_name))
        .select_from(subq)
        .order_by(subq.c.follower_company_name.asc())
    ).all()
    form.coinsurer_name.choices = ["View all"] + coinsurer_choices

    if form.validate_on_submit() and form.filter_coinsurer.data:
        coinsurer_choice = form.data["coinsurer_name"]
        if coinsurer_choice != "View all":
            stmt = stmt.where(Coinsurance.follower_company_name == coinsurer_choice)
    return stmt


@coinsurance_bp.route("/list/Settled/exception", methods=["POST", "GET"])
@login_required
@admin_required
def list_settled_entries_without_utr():
    form_select_coinsurer = CoinsurerSelectForm()
    stmt = (
        db.select(Coinsurance)
        .where(Coinsurance.utr_number.is_(None))
        .where(Coinsurance.current_status == "Settled")
    ).order_by(Coinsurance.follower_company_name.desc())

    stmt = select_coinsurers_v2(stmt, form_select_coinsurer)
    query = db.session.scalars(stmt)
    return render_template(
        "view_all_coinsurance_entries.html",
        coinsurance_entries=query,
        update_settlement=False,
        form_select_coinsurer=form_select_coinsurer,
        title="Settled entries without UTR number",
    )


@coinsurance_bp.route("/list/company/<string:coinsurer_name>/", methods=["POST", "GET"])
@login_required
def list_coinsurance_entries_by_coinsurer_name(coinsurer_name):
    form_select_coinsurer = CoinsurerSelectForm()

    stmt = (
        db.select(Coinsurance)
        .where(
            db.and_(
                Coinsurance.follower_company_name == coinsurer_name,
                Coinsurance.current_status != "No longer valid",
            )
        )
        .order_by(Coinsurance.follower_company_name)
    )

    if current_user.user_type == "ro_user":
        stmt = stmt.where(Coinsurance.uiic_regional_code == current_user.ro_code)

    elif current_user.user_type == "oo_user":
        stmt = stmt.where(
            db.and_(
                (Coinsurance.uiic_office_code == current_user.oo_code),
                (Coinsurance.uiic_regional_code == current_user.ro_code),
            )
        )

    stmt = select_coinsurers_v2(stmt, form_select_coinsurer)
    query = db.session.scalars(stmt).all()
    if current_user.user_type == "ro_user":
        custom_title = f" uploaded by RO {current_user.ro_code}"
    elif current_user.user_type == "oo_user":
        custom_title = f" uploaded by OO {current_user.oo_code}"
    else:
        custom_title = ""

    return render_template(
        "view_all_coinsurance_entries.html",
        coinsurance_entries=query,
        update_settlement=False,
        form_select_coinsurer=form_select_coinsurer,
        title=f"List of all coinsurance confirmations of {coinsurer_name} {custom_title}",
    )


@coinsurance_bp.route("/list/all", methods=["POST", "GET"])
@login_required
def list_coinsurance_entries():
    form_select_coinsurer = CoinsurerSelectForm()
    stmt = (
        db.select(Coinsurance)
        .where(Coinsurance.current_status != "No longer valid")
        .order_by(Coinsurance.follower_company_name.asc())
    )

    if current_user.user_type == "ro_user":
        stmt = stmt.where(Coinsurance.uiic_regional_code == current_user.ro_code)
    elif current_user.user_type == "oo_user":
        stmt = stmt.where(
            db.and_(
                Coinsurance.uiic_office_code == current_user.oo_code,
                Coinsurance.uiic_regional_code == current_user.ro_code,
            )
        )

    stmt = select_coinsurers_v2(stmt, form_select_coinsurer)
    query = db.session.scalars(stmt).all()
    if current_user.user_type == "ro_user":
        custom_title = f" uploaded by RO {current_user.ro_code}"
    elif current_user.user_type == "oo_user":
        custom_title = f" uploaded by OO {current_user.oo_code}"
    else:
        custom_title = ""

    return render_template(
        "view_all_coinsurance_entries.html",
        coinsurance_entries=query,
        update_settlement=False,
        form_select_coinsurer=form_select_coinsurer,
        title=f"List of all coinsurance confirmations{custom_title}",
    )


@coinsurance_bp.route("/list/status/<string:status>/", methods=["POST", "GET"])
@login_required
def list_coinsurance_entries_by_status(status):
    form_select_coinsurer = CoinsurerSelectForm()
    form = SettlementUTRForm()

    stmt = (
        db.select(Coinsurance)
        .where(Coinsurance.current_status == status)
        .order_by(Coinsurance.follower_company_name.asc())
    )

    if current_user.user_type == "ro_user":
        stmt = stmt.where(Coinsurance.uiic_regional_code == current_user.ro_code)

    elif current_user.user_type == "oo_user":
        stmt = stmt.where(
            (Coinsurance.uiic_office_code == current_user.oo_code)
            & (Coinsurance.uiic_regional_code == current_user.ro_code)
        )

    stmt = select_coinsurers_v2(stmt, form_select_coinsurer)
    query = db.session.scalars(stmt).all()
    update_settlement = False
    if (
        current_user.user_type in ["admin", "coinsurance_hub_user"]
        and status == "To be settled"
    ):
        update_settlement = True
        subq = stmt.subquery()
        coinsurer_choices = db.session.scalars(
            db.select(subq.c.follower_company_name).distinct().select_from(subq)
        ).all()

        utr_list = db.session.scalars(
            db.select(Settlement).order_by(Settlement.date_of_settlement.desc())
        ).all()

        form.utr_number.choices = [
            (utr.utr_number, str(utr))
            for utr in utr_list
            if utr.name_of_company in coinsurer_choices
        ]

        if form.validate_on_submit() and form.update_settlement.data:
            form_coinsurance_keys = request.form.getlist("coinsurance_keys")
            form_coinsurance_keys = [int(i) for i in form_coinsurance_keys]
            form_utr_number = form.data["utr_number"]

            settlement_company_name = db.session.scalar(
                db.select(Settlement.name_of_company).where(
                    Settlement.utr_number == form_utr_number
                )
            )

            # looping through objects and updating manually for capturing version history
            # through sqlalchemy-continuum

            stmt = db.select(Coinsurance).where(
                Coinsurance.id.in_(form_coinsurance_keys),
                Coinsurance.follower_company_name == settlement_company_name,
            )

            for row in db.session.scalars(stmt):
                row.utr_number = form_utr_number
                row.current_status = "Settled"

            db.session.commit()

            return redirect(
                url_for(
                    "coinsurance.list_settled_coinsurance_entries",
                    utr_number=form_utr_number,
                )
            )

    return render_template(
        "view_all_coinsurance_entries.html",
        coinsurance_entries=query,
        update_settlement=update_settlement,
        status=status,
        form_select_coinsurer=form_select_coinsurer,
        form=form,
    )


@coinsurance_bp.route("/list/settlements/<string:utr_number>/", methods=["POST", "GET"])
@login_required
def list_settled_coinsurance_entries(utr_number):
    form_select_coinsurer = CoinsurerSelectForm()
    coinsurance_entries = db.select(Coinsurance).where(
        Coinsurance.utr_number == utr_number
    )
    stmt = select_coinsurers_v2(coinsurance_entries, form_select_coinsurer)
    query = db.session.scalars(stmt).all()
    return render_template(
        "view_all_coinsurance_entries.html",
        coinsurance_entries=query,
        update_settlement=False,
        form_select_coinsurer=form_select_coinsurer,
    )


@coinsurance_bp.route("/settlements/")
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


@coinsurance_bp.route("/settlements/add", methods=["POST", "GET"])
@login_required
@admin_required
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


@coinsurance_bp.route("/log/<int:coinsurance_id>/")
@login_required
@admin_required
def view_coinsurance_log(coinsurance_id):
    CoinsuranceVersion = version_class(Coinsurance)
    log = db.session.scalars(
        db.select(CoinsuranceLog)
        .where(CoinsuranceLog.coinsurance_id == coinsurance_id)
        .order_by(CoinsuranceLog.id)
    )

    version_log = db.session.scalars(
        db.select(CoinsuranceVersion)
        .where(CoinsuranceVersion.id == coinsurance_id)
        .order_by(CoinsuranceVersion.transaction_id)
    )
    log_column_names = [column.name for column in Coinsurance.__table__.columns]
    version_column_names = [
        column.name for column in CoinsuranceVersion.__table__.columns
    ]
    return render_template(
        "view_coinsurance_log.html",
        log=log,
        column_names=log_column_names,
        version_column_names=version_column_names,
        version_log=version_log,
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


@coinsurance_bp.route("/cash_call/view/<int:cash_call_key>/")
@login_required
def view_cash_call(cash_call_key):
    cash_call = db.get_or_404(CoinsuranceCashCall, cash_call_key)
    return render_template("cash_call_view.html", cash_call=cash_call)


@coinsurance_bp.route("/cash_call/list/<string:status>/")
@login_required
def list_cash_calls(status="all"):
    cash_call_list = db.session.scalars(db.select(CoinsuranceCashCall))

    return render_template("cash_call_list.html", list=cash_call_list)


@coinsurance_bp.route("/cash_call/edit/<int:cash_call_key>/", methods=["POST", "GET"])
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


# # bulk upload cash calls
# @coinsurance_bp.route("/cash_call/bulk_upload", methods=["POST", "GET"])
# @login_required
# def bulk_upload_cash_call():
#     form = UploadFileForm()
#     if form.validate_on_submit():
#         df = pd.read_excel(form.data["file_upload"])

#         df["created_on"] = datetime.now()
#         df["created_by"] = current_user.username

#         df.to_sql(
#             "coinsurance_cash_call",
#             db.engine,
#             if_exists="append",
#             index=False,
#         )
#         flash("Coinsurance cash call details have been uploaded successfully.")
#     return render_template(
#         "coinsurance_upload_file_template.html",
#         form=form,
#         title="Bulk upload cash call details",
#     )


# bulk upload settlements
@coinsurance_bp.route("/settlements/bulk_upload", methods=["POST", "GET"])
@login_required
@admin_required
def bulk_upload_settlements():
    form = UploadFileForm()
    form.file_upload.render_kw.update({"accept": ".csv"})
    if form.validate_on_submit():
        df_settlement = pd.read_csv(form.data["file_upload"])
        df_settlement.columns = df_settlement.columns.str.lower()
        db.session.execute(
            db.insert(Settlement), df_settlement.to_dict(orient="records")
        )
        db.session.commit()

        flash("Settlement details have been uploaded successfully.")
    return render_template(
        "coinsurance_upload_file_template.html",
        form=form,
        title="Bulk upload settlement details (CSV)",
    )


@coinsurance_bp.route("/query/", methods=["POST", "GET"])
@login_required
def query_coinsurance_entries():
    form = QueryForm()
    if form.validate_on_submit():
        status_list = form.status.data
        coinsurers_list = form.coinsurer_name.data
        coinsurance_entries = db.select(Coinsurance)
        if status_list:
            coinsurance_entries = coinsurance_entries.where(
                Coinsurance.current_status.in_(status_list)
            )
        if coinsurers_list:
            coinsurance_entries = coinsurance_entries.where(
                Coinsurance.follower_company_name.in_(coinsurers_list)
            )

        form_select_coinsurer = CoinsurerSelectForm()
        stmt = select_coinsurers_v2(coinsurance_entries, form_select_coinsurer)
        query = db.session.scalars(stmt).all()
        return render_template(
            "view_all_coinsurance_entries.html",
            coinsurance_entries=query,
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
    base_directory = (
        current_app.config.get("UPLOAD_FOLDER_PATH") / "coinsurance" / "bank_mandates"
    )
    return send_from_directory(
        directory=base_directory,
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

    pending_filter = db.or_(
        CoinsuranceTokenRequestId.jv_passed.is_(False),
        CoinsuranceTokenRequestId.jv_passed.is_(None),
    )
    pending_token_ids = db.session.scalars(
        db.select(CoinsuranceTokenRequestId).where(pending_filter)
    )
    pending_count = db.session.scalar(
        db.select(db.func.count(CoinsuranceTokenRequestId.id)).where(pending_filter)
    )

    return render_template(
        "token_id_list.html",
        token_ids=token_ids,
        pending_token_ids=pending_token_ids,
        pending_count=pending_count,
    )


@coinsurance_bp.route("/token_id/download_jv/")
@login_required
@admin_required
def token_id_download_jv():
    case_ho_gl = db.case(
        (
            CoinsuranceTokenRequestId.type_of_amount == "Payable",
            "CR",
        ),
        else_="DR",
    ).label("DR/CR")
    case_transfer_gl = db.case(
        (
            CoinsuranceTokenRequestId.type_of_amount == "Payable",
            "DR",
        ),
        else_="CR",
    ).label("DR/CR")
    pending_filter = db.or_(
        CoinsuranceTokenRequestId.jv_passed.is_(False),
        CoinsuranceTokenRequestId.jv_passed.is_(None),
    )
    ho_entries = db.select(
        db.literal("000100").label("Office Location"),
        CoinsuranceTokenRequestId.gl_code.label("GL Code"),
        db.literal("9000100").label("SL Code"),
        case_ho_gl,
        CoinsuranceTokenRequestId.amount.label("Amount"),
        CoinsuranceTokenRequestId.remarks.label("Remarks"),
    ).where(pending_filter)
    transfer_entries = db.select(
        db.literal("000100").label("Office Location"),
        CoinsuranceTokenRequestId.jv_gl_code.label("GL Code"),
        CoinsuranceTokenRequestId.jv_sl_code.label("SL Code"),
        case_transfer_gl,
        CoinsuranceTokenRequestId.amount.label("Amount"),
        CoinsuranceTokenRequestId.remarks.label("Remarks"),
    ).where(pending_filter)

    combined_stmt = db.union_all(ho_entries, transfer_entries)

    with db.engine.connect() as conn:
        df_token_jv = pd.read_sql(combined_stmt, conn)
    output = BytesIO()

    df_token_jv.to_excel(output, index=False)

    # Set the buffer position to the beginning
    output.seek(0)

    filename = f"token_id_jv_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"

    return send_file(output, as_attachment=True, download_name=filename)


@coinsurance_bp.route("/token_id/mark_as_completed/", methods=["POST"])
@login_required
@admin_required
def mark_token_ids_completed():
    selected_ids = request.form.getlist("selected_ids")
    selected_ids = [int(id) for id in selected_ids]
    if not selected_ids:
        flash("No rows selected", "warning")
        return redirect(url_for("coinsurance.token_id_list"))

    stmt = (
        db.update(CoinsuranceTokenRequestId)
        .where(CoinsuranceTokenRequestId.id.in_(selected_ids))
        .values({CoinsuranceTokenRequestId.jv_passed: True})
    )
    db.session.execute(stmt)
    db.session.commit()
    flash(f"{len(selected_ids)} rows marked as completed", "success")
    return redirect(url_for("coinsurance.token_id_list"))


@coinsurance_bp.route("/token_id/download/<int:key>/")
@login_required
@admin_required
def download_token_id_document(key):
    token_id = db.get_or_404(CoinsuranceTokenRequestId, key)
    base_directory = (
        current_app.config.get("UPLOAD_FOLDER_PATH")
        / "coinsurance"
        / "token_request_id"
    )
    return send_from_directory(
        directory=base_directory,
        path=token_id.upload_document,
        download_name=f"{token_id.company_name}_{token_id.type_of_amount}_{token_id.amount}.pdf",
        as_attachment=True,
    )


@coinsurance_bp.route("/to_be_settled/summary/")
@login_required
def company_wise_to_be_settled_summary():
    START_DATE = datetime(2026, 3, 1)
    net_expr = db.func.sum(
        db.func.coalesce(Coinsurance.payable_amount, 0)
        + db.func.coalesce(Coinsurance.int_ri_payable_amount, 0)
        - db.func.coalesce(Coinsurance.receivable_amount, 0)
        - db.func.coalesce(Coinsurance.int_ri_receivable_amount, 0)
    )
    query = (
        db.select(
            Coinsurance.follower_company_name,
            db.func.sum(db.func.coalesce(Coinsurance.payable_amount, 0)).label(
                "payable_amount"
            ),
            db.func.sum(db.func.coalesce(Coinsurance.receivable_amount, 0)).label(
                "receivable_amount"
            ),
            db.func.sum(db.func.coalesce(Coinsurance.int_ri_payable_amount, 0)).label(
                "ri_payable_amount"
            ),
            db.func.sum(
                db.func.coalesce(Coinsurance.int_ri_receivable_amount, 0)
            ).label("ri_receivable_amount"),
            db.case((net_expr > 0, net_expr), else_=0).label("net_payable"),
            db.case((net_expr < 0, db.func.abs(net_expr)), else_=0).label(
                "net_receivable"
            ),
        )
        .where(
            Coinsurance.date_created_date >= START_DATE,
            Coinsurance.current_status == "To be settled",
        )
        .group_by(Coinsurance.follower_company_name)
    )
    result = db.session.execute(query).mappings().all()

    return render_template("company_wise_to_be_settled_summary.html", result=result)


@coinsurance_bp.route(
    "/to_be_settled/company/<string:company>/", methods=["POST", "GET"]
)
@login_required
def to_be_settled_company_wise_details(company):
    START_DATE = datetime(2026, 3, 1)
    form_select_coinsurer = CoinsurerSelectForm()
    settlement_form = SettlementUTRForm()
    utr_list = db.session.scalars(
        db.select(Settlement).where(
            Settlement.name_of_company == company,
            Settlement.date_of_settlement >= START_DATE,
        )
    )
    settlement_form.utr_number.choices = [
        (utr.utr_number, str(utr)) for utr in utr_list
    ]

    query = (
        db.select(Coinsurance)
        .where(
            Coinsurance.follower_company_name == company,
            Coinsurance.date_created_date >= START_DATE,
            Coinsurance.current_status == "To be settled",
        )
        .order_by(Coinsurance.date_created_date)
    )
    result = db.session.execute(query).scalars().all()
    select_coinsurers_v2(query, form_select_coinsurer)

    if settlement_form.validate_on_submit() and settlement_form.update_settlement.data:
        selected_ids = request.form.getlist("coinsurance_keys")
        selected_ids = [int(i) for i in selected_ids]
        if not selected_ids:
            flash("No entries selected.", "warning")
            return redirect(
                url_for(
                    "coinsurance.to_be_settled_company_wise_details", company=company
                )
            )
        form_utr_number = settlement_form.utr_number.data
        if not form_utr_number:
            flash("No UTR numbers selected.", "warning")
            return redirect(
                url_for(
                    "coinsurance.to_be_settled_company_wise_details", company=company
                )
            )
        update_stmt = (
            db.update(Coinsurance)
            .where(Coinsurance.id.in_(selected_ids))
            .values(
                {
                    Coinsurance.current_status: "Settled",
                    Coinsurance.utr_number: form_utr_number,
                }
            )
        )
        db.session.execute(update_stmt)
        db.session.commit()
        flash(f"{len(selected_ids)} entries marked as settled.", "success")
        return redirect(
            url_for("coinsurance.to_be_settled_company_wise_details", company=company)
        )
    return render_template(
        "view_all_coinsurance_entries.html",
        coinsurance_entries=result,
        update_settlement=True,
        form_select_coinsurer=form_select_coinsurer,
        form=settlement_form,
        status="To be settled",
        title="List of coinsurance confirmations - ",
    )
