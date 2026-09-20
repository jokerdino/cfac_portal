import requests
from flask import abort, current_app, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from extensions import db
from set_view_permissions import admin_required

from . import fund_intimation_bp
from .forms import FundIntimationForm, FundIntimationFormOO, FundIntimationFormRO
from .models import FundIntimation


@fund_intimation_bp.route("/api/check_transaction/", methods=["GET", "POST"])
def check_pending_transactions():
    pending_transactions = db.session.execute(
        db.select(
            FundIntimation.display_transaction_id.label("transaction_id"),
            db.func.to_char(FundIntimation.date_of_intimation, "DD-MM-YYYY").label(
                "date_of_intimation"
            ),
        ).where(
            FundIntimation.utr_number.is_(None),
        )
    ).mappings()
    data = [dict(row) for row in pending_transactions]
    return {"pending_transactions": data}


@fund_intimation_bp.route("/add/", methods=["POST", "GET"])
@login_required
def fund_intimation_add():
    if current_user.user_type == "ro_user":
        form = FundIntimationFormRO()
        form.regional_office_code.data = current_user.ro_code
    elif current_user.user_type in ["oo_user"]:
        form = FundIntimationFormOO()
        form.regional_office_code.data = current_user.ro_code
        form.operating_office_code.data = current_user.oo_code
    elif current_user.user_type in ["coinsurance_hub_user"]:
        form = FundIntimationFormOO()
        form.regional_office_code.data = current_user.oo_code
        form.operating_office_code.data = current_user.oo_code

    else:
        form = FundIntimationForm()
    if form.validate_on_submit():
        fund_intimation = FundIntimation()
        form.populate_obj(fund_intimation)
        db.session.add(fund_intimation)
        db.session.commit()
        return redirect(url_for(".fund_intimation_view", id=fund_intimation.id))
    return render_template(
        "fund_intimation_form.html", form=form, title="Add new fund intimation"
    )


@fund_intimation_bp.route("/view/<int:id>/", methods=["GET"])
@login_required
def fund_intimation_view(id):
    intimation = db.get_or_404(FundIntimation, id)
    intimation.require_access(current_user)
    return render_template(
        "fund_intimation_view.html", fi=intimation, title="View fund intimation"
    )


@fund_intimation_bp.route("/edit/<int:id>/", methods=["POST", "GET"])
@login_required
def fund_intimation_edit(id):
    intimation = db.get_or_404(FundIntimation, id)
    intimation.require_access(current_user)
    if intimation.check_status():
        return redirect(url_for(".fund_intimation_view", id=intimation.id))
    if current_user.user_type == "ro_user":
        form = FundIntimationFormRO(obj=intimation)
    elif current_user.user_type in ["oo_user", "coinsurance_hub_user"]:
        form = FundIntimationFormOO(obj=intimation)
    else:
        form = FundIntimationForm(obj=intimation)

    if form.validate_on_submit():
        form.populate_obj(intimation)
        db.session.commit()
        return redirect(url_for(".fund_intimation_view", id=intimation.id))
    return render_template(
        "fund_intimation_form.html", form=form, title="Edit fund intimation"
    )


@fund_intimation_bp.route("/list/<string:status>/", methods=["GET"])
@login_required
def fund_intimation_list(status="pending"):
    column_names = [
        "date_of_intimation",
        "regional_office_code",
        "operating_office_code",
        "type_of_disbursement",
        "nature_of_recipient",
        "name_of_recipient",
        "purpose_of_disbursement",
        "expected_date_of_disbursement",
        "transaction_id",
        "transaction_amount",
        "utr_number",
    ]
    query = db.select(FundIntimation).order_by(FundIntimation.date_of_intimation.desc())

    role = current_user.user_type
    if role == "ro_user":
        query = query.where(FundIntimation.regional_office_code == current_user.ro_code)
    elif role in ["oo_user", "coinsurance_hub_user"]:
        query = query.where(
            FundIntimation.operating_office_code == current_user.oo_code
        )
    elif role != "admin":
        abort(404)
    if status == "pending":
        query = query.where(FundIntimation.utr_number.is_(None))
        title = "List of pending transactions"
    elif status == "completed":
        query = query.where(FundIntimation.utr_number.isnot(None))
        title = "List of completed transactions"
    elif status == "all":
        title = "List of all transactions"
    intimation_list = db.session.scalars(query).all()
    return render_template(
        "fund_intimation_list.html",
        intimation_list=intimation_list,
        column_names=column_names,
        title=title,
        status=status,
    )


@fund_intimation_bp.route("/api/post_transaction/")
@login_required
@admin_required
def fund_intimation_utr_number_update():
    # Get transactions for which UTR is not available
    #  query = db.select(
    #     FundIntimation.display_transaction_id.label("transaction_id")
    #  ).where(FundIntimation.utr_number.is_(None))

    query = db.select(FundIntimation.transaction_id).where(
        FundIntimation.utr_number.is_(None)
    )

    transaction_ids = db.session.execute(query).scalars().all()

    if not transaction_ids:
        return {
            "message": "No transactions pending for UTR update",
            "updated": 0,
        }

    external_url = (
        f"{current_app.config.get('CFAC_FLASK_DASHBOARD_URL')}api/update_utr/"
    )

    payload = {"transaction_ids": transaction_ids}

    try:
        external_response = requests.post(
            external_url,
            json=payload,
            timeout=30,
            proxies={
                "http": None,
                "https": None,
            },
            verify=False,
        )

        external_response.raise_for_status()

    except requests.RequestException as exc:
        flash(f"Failed to fetch UTR from external API due to error {exc!s}", "error")
        return redirect(url_for(".fund_intimation_list", status="pending"))

    response_data = external_response.json()

    # Expected:
    # {
    #     "data": [
    #         {
    #             "transaction_id": "...",
    #             "utr_number": "..."
    #         }
    #     ]
    # }

    utr_data = response_data.get("data", [])
    utr_map = {
        item["transaction_id"]: item["utr_number"]
        for item in utr_data
        if item.get("transaction_id") and item.get("utr_number")
    }

    for transaction_id, utr_number in utr_map.items():
        db.session.execute(
            db.update(FundIntimation)
            .where(
                FundIntimation.transaction_id == transaction_id,
                FundIntimation.utr_number.is_(None),
            )
            .values(utr_number=utr_number)
        )

    db.session.commit()

    # updated = 0

    # for item in utr_data:
    #     transaction_id = item.get("transaction_id")
    #     utr_number = item.get("utr_number")

    #     if not transaction_id or not utr_number:
    #         continue

    #     fund_intimation = db.session.scalar(
    #         db.select(FundIntimation).where(
    #             FundIntimation.transaction_id == transaction_id,
    #             FundIntimation.utr_number.is_(None),
    #         )
    #     )

    #     if fund_intimation:
    #         fund_intimation.utr_number = utr_number
    #         updated += 1

    # db.session.commit()

    flash(
        f"UTR update completed. "
        f"Requested: {len(transaction_ids)}, "
        f"Received: {len(utr_data)}, "
        "success",
    )

    return redirect(url_for(".fund_intimation_list", status="pending"))
