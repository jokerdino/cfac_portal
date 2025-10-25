from datetime import datetime
import os

from flask import (
    current_app,
    redirect,
    render_template,
    send_from_directory,
    url_for,
)
from flask_login import login_required
from werkzeug.utils import secure_filename

from . import contracts_bp
from .contracts_form import ContractsAddForm
from .contracts_model import Contracts

from extensions import db
from set_view_permissions import admin_required


@contracts_bp.route("/add", methods=["POST", "GET"])
@login_required
@admin_required
def add_contract_entry():
    form = ContractsAddForm()

    if form.validate_on_submit():
        contract = Contracts()
        form.populate_obj(contract)

        upload_contract_file(form, "upload_contract_file", contract, "contract_file")

        db.session.add(contract)
        db.session.commit()

        return redirect(url_for("contracts.view_contract", contract_id=contract.id))
    return render_template(
        "add_contracts_entry.html", form=form, title="Add new contract details"
    )


@contracts_bp.route("/download/<int:contract_id>/")
@login_required
@admin_required
def download_contract_document(contract_id):
    contract = db.get_or_404(Contracts, contract_id)

    return send_from_directory(
        directory=os.path.dirname(contract.file_path),
        path=os.path.basename(contract.file_path),
        as_attachment=True,
        download_name=contract.download_filename,
    )


@contracts_bp.route("/view/<int:contract_id>/")
@login_required
@admin_required
def view_contract(contract_id):
    contract = db.get_or_404(Contracts, contract_id)

    return render_template(
        "view_contract.html",
        contract=contract,
    )


def upload_contract_file(form, form_field_name, model, model_field):
    if form.data[form_field_name]:
        contract_filename_data = secure_filename(form.data[form_field_name].filename)
        contract_file_extension = contract_filename_data.rsplit(".", 1)[1]
        contract_filename = (
            "contract"
            + datetime.now().strftime("%d%m%Y %H%M%S")
            + "."
            + contract_file_extension
        )
        form.upload_contract_file.data.save(
            f"{current_app.config.get('UPLOAD_FOLDER')}contracts/" + contract_filename
        )
        setattr(model, model_field, contract_filename)


@contracts_bp.route("/edit/<int:contract_id>/", methods=["GET", "POST"])
@login_required
@admin_required
def edit_contract(contract_id):
    contract = db.get_or_404(Contracts, contract_id)
    form = ContractsAddForm(obj=contract)

    if form.validate_on_submit():
        form.populate_obj(contract)

        upload_contract_file(form, "upload_contract_file", contract, "contract_file")
        db.session.commit()

        return redirect(url_for("contracts.view_contract", contract_id=contract.id))

    return render_template(
        "add_contracts_entry.html", form=form, title="Edit contract details"
    )


@contracts_bp.route("/<string:status>/")
@login_required
@admin_required
def view_contracts(status):
    today = datetime.date(datetime.now())
    stmt = db.select(Contracts)
    if status == "expired":
        stmt = stmt.filter(Contracts.end_date < today)
    elif status == "active":
        stmt = stmt.filter(Contracts.end_date >= today)

    contracts = db.session.scalars(stmt)
    return render_template(
        "contract_home_page.html",
        query=contracts,
        today=today,
        status=status,
    )
