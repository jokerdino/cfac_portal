from datetime import datetime
import humanize

from flask import (
    current_app,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.contracts import contracts_bp
from app.contracts.contracts_form import ContractsAddForm
from app.contracts.contracts_model import Contracts


@contracts_bp.route("/add", methods=["POST", "GET"])
@login_required
def add_contract_entry():
    from server import db

    form = ContractsAddForm()

    if form.validate_on_submit():
        vendor = form.data["vendor_name"]
        purpose = form.data["purpose"]
        start_date = form.data["start_date"]
        end_date = form.data["end_date"]
        emd = form.data["emd"]
        renewal = form.data["renewal"]
        remarks = form.data["remarks"]
        notice_period = form.data["notice_period"]
        if form.data["upload_contract_file"]:
            contract_filename_data = secure_filename(
                form.data["upload_contract_file"].filename
            )
            contract_file_extension = contract_filename_data.rsplit(".", 1)[1]
            contract_filename = (
                "contract"
                + datetime.now().strftime("%d%m%Y %H%M%S")
                + "."
                + contract_file_extension
            )
            form.upload_contract_file.data.save(
                f"{current_app.config.get('UPLOAD_FOLDER')}contracts/"
                + contract_filename
            )
        else:
            contract_filename = None
        contract = Contracts(
            vendor=vendor,
            purpose=purpose,
            start_date=start_date,
            end_date=end_date,
            emd=emd,
            renewal=renewal,
            remarks=remarks,
            notice_period=notice_period,
            contract_file=contract_filename,
        )
        db.session.add(contract)
        db.session.commit()

        # return redirect
        return redirect(url_for("contracts.view_contract", contract_id=contract.id))
    return render_template(
        "add_contracts_entry.html", form=form, title="Add new contract details"
    )


@contracts_bp.route("/download/<int:contract_id>")
def download_contract_document(contract_id):
    contract = Contracts.query.get_or_404(contract_id)
    filename_extension = contract.contract_file.rsplit(".", 1)[1]
    filename = (
        f"{contract.id}_{contract.vendor}_{contract.purpose}.{filename_extension}"
    )
    return send_from_directory(
        directory=f"{current_app.config.get('UPLOAD_FOLDER')}contracts/",
        path=contract.contract_file,
        as_attachment=True,
        download_name=filename,
    )


@contracts_bp.route("/view/<int:contract_id>")
def view_contract(contract_id):
    contract = Contracts.query.get_or_404(contract_id)

    return render_template(
        "view_contract.html", contract=contract, compare_end_date=compare_end_date
    )


@contracts_bp.route("/edit/<int:contract_id>", methods=["GET", "POST"])
def edit_contract(contract_id):
    from server import db

    contract = Contracts.query.get_or_404(contract_id)
    form = ContractsAddForm()

    if form.validate_on_submit():
        contract.vendor = form.vendor_name.data
        contract.start_date = form.start_date.data
        contract.end_date = form.end_date.data
        contract.purpose = form.purpose.data
        contract.emd = form.emd.data
        contract.remarks = form.remarks.data
        contract.renewal = form.renewal.data
        contract.notice_period = form.notice_period.data

        # uploading revised contract documents
        if form.data["upload_contract_file"]:
            contract_filename_data = secure_filename(
                form.data["upload_contract_file"].filename
            )
            contract_file_extension = contract_filename_data.rsplit(".", 1)[1]
            contract_filename = (
                "contract"
                + datetime.now().strftime("%d%m%Y %H%M%S")
                + "."
                + contract_file_extension
            )
            form.upload_contract_file.data.save(
                f"{current_app.config.get('UPLOAD_FOLDER')}contracts/"
                + contract_filename
            )

            contract.contract_file = contract_filename
        db.session.commit()

        return redirect(url_for("contracts.view_contract", contract_id=contract.id))

    form.vendor_name.data = contract.vendor
    form.purpose.data = contract.purpose
    form.start_date.data = contract.start_date
    form.end_date.data = contract.end_date
    form.emd.data = contract.emd
    form.renewal.data = contract.renewal
    form.remarks.data = contract.remarks
    form.notice_period.data = contract.notice_period

    return render_template(
        "add_contracts_entry.html", form=form, title="Edit contract details"
    )


@contracts_bp.route("/<string:status>")
def view_contracts(status):
    #    from server import db

    if status == "expired":
        contracts = Contracts.query.filter(
            Contracts.end_date < datetime.date(datetime.now())
        )
    elif status == "active":
        contracts = Contracts.query.filter(
            (Contracts.end_date > datetime.date(datetime.now()))
            | (Contracts.end_date == datetime.date(datetime.now()))
        )
    elif status == "all":
        contracts = Contracts.query.all()
    else:
        return redirect(url_for("contracts.view_contracts", status="active"))
    return render_template(
        "contract_home_page.html",
        query=contracts,
        compare_end_date=compare_end_date,
        today=datetime.date(datetime.now()),
        status=status,
    )


def compare_end_date(end_date):
    today = datetime.date(datetime.now())
    if end_date == today:
        return "Expiring today"
    elif end_date > today:
        return f"Expiring in {humanize.naturaldelta(end_date - today)}."
    else:
        return f"Expired {humanize.naturaldelta(end_date - today)} ago."
