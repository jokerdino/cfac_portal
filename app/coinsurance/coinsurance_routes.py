from datetime import datetime
import pandas as pd
from sqlalchemy import func, distinct, select, create_engine

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user
from werkzeug.utils import secure_filename

from app.coinsurance import coinsurance_bp
from app.coinsurance.coinsurance_form import (
    CoinsuranceForm,
    SettlementForm,
    SettlementUTRForm,
    CoinsuranceBalanceQueryForm,
    CoinsurerSelectForm,
)
from app.coinsurance.coinsurance_model import (
    Coinsurance,
    Coinsurance_log,
    Remarks,
    Settlement,
    CoinsuranceBalances,
)

from app.tickets.tickets_routes import humanize_datetime


@coinsurance_bp.route("/")
def home_page():
    from server import db

    if current_user.user_type == "ro_user":
        query = (
            Coinsurance.query.filter(
                Coinsurance.uiic_regional_code == current_user.oo_code
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
                Coinsurance.uiic_office_code == current_user.oo_code
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

    settlement_query = (
        db.session.query(
            func.date_trunc("month", Settlement.date_of_settlement),
            func.date_trunc("year", Settlement.date_of_settlement),
            Settlement.type_of_transaction,
            func.sum(Settlement.settled_amount),
        )
        .group_by(
            Settlement.type_of_transaction,
            func.date_trunc("month", Settlement.date_of_settlement),
            func.date_trunc("year", Settlement.date_of_settlement),
        )
        .order_by(
            func.date_trunc("month", Settlement.date_of_settlement).desc(),
            func.date_trunc("year", Settlement.date_of_settlement).desc(),
        )
    )
    return render_template(
        "coinsurance_home.html", dashboard=query, settlement_query=settlement_query
    )


@coinsurance_bp.route("/add_entry", methods=["POST", "GET"])
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
            form.statement.data.save("statements/" + statement_filename)
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
            form.confirmation.data.save("confirmations/" + confirmation_filename)
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
                "ri_confirmations/" + ri_confirmation_filename
            )
        else:
            ri_confirmation_filename = None
        current_status = "To be reviewed by coinsurance hub"
        form_remarks = form.data["remarks"]
        coinsurance = Coinsurance(
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
            insured_name=name_of_insured,
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
def view_coinsurance_entry(coinsurance_id):
    coinsurance = Coinsurance.query.get_or_404(coinsurance_id)
    remarks = Remarks.query.filter(Remarks.coinsurance_id == coinsurance_id)
    settlement = Settlement.query.filter(
        Settlement.utr_number == coinsurance.utr_number
    ).all()

    enable_edit_button = enable_button(current_user, coinsurance)
    # commented out and code moved to function enable_button on 17.03.2024
    # enable_edit_button = False
    # if current_user.user_type in ["admin", "coinsurance_hub_user"]:
    #     if coinsurance.current_status != "Settled":
    #         enable_edit_button = True
    #     elif coinsurance.current_status == "Settled":
    #         if Settlement.query.filter(
    #             Settlement.utr_number == coinsurance.utr_number
    #         ).first():
    #             enable_edit_button = False
    #         else:
    #             enable_edit_button = True
    # elif current_user.user_type in ["oo_user", "ro_user"]:
    #     if coinsurance.current_status == "Needs clarification from RO or OO":
    #         enable_edit_button = True
    return render_template(
        "view_coinsurance_entry.html",
        coinsurance=coinsurance,
        remarks=remarks,
        settlement=settlement,
        enable_edit_button=enable_edit_button,
        humanize_datetime=humanize_datetime,
    )


@coinsurance_bp.route(
    "/<string:requirement>/<int:coinsurance_id>", methods=["POST", "GET"]
)
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
        directory=f"{requirement}s/",
        path=path,
        as_attachment=True,
        download_name=filename,
    )


@coinsurance_bp.route("/settlements/<int:settlement_id>", methods=["POST", "GET"])
def download_settlements(settlement_id):
    settlement = Settlement.query.get_or_404(settlement_id)

    file_extension = settlement.file_settlement_file.rsplit(".", 1)[1]
    path = settlement.file_settlement_file
    filename = f"{settlement.name_of_company} - {settlement.type_of_transaction} - {settlement.utr_number}.{file_extension}"
    return send_from_directory(
        directory="settlements/",
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
        )
        .distinct()
    )
    form.settlement.choices = [
        (
            utr_number,
            f"{name_of_company}-{utr_number} Rs. {settled_amount} on {date_of_settlement.strftime('%d/%m/%Y')}",
        )
        for name_of_company, utr_number, date_of_settlement, settled_amount in utr_list
    ]


