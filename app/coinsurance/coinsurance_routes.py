import uuid
from datetime import datetime
from sqlalchemy import func, distinct, select  # , groupby

from flask import redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename

from app.coinsurance import coinsurance_bp
from app.coinsurance.coinsurance_form import CoinsuranceForm, SettlementForm
from app.coinsurance.coinsurance_model import (  # , User
    Coinsurance,
    Coinsurance_log,
    Remarks,
    Settlement,
)


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
            .all()
        )
    else:
        query = (
            db.session.query(
                Coinsurance.current_status, func.count(Coinsurance.current_status)
            )
            .group_by(Coinsurance.current_status)
            .all()
        )

    return render_template("coinsurance_home.html", dashboard=query)


@coinsurance_bp.route("/add_entry", methods=["POST", "GET"])
def add_coinsurance_entry():
    from server import db

    form = CoinsuranceForm()
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

        bool_ri_involved = form.data["bool_reinsurance"]
        ri_payable_amount = form.data["int_ri_payable_amount"] or 0
        ri_receivable_amount = form.data["int_ri_receivable_amount"] or 0

        net_amount = (
            payable_amount
            - receivable_amount
            + ri_payable_amount
            - ri_receivable_amount
        )

        statement_filename_data = secure_filename(form.data["statement"].filename)
        statement_file_extension = statement_filename_data.rsplit(".", 1)[1]
        statement_filename = (
            "statement"
            + datetime.now().strftime("%d%m%Y %H%M%S")
            + "."
            + statement_file_extension
        )
        form.statement.data.save("statements/" + statement_filename)

        confirmation_filename_data = secure_filename(form.data["confirmation"].filename)
        confirmation_file_extension = confirmation_filename_data.rsplit(".", 1)[1]
        confirmation_filename = (
            "confirmation"
            + datetime.now().strftime("%d%m%Y %H%M%S")
            + "."
            + confirmation_file_extension
        )
        form.confirmation.data.save("confirmations/" + confirmation_filename)

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
        current_status = (
            "To be reviewed by coinsurance hub"  # form.data['current_status']
        )
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
        )
        db.session.add(coinsurance)
        db.session.commit()
        if form_remarks:
            remarks = Remarks(
                coinsurance_id=coinsurance.id,
                user=current_user.oo_code,
                remarks=form_remarks,
                time_of_remark=datetime.now(),
            )
            db.session.add(remarks)
            db.session.commit()
        coinsurance_log = Coinsurance_log(
            coinsurance_id=coinsurance.id,
            user=current_user.oo_code,
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
        return redirect(url_for("coinsurance.list_coinsurance_entries"))

    if current_user.user_type == "oo_user":
        form.regional_office_code.data = current_user.ro_code
        form.oo_code.data = current_user.oo_code
    elif current_user.user_type == "ro_user":
        form.regional_office_code.data = current_user.ro_code
    return render_template(
        "coinsurance_entry.html",
        form=form,
        change_status=False,
        enable_save_button=True,
        update_settlement=False,
    )


@coinsurance_bp.route("/view/<int:coinsurance_id>")
def view_coinsurance_entry(coinsurance_id):
    coinsurance = Coinsurance.query.get_or_404(coinsurance_id)
    remarks = Remarks.query.filter(Remarks.coinsurance_id == coinsurance_id)
    settlement = Settlement.query.filter(
        Settlement.settlement_uuid == coinsurance.settlement_uuid
    ).all()
    enable_edit_button = False
    if current_user.user_type == "admin":
        if coinsurance.current_status != "Settled":
            enable_edit_button = True
        elif coinsurance.current_status == "Settled":
            if coinsurance.settlement_uuid:  # is not None:
                enable_edit_button = False
            else:
                enable_edit_button = True
    elif current_user.user_type in ("oo_user", "ro_user"):
        if coinsurance.current_status == "Needs clarification from RO or OO":
            enable_edit_button = True
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

@coinsurance_bp.route("/settlements/<int:settlement_id>", methods=['POST','GET'])
def download_settlements(settlement_id):
    settlement = Settlement.query.get_or_404(settlement_id)

    file_extension = settlement.file_settlement_file.rsplit(".", 1)[1]
    path = settlement.file_settlement_file
    filename = f"{settlement.name_of_company} - {settlement.type_of_transaction} - {settlement.utr_number}.{file_extension}"
    return send_from_directory(
            directory = "settlements/",
            path = path,
            as_attachment=True,
            download_name=filename,
            )

@coinsurance_bp.route("/edit/<int:coinsurance_id>", methods=["POST", "GET"])
def edit_coinsurance_entry(coinsurance_id):
    from server import db

    form = CoinsuranceForm()
    coinsurance = Coinsurance.query.get_or_404(coinsurance_id)

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
        coinsurer_name = form.data["coinsurer_name"]
        coinsurer_office_code = form.data["coinsurer_office_code"]
        payable_amount = form.data["payable_amount"]
        receivable_amount = form.data["receivable_amount"]

        request_id = form.data["request_id"]
        current_status = "To be reviewed by coinsurance hub"
        if current_user.user_type in ("coinsurance_hub_user", "admin"):
           # or current_user.user_type == "admin"
        #):
            current_status = form.data["current_status"]

        type_of_transaction = form.data["type_of_transaction"]

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
            settlement_uuid = form.data["settlement"]
            coinsurance.settlement_uuid = settlement_uuid

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

        db.session.commit()

        if form.data["remarks"]:
            remarks = Remarks(
                coinsurance_id=coinsurance.id,
                user=current_user.oo_code,
                remarks=form.data["remarks"],
                time_of_remark=datetime.now(),
            )
            db.session.add(remarks)
            db.session.commit()

        coinsurance_log = Coinsurance_log(
            coinsurance_id=coinsurance.id,
            user=current_user.oo_code,
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

        return redirect(url_for("coinsurance.list_coinsurance_entries"))
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

    if coinsurance.boolean_reinsurance_involved:
        form.int_ri_payable_amount.data = coinsurance.int_ri_payable_amount
        form.int_ri_receivable_amount.data = coinsurance.int_ri_receivable_amount

    enable_save_button = False
    change_status = False
    update_settlement = False

    if current_user.user_type == "admin":
        if coinsurance.current_status != "Settled":
            change_status = True
            enable_save_button = True
        elif coinsurance.current_status == "Settled":
            change_status = True
            if coinsurance.settlement_uuid is None:
                update_settlement = True
                enable_save_button = True
                form.settlement.choices = [
                    (g.settlement_uuid, g.utr_number)
                    for g in Settlement.query.filter(
                        Settlement.name_of_company == coinsurance.follower_company_name
                    )
                ]
            else:
                update_settlement = False
                enable_save_button = False
        else:
            enable_save_button = False
    elif current_user.user_type in ["oo_user", "ro_user"]:
        if coinsurance.current_status == "Needs clarification from RO or OO":
            enable_save_button = True

    #  if coinsurance.current_status == "Settled" and coinsurance.settlement_uuid is None:
    #     update_settlement = True

    # if coinsurance.current_status == "Settled" and coinsurance.settlement_uuid:
    #   update_settlement = False
    # form.settlement.data = coinsurance.settlement_uuid
    # [(g.id, g.name) for g in Group.query.order_by('name')]
    return render_template(
        "coinsurance_entry.html",
        form=form,
        coinsurance=coinsurance,
        remarks=remarks,
        change_status=change_status,
        enable_save_button=enable_save_button,
        update_settlement=update_settlement,
    )


@coinsurance_bp.route("/list/all")
def list_coinsurance_entries():

    # db.session.scalars(select(Coinsurance)).all() #Coinsurance.query.all()
    if current_user.user_type == "ro_user":
        coinsurance_entries = Coinsurance.query.filter(
            Coinsurance.uiic_regional_code == current_user.ro_code
        )
    elif current_user.user_type == "oo_user":
        coinsurance_entries = Coinsurance.query.filter(
            Coinsurance.uiic_office_code == current_user.oo_code
        )
    else:
        coinsurance_entries = Coinsurance.query.all()
    return render_template(
        "coinsurance_entries_all.html",
        coinsurance_entries=coinsurance_entries,
        update_settlement=False,
    )


@coinsurance_bp.route("/list/<string:status>")
def list_coinsurance_entries_by_status(status):

    if current_user.user_type == "ro_user":
        coinsurance_entries = Coinsurance.query.filter(
            Coinsurance.uiic_regional_code == current_user.ro_code
        ).filter(Coinsurance.current_status == status)
    elif current_user.user_type == "oo_user":
        coinsurance_entries = Coinsurance.query.filter(
            Coinsurance.uiic_office_code == current_user.oo_code
        ).filter(Coinsurance.current_status == status)
    else:
        coinsurance_entries = Coinsurance.query.filter(
            Coinsurance.current_status == status
        ).all()
    return render_template(
        "coinsurance_entries_all.html",
        coinsurance_entries=coinsurance_entries,
        update_settlement=False,
        status = status
    )


@coinsurance_bp.route("/list/settlements")
def list_settlement_entries():
    settlement_entries = Settlement.query.all()

    return render_template(
        "list_settlement_entries.html", settlement_entries=settlement_entries
    )


@coinsurance_bp.route(
    "/list/settlements_entries/<uuid:uuid>"
)
def list_settled_coinsurance_entries(uuid):
    return render_template(
        "coinsurance_entries_all.html",
        coinsurance_entries=Coinsurance.query.filter(
            Coinsurance.settlement_uuid == uuid
        ),
        update_settlement=False,
    )


@coinsurance_bp.route("/view/settlement/<int:settlement_id>")
def view_settlement_entry(settlement_id):
    settlement = Settlement.query.get_or_404(settlement_id)
    return render_template("view_settlement_entry.html", settlement=settlement)


@coinsurance_bp.route("/settlement_data/<uuid:uuid_value>", methods=["POST", "GET"])
def add_settlement_data(uuid_value):
    from server import db

    form = SettlementForm()
    if form.validate_on_submit():
        name_of_company = form.data["coinsurer_name"]
        date_of_settlement = form.data["date_of_settlement"]
        amount_settled = form.data["amount_settled"]
        utr_number = form.data["utr_number"]
        type_of_settlement = form.data["type_of_settlement"]

        settlement_filename_data = secure_filename(form.data["settlement_file"].filename)
        settlement_file_extension = settlement_filename_data.rsplit(".", 1)[1]
        settlement_filename = (
            "settlement"
            + datetime.now().strftime("%d%m%Y %H%M%S")
            + "."
            + settlement_file_extension
        )
        form.settlement_file.data.save("settlements/" + settlement_filename)

        settlement = Settlement(
            name_of_company=name_of_company,
            date_of_settlement=date_of_settlement,
            settled_amount=amount_settled,
            file_settlement_file = settlement_filename,
            utr_number=utr_number,
            type_of_transaction=type_of_settlement,
            settlement_uuid=uuid_value,
        )

        db.session.add(settlement)

        db.session.commit()

        return redirect(
            url_for("coinsurance.list_coinsurance_entries_to_be_settled")
        )
    return render_template("settlement_entry.html", form=form)


@coinsurance_bp.route("/list/to_be_settled", methods=["POST", "GET"])
def list_coinsurance_entries_to_be_settled():
    from server import db

    coinsurance_entries = Coinsurance.query.filter(
        Coinsurance.current_status == "To be considered for settlement"
    )
    update_settlement = True
    if request.method == "POST":
        uuid_value = str(uuid.uuid4())
        form_coinsurance_keys = request.form.getlist("coinsurance_keys")

        for key in form_coinsurance_keys:
            coinsurance = Coinsurance.query.get_or_404(key)
            coinsurance.settlement_uuid = uuid_value
            coinsurance.current_status = "Settled"
        db.session.commit()
        return redirect(
            url_for("coinsurance.add_settlement_data", uuid_value=uuid_value)
        )
    return render_template(
        "coinsurance_entries_all.html",
        coinsurance_entries=coinsurance_entries,
        update_settlement=update_settlement,
    )


@coinsurance_bp.route("/log/<int:coinsurance_id>")
def view_coinsurance_log(coinsurance_id):
    log = Coinsurance_log.query.filter(Coinsurance_log.coinsurance_id == coinsurance_id)
    column_names = Coinsurance_log.query.statement.columns.keys()
    return render_template(
        "view_coinsurance_log.html", log=log, column_names=column_names
    )
