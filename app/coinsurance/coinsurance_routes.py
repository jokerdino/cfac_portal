import uuid
from datetime import datetime

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
    return render_template("coinsurance_home.html")


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
    )


@coinsurance_bp.route("/view/<int:coinsurance_id>")
def view_coinsurance_entry(coinsurance_id):
    coinsurance = Coinsurance.query.get_or_404(coinsurance_id)
    remarks = Remarks.query.filter(Remarks.coinsurance_id == coinsurance_id)
    enable_edit_button = False
    if current_user.user_type == "admin":
        enable_edit_button = True
    elif current_user.user_type == "oo_user" or "ro_user":
        if coinsurance.current_status == "Needs clarification from RO/OO":
            enable_edit_button = True
    return render_template(
        "view_coinsurance_entry.html",
        coinsurance=coinsurance,
        remarks=remarks,
        enable_edit_button=enable_edit_button,
    )


@coinsurance_bp.route("/statement/<int:coinsurance_id>", methods=["POST", "GET"])
def download_statement(coinsurance_id):
    coinsurance = Coinsurance.query.get_or_404(coinsurance_id)
    statement_file_extension = coinsurance.statement.rsplit(".", 1)[1]
    if coinsurance.net_amount < 0:
        amount_string = f"receivable {coinsurance.net_amount * -1}"
    else:
        amount_string = f"payable {coinsurance.net_amount}"
    statement_filename = f"{coinsurance.type_of_transaction} statement - {coinsurance.uiic_office_code} - {coinsurance.follower_company_name} {amount_string}.{statement_file_extension}"
    return send_from_directory(
        directory="statements/",
        path=coinsurance.statement,
        as_attachment=True,
        download_name=statement_filename,
    )