@coinsurance_bp.route("/edit/<int:coinsurance_id>", methods=["POST", "GET"])
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
        payable_amount = form.data["payable_amount"]
        receivable_amount = form.data["receivable_amount"]

        request_id = form.data["request_id"]
        current_status = "To be reviewed by coinsurance hub"
        if current_user.user_type in ["coinsurance_hub_user", "admin"]:
            current_status = form.data["current_status"]

        type_of_transaction = form.data["type_of_transaction"]
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
            form.statement.data.save("statements/" + statement_filename)
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
            form.confirmation.data.save("confirmations/" + confirmation_filename)
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
                "ri_confirmations/" + ri_confirmation_filename
            )
            coinsurance.ri_confirmation = ri_confirmation_filename

        if form.data["current_status"] == "Settled" and form.data["settlement"]:
            utr_number = form.data["settlement"]
            coinsurance.utr_number = utr_number

        coinsurance.uiic_regional_code = regional_office_code
        coinsurance.uiic_office_code = oo_code
        coinsurance.follower_company_name = coinsurer_name
        coinsurance.follower_office_code = coinsurer_office_code

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

    #        commented out since code moved to function enable_button on 17.03.2024
    # enable_save_button = False
    # if current_user.user_type in ["admin", "coinsurance_hub_user"]:
    #     if coinsurance.current_status != "Settled":
    #         # change_status = True
    #         enable_save_button = True
    #     elif coinsurance.current_status == "Settled":
    #         # change_status = True
    #
    #         if not Settlement.query.filter(
    #             Settlement.utr_number == coinsurance.utr_number
    #         ).first():
    #             update_settlement = True
    #             enable_save_button = True
    #             update_utr_choices(coinsurance, form)
    #             # commented out since code moved to function update_utr_choices on 17.03.2024
    #             # utr_list = (
    #             #     Settlement.query.filter(
    #             #         coinsurance.follower_company_name == Settlement.name_of_company
    #             #     )
    #             #     .with_entities(
    #             #         Settlement.name_of_company,
    #             #         Settlement.utr_number,
    #             #         Settlement.date_of_settlement,
    #             #         Settlement.settled_amount,
    #             #     )
    #             #     .distinct()
    #             # )
    #             # form.settlement.choices = [
    #             #     (
    #             #         utr_number,
    #             #         f"{name_of_company}-{utr_number} on {date_of_settlement.strftime('%d/%m/%Y')} {settled_amount}",
    #             #     )
    #             #     for name_of_company, utr_number, date_of_settlement, settled_amount in utr_list
    #             # ]
    #
    # elif current_user.user_type in ["oo_user", "ro_user"]:
    #     if coinsurance.current_status == "Needs clarification from RO or OO":
    #         enable_save_button = True

    return render_template(
        "edit_coinsurance_entry.html",
        form=form,
        coinsurance=coinsurance,
        remarks=remarks,
        change_status=change_status,
        enable_save_button=enable_save_button,
        update_settlement=update_settlement,
        humanize_datetime=humanize_datetime,
        edit=True,
    )


def select_coinsurers(query, form):
    coinsurer_choices = query.distinct(Coinsurance.follower_company_name)
    form.coinsurer_name.choices: list[str] = ["View all"] + [
        x.follower_company_name for x in coinsurer_choices
    ]

    if form.validate_on_submit() and form.filter_coinsurer.data:
        coinsurer_choice: str = form.data["coinsurer_name"]
        if coinsurer_choice != "View all":
            query = query.filter(Coinsurance.follower_company_name == coinsurer_choice)
        return query
        # else:
        #   return query
    return query


@coinsurance_bp.route("/list/Settled/exception")
def list_settled_entries_without_utr():
    form_select_coinsurer = CoinsurerSelectForm()
    coinsurance_entries = Coinsurance.query.order_by(
        Coinsurance.follower_company_name.desc()
    ).filter(Coinsurance.utr_number.is_(None))
    if current_user.user_type == "ro_user":
        coinsurance_entries = Coinsurance.query.filter(
            Coinsurance.uiic_regional_code == current_user.ro_code
        )

    elif current_user.user_type == "oo_user":
        coinsurance_entries = Coinsurance.query.filter(
            Coinsurance.uiic_office_code == current_user.oo_code
        )

    coinsurance_entries = select_coinsurers(coinsurance_entries, form_select_coinsurer)

    return render_template(
        "view_all_coinsurance_entries.html",
        coinsurance_entries=coinsurance_entries,
        update_settlement=False,
        form_select_coinsurer=form_select_coinsurer,
        title="Settled entries without UTR number",
    )