@coinsurance_bp.route("/confirmation/<int:coinsurance_id>", methods=["POST", "GET"])
def download_confirmation(coinsurance_id):
    coinsurance = Coinsurance.query.get_or_404(coinsurance_id)
    confirmation_file_extension = coinsurance.confirmation.rsplit(".", 1)[1]
    if coinsurance.net_amount < 0:
        amount_string = f"receivable {coinsurance.net_amount * -1}"
    else:
        amount_string = f"payable {coinsurance.net_amount}"
    confirmation_filename = f"{coinsurance.type_of_transaction} confirmation - {coinsurance.uiic_office_code} - {coinsurance.follower_company_name} {amount_string}.{confirmation_file_extension}"
    return send_from_directory(
        directory="confirmations/",
        path=coinsurance.confirmation,
        as_attachment=True,
        download_name=confirmation_filename,
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
        if (
            current_user.user_type == "coinsurance_hub_user"
            or current_user.user_type == "admin"
        ):
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
    if current_user.user_type == "admin":
        change_status = True
        enable_save_button = True
    elif current_user.user_type == "oo_user" or current_user.user_type == "ro_user":
        if coinsurance.current_status == "Needs clarification from RO/OO":
            enable_save_button = True
    return render_template(
        "coinsurance_entry.html",
        form=form,
        coinsurance=coinsurance,
        remarks=remarks,
        change_status=change_status,
        enable_save_button=enable_save_button,
    )


@coinsurance_bp.route("/list/all")
def list_coinsurance_entries():
    pass

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


@coinsurance_bp.route("/settlement_data/<uuid:uuid_value>", methods=["POST", "GET"])
def add_settlement_data(uuid_value):
    from server import db

    # coinsurance = Coinsurance.query.filter(Coinsurance.settlement_id == uuid_value)
    # print(coinsurance)#.all()
    form = SettlementForm()
    if form.validate_on_submit():
        # print(form_coinsurance_keys)
        name_of_company = form.data["coinsurer_name"]
        date_of_settlement = form.data["date_of_settlement"]
        amount_settled = form.data["amount_settled"]
        utr_number = form.data["utr_number"]
        type_of_settlement = form.data["type_of_settlement"]

        settlement_uuid = uuid_value
        settlement = Settlement(
            name_of_company=name_of_company,
            date_of_settlement=date_of_settlement,
            settled_amount=amount_settled,
            utr_number=utr_number,
            type_of_transaction=type_of_settlement,
            settlement_uuid=uuid_value,
        )

        db.session.add(settlement)
        # coinsurance = Coinsurance.query.filter(Coinsurance.settlement_id == uuid_value).all()
        # for entry in coinsurance:
        #    entry.settlement_id = settlement.id
        #  coinsurance.settlement_id = settlement.id
        db.session.commit()

        # form_coinsurance_keys = requests.post(f"http://localhost:8080/coinsurance/api/add_message/{uuid_value}").json()#uid_value)
        # print(form_coinsurance_keys)
        # return request.form.to_dict()
        #  for key in form_coinsurance_keys.json():
        # #     print(key[1])
        #      coinsurance = Coinsurance.query.get_or_404(key)
        #      coinsurance.settlement_id = settlement.id
        #      coinsurance.current_status = "Settled"
        #      db.session.commit()
        return redirect(
            url_for("coinsurance.list_coinsurance_entries_to_be_settled")
        )  # , coinsurance_entries = coinsurance_entries,
    return render_template("settlement_entry.html", form=form)


# @coinsurance_bp.route('/api/add_message/<uuid:uuid_value>', methods=['GET', 'POST'])
# def add_message(uuid_value):
#    content = request.json
#    return content['keys']
#
@coinsurance_bp.route("/list/to_be_settled", methods=["POST", "GET"])
def list_coinsurance_entries_to_be_settled():
    from server import db

    # form_coinsurance_keys = ["22"]
    coinsurance_entries = Coinsurance.query.filter(
        Coinsurance.current_status == "To be considered for settlement"
    )
    update_settlement = True
    if request.method == "POST":
        #   print(form_coinsurance_keys)
        uuid_value = str(uuid.uuid4())
        form_coinsurance_keys = request.form.getlist("coinsurance_keys")
        # res = requests.post(f'http://localhost:8080/coinsurance/api/add_message/{uuid_value}', json={"keys":form_coinsurance_keys})
        # if res.ok:
        #    print(res.json())
        # print(form_coinsurance_keys)
        # print("out")
        # get settlement details here
        # for key in form_coinsurance_keys:
        # coinsurance = Coinsurance.query.get_or_404
        # form = SettlementForm()
        # if form.validate_on_submit():
        #    print(form_coinsurance_keys)
        #    date_of_settlement = form.data['date_of_settlement']
        #    amount_settled = form.data['amount_settled']
        #    utr_number = form.data['utr_number']
        #    type_of_settlement = form.data['type_of_settlement']

        #    settlement = Settlement(date_of_settlement = date_of_settlement, settled_amount = amount_settled,
        #            utr_number = utr_number, type_of_transaction= type_of_settlement)

        #    db.session.add(settlement)
        #    db.session.commit()
        for key in form_coinsurance_keys:
            # print(key[1])
            coinsurance = Coinsurance.query.get_or_404(key)
            coinsurance.settlement_uuid = uuid_value
            coinsurance.current_status = "Settled"
        db.session.commit()
        #    return redirect(url_for('coinsurance.list_coinsurance_entries_to_be_settled'))#, coinsurance_entries = coinsurance_entries,
        #       # update_settlement = update_settlement))
        ##response = redirect(url_for("coinsurance.add_settlement_data"))
        return redirect(
            url_for("coinsurance.add_settlement_data", uuid_value=uuid_value)
        )  #:w, form = form, form_coinsurance_keys = form_coinsurance_keys)) #, list_keys = form_coinsurance_keys)
    # if request.method == "GET":
    #    coinsurance_entries = Coinsurance.query.filter(Coinsurance.current_status == "To be considered for settlement")
    #   update_settlement = True
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