@coinsurance_bp.route("/list/all", methods=["POST", "GET"])
def list_coinsurance_entries():
    form_select_coinsurer = CoinsurerSelectForm()

    coinsurance_entries = Coinsurance.query.order_by(
        Coinsurance.follower_company_name.desc()
    )
    if current_user.user_type == "ro_user":
        coinsurance_entries = Coinsurance.query.filter(
            Coinsurance.uiic_regional_code == current_user.ro_code
        )

    elif current_user.user_type == "oo_user":
        coinsurance_entries = Coinsurance.query.filter(
            Coinsurance.uiic_office_code == current_user.oo_code
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
def list_coinsurance_entries_by_status(status):
    form_select_coinsurer = CoinsurerSelectForm()

    coinsurance_entries = Coinsurance.query.filter(Coinsurance.current_status == status)
    if current_user.user_type == "ro_user":
        coinsurance_entries = coinsurance_entries.filter(
            Coinsurance.uiic_regional_code == current_user.ro_code
        )
        # coinsurance_entries = Coinsurance.query.filter(
        #     Coinsurance.uiic_regional_code == current_user.ro_code
        # ).filter(Coinsurance.current_status == status)
    elif current_user.user_type == "oo_user":
        coinsurance_entries = coinsurance_entries.filter(
            Coinsurance.uiic_office_code == current_user.oo_code
        )
        # coinsurance_entries = Coinsurance.query.filter(
        #     Coinsurance.uiic_office_code == current_user.oo_code
        # ).filter(Coinsurance.current_status == status)

    coinsurance_entries = select_coinsurers(coinsurance_entries, form_select_coinsurer)

    # update_settlement = False
    if current_user.user_type in ["admin", "coinsurance_hub_user"]:
        if status in ["To be settled"]:  # , "To be considered for settlement"]:
            # update_settlement = True
            # coinsurance_entries = select_coinsurers(
            #     coinsurance_entries, form_select_coinsurer
            # )

            coinsurer_choices = coinsurance_entries.distinct(
                Coinsurance.follower_company_name
            )
            list_coinsurer_choices = [
                x.follower_company_name for x in coinsurer_choices
            ]

            from server import db

            form = SettlementUTRForm()

            utr_list = Settlement.query.with_entities(
                Settlement.name_of_company,
                Settlement.utr_number,
                Settlement.settled_amount,
                Settlement.date_of_settlement,
            ).distinct()
            form.utr_number.choices = [
                (
                    utr_number,
                    f"{name_of_company}-{utr_number}: Rs. {settled_amount} on {date_of_settlement.strftime('%d/%m/%Y')}",
                )
                for name_of_company, utr_number, settled_amount, date_of_settlement in utr_list
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
            )
        else:
            # coinsurance_entries = select_coinsurers(
            #     coinsurance_entries, form_select_coinsurer
            # )
            return render_template(
                "view_all_coinsurance_entries.html",
                coinsurance_entries=coinsurance_entries,
                update_settlement=True,
                status=status,
                #        form=form,
                form_select_coinsurer=form_select_coinsurer,
            )
    else:
        # coinsurance_entries = select_coinsurers(
        #     coinsurance_entries, form_select_coinsurer
        # )
        return render_template(
            "view_all_coinsurance_entries.html",
            coinsurance_entries=coinsurance_entries,
            update_settlement=False,
            status=status,
            #        form=form,
            form_select_coinsurer=form_select_coinsurer,
        )


@coinsurance_bp.route("/list/settlements/<string:utr_number>", methods=["POST", "GET"])
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
def list_settlement_entries():
    settlement_entries = Settlement.query.all()

    return render_template(
        "list_settlement_entries.html", settlement_entries=settlement_entries
    )


@coinsurance_bp.route("/settlements/view/<int:settlement_id>")
def view_settlement_entry(settlement_id):
    settlement = Settlement.query.get_or_404(settlement_id)
    return render_template("view_settlement_entry.html", settlement=settlement)


@coinsurance_bp.route("/settlements/add_settlement_data", methods=["POST", "GET"])
def add_settlement_data():
    from server import db

    form = SettlementForm()
    if form.validate_on_submit():
        name_of_company = form.data["coinsurer_name"]
        date_of_settlement = form.data["date_of_settlement"]
        amount_settled = form.data["amount_settled"]
        utr_number = form.data["utr_number"]
        type_of_settlement = form.data["type_of_settlement"]
        notes = form.data["notes"]
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
            form.settlement_file.data.save("settlements/" + settlement_filename)
        else:
            settlement_filename = None

        settlement = Settlement(
            name_of_company=name_of_company,
            date_of_settlement=date_of_settlement,
            settled_amount=amount_settled,
            file_settlement_file=settlement_filename,
            utr_number=utr_number,
            type_of_transaction=type_of_settlement,
            notes=notes,
        )

        db.session.add(settlement)
        db.session.commit()

        return redirect(
            url_for("coinsurance.view_settlement_entry", settlement_id=settlement.id)
        )
    return render_template("add_settlement_entry.html", form=form)


@coinsurance_bp.route("/log/<int:coinsurance_id>")
def view_coinsurance_log(coinsurance_id):
    log = Coinsurance_log.query.filter(Coinsurance_log.coinsurance_id == coinsurance_id)
    column_names = Coinsurance_log.query.statement.columns.keys()
    return render_template(
        "view_coinsurance_log.html", log=log, column_names=column_names
    )


@coinsurance_bp.route("/upload_balances", methods=["POST", "GET"])
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
            },
            inplace=True,
        )
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
        df_coinsurance_balance.to_sql(
            "coinsurance_balances", engine, if_exists="append", index=False
        )
        flash("Coinsurance balance has been uploaded to database.")
    return render_template("coinsurance_balance_upload.html")


@coinsurance_bp.route("/view_coinsurance_balance", methods=["POST", "GET"])
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

    if form.validate_on_submit():
        period = form.data["period"]
        return redirect(url_for("coinsurance.view_coinsurance_balance", period=period))
    return render_template("query_coinsurance_balance.html", form=form)


@coinsurance_bp.route("/view_coinsurance_balance/<string:period>")
def view_coinsurance_balance(period):
    coinsurance_balance = CoinsuranceBalances.query.filter(
        CoinsuranceBalances.period == period
    )
    return render_template(
        "view_coinsurance_balance.html",
        coinsurance_balance=coinsurance_balance,
        period=period,
    )
