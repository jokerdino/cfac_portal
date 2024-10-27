from datetime import datetime
from dataclasses import asdict

from sqlalchemy import (
    and_,
    func,
    case,
    cast,
    String,
)


from flask import abort, flash, redirect, render_template, url_for, request
from flask_login import current_user, login_required

from . import pool_credits_bp
from .pool_credits_form import UpdatePoolCreditsForm
from .pool_credits_model import PoolCredits, PoolCreditsPortal

from app.funds.funds_model import FundBankStatement, FundJournalVoucherFlagSheet

from extensions import db
from set_view_permissions import ro_user_only, admin_required


@pool_credits_bp.route("/<string:status>/", methods=["POST", "GET"])
@login_required
@ro_user_only
def pool_credits_list_identified_api(status):
    from extensions import db

    if request.method == "POST":

        list_pool_keys = request.form.getlist("pool_keys")
        updated_time = datetime.now()
        for key in list_pool_keys:
            pool_credit_entry = PoolCredits.query.get_or_404(key)
            pool_credit_entry.bool_jv_passed = True
            pool_credit_entry.jv_passed_by = current_user.username
            pool_credit_entry.jv_passed_on = updated_time
            db.session.commit()

    return render_template("pool_credits_list_ajax.html", status=status)


@pool_credits_bp.route("/api/v1/data/pool_credits_portal/", methods=["GET"])
def pool_credits_portal():

    # http://0.0.0.0:8080/pool_credits/api/data/pool_credits_portal/?date_added=2024-08-26T15:11:11Z
    from extensions import db

    entries = db.session.query(PoolCreditsPortal)
    request_param = request.args

    request_param_dict = {}
    for key, value in request_param.items():
        try:
            param, operator = key.split("__")
        except ValueError:
            param, operator = key, None

        request_param_dict[param] = {"operator": operator, "value": value}

    amount_credit = set_value("amount_credit", request_param_dict)
    txt_reference_number = set_value("reference_no", request_param_dict)
    id = set_value("id", request_param_dict)
    date_value_date = set_value("value_date", request_param_dict)
    txt_name_of_remitter = set_value("remitter", request_param_dict)
    date_created_date = set_value("created_date", request_param_dict)

    if amount_credit:
        entries = dynamic_query_column(entries, "amount_credit", amount_credit)
    if txt_reference_number:
        entries = dynamic_query_column(
            entries, "txt_reference_number", txt_reference_number
        )
    if date_value_date:
        entries = dynamic_query_column(entries, "date_value_date", date_value_date)
    if txt_name_of_remitter:
        entries = dynamic_query_column(
            entries, "txt_name_of_remitter", txt_name_of_remitter
        )
    if date_created_date:
        entries = dynamic_query_column(entries, "date_created_date", date_created_date)
    if id:
        entries = dynamic_query_column(entries, "id", id)

    entries_count = entries.count()  # if entries else 0
    return {
        "recordsTotal": entries_count,
        "data": [asdict(entry) for entry in entries],
    }


def set_value(string, dict_values):
    return dict_values[string] if string in dict_values.keys() else False


def dynamic_query_column(entries, col_name, dict_param):
    operator = dict_param["operator"] if dict_param["operator"] else "eq"
    value = dict_param["value"]
    # in, eq, not, gte, lte, gt, lt, like, ilike

    if operator == "eq":
        entries = entries.filter(getattr(PoolCreditsPortal, col_name) == value)
    elif operator == "gt":
        entries = entries.filter(getattr(PoolCreditsPortal, col_name) > value)
    elif operator == "gte":
        entries = entries.filter(getattr(PoolCreditsPortal, col_name) >= value)
    elif operator == "lt":
        entries = entries.filter(getattr(PoolCreditsPortal, col_name) < value)
    elif operator == "lte":
        entries = entries.filter(getattr(PoolCreditsPortal, col_name) <= value)
    elif operator == "like":
        entries = entries.filter(
            getattr(PoolCreditsPortal, col_name).like(f"%{value}%")
        )
    elif operator == "ilike":
        entries = entries.filter(
            getattr(PoolCreditsPortal, col_name).ilike(f"%{value}%")
        )
    # elif operator == "in":
    #     entries = entries.filter(getattr(PoolCreditsPortal, col_name).in_(value))
    elif operator == "not":
        entries = entries.filter(getattr(PoolCreditsPortal, col_name) != value)
    elif operator is None:
        entries = entries
    return entries


@pool_credits_bp.route("/api/v1/data/<string:status>/", methods=["GET"])
@login_required
@ro_user_only
def get_data(status):
    from extensions import db

    if status == "unidentified":
        entries = db.session.query(PoolCredits).filter(
            PoolCredits.str_regional_office_code.is_(None)
        )

    elif status == "identified":
        entries = db.session.query(PoolCredits).filter(
            (PoolCredits.str_regional_office_code.is_not(None))
            & (PoolCredits.bool_jv_passed.is_(False))
        )
    elif status == "jv_passed":
        entries = db.session.query(PoolCredits).filter(
            (PoolCredits.str_regional_office_code.is_not(None))
            & (PoolCredits.bool_jv_passed.is_(True))
        )

    # order by date of creation and ID descending order
    # entries = entries.order_by(
    #     PoolCredits.date_created_date.desc(), PoolCredits.id.desc()
    # )

    # filter only entries uploaded after Oct-2024
    entries = entries.filter(PoolCredits.value_date >= "2024-10-01")

    entries_count = entries.count()

    # search filter
    search = request.args.get("search[value]")
    if search:
        entries = entries.filter(
            db.or_(
                cast(PoolCredits.book_date, String).like(f"%{search}%"),
                PoolCredits.description.ilike(f"%{search}%"),
                cast(PoolCredits.credit, String).like(f"%{search}%"),
                cast(PoolCredits.debit, String).like(f"%{search}%"),
                cast(PoolCredits.value_date, String).like(f"%{search}%"),
                PoolCredits.reference_no.ilike(f"%{search}%"),
                cast(PoolCredits.str_regional_office_code, String).like(f"%{search}%"),
            )
        )

    total_filtered = entries.count()

    # sorting
    order = []
    i = 0
    while True:
        col_index = request.args.get(f"order[{i}][column]")
        if col_index is None:
            break
        col_name = request.args.get(f"columns[{col_index}][data]")
        descending = request.args.get(f"order[{i}][dir]") == "desc"
        col = getattr(PoolCredits, col_name)
        if descending:
            col = col.desc()
        order.append(col)
        i += 1
    if order:
        entries = entries.order_by(*order)

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


@pool_credits_bp.route("/edit/<int:id>/", methods=["POST", "GET"])
@login_required
@ro_user_only
def update_pool_credit(id):
    from extensions import db

    #    id = int(id)
    entry = db.session.query(PoolCredits).get_or_404(id)
    form = UpdatePoolCreditsForm(obj=entry)
    if current_user.user_type != "admin":
        form.str_regional_office_code.choices = [current_user.ro_code]
    if entry.bool_jv_passed == True:
        flash("JV has already been passed.")
    elif form.validate_on_submit():
        form.populate_obj(entry)

        db.session.commit()

        return redirect(url_for("pool_credits.view_pool_credit", id=id))

    return render_template("pool_credits_edit.html", entry=entry, form=form)


@pool_credits_bp.route("/view/<int:id>/")
@login_required
@ro_user_only
def view_pool_credit(id):
    from extensions import db

    entry = db.session.query(PoolCredits).get_or_404(id)

    return render_template("pool_credits_view.html", entry=entry)


@pool_credits_bp.route("/summary/")
@login_required
@admin_required
def view_pool_credit_summary():
    from extensions import db

    case_unidentified = case(
        (
            PoolCredits.str_regional_office_code.is_(None),
            PoolCredits.credit,
        ),
        else_=0,
    ).label("Unidentified")

    case_identified = case(
        (
            (PoolCredits.str_regional_office_code.is_not(None))
            & (PoolCredits.bool_jv_passed == False),
            PoolCredits.credit,
        ),
        else_=0,
    ).label("Identified")

    case_jv_passed = case(
        (
            PoolCredits.bool_jv_passed == True,
            PoolCredits.credit,
        ),
        else_=0,
    ).label("JV passed")

    summary_query = (
        db.session.query(PoolCredits)
        .with_entities(
            func.date_trunc("month", PoolCredits.value_date),
            func.date_trunc("year", PoolCredits.value_date),
            func.sum(case_unidentified),
            func.sum(case_identified),
            func.sum(case_jv_passed),
        )
        .group_by(
            func.date_trunc("month", PoolCredits.value_date),
            func.date_trunc("year", PoolCredits.value_date),
        )
        .order_by(
            func.date_trunc("month", PoolCredits.value_date).desc(),
            func.date_trunc("year", PoolCredits.value_date).desc(),
        )
        .filter(PoolCredits.value_date >= "2024-10-01")
    )

    return render_template("summary_view.html", query=summary_query)


@pool_credits_bp.route("/daily_jv")
@login_required
@ro_user_only
def daily_jv():

    return render_template("daily_jv_entries.html")


@pool_credits_bp.route("/api/v1/data/daily_jv")
@login_required
@ro_user_only
def daily_jv_entries():

    # query
    daily_jv_entries = (
        db.session.query(FundBankStatement, FundJournalVoucherFlagSheet)
        .join(
            FundJournalVoucherFlagSheet,
            FundBankStatement.description.like(
                "%" + FundJournalVoucherFlagSheet.txt_description + "%"
            ),
        )
        .filter(FundBankStatement.flag_description == "OTHER RECEIPTS")
        .filter(FundBankStatement.value_date >= "2024-10-01")
        .order_by(FundBankStatement.id.desc())
    )

    entries_count = daily_jv_entries.count()

    # search
    search = request.args.get("search[value]")
    if search:
        daily_jv_entries = daily_jv_entries.filter(
            db.or_(
                cast(FundBankStatement.book_date, String).like(f"%{search}%"),
                FundBankStatement.description.ilike(f"%{search}%"),
                cast(FundBankStatement.credit, String).like(f"%{search}%"),
                cast(FundBankStatement.value_date, String).like(f"%{search}%"),
                FundBankStatement.reference_no.ilike(f"%{search}%"),
                FundJournalVoucherFlagSheet.txt_description.ilike(f"%{search}%"),
                FundJournalVoucherFlagSheet.txt_flag.ilike(f"%{search}%"),
                cast(FundJournalVoucherFlagSheet.txt_gl_code, String).like(
                    f"%{search}%"
                ),
                cast(FundJournalVoucherFlagSheet.txt_sl_code, String).like(
                    f"%{search}%"
                ),
            )
        )

    total_filtered = daily_jv_entries.count()

    # sorting
    # order = []
    # i = 0
    # while True:
    #     col_index = request.args.get(f"order[{i}][column]")
    #     if col_index is None:
    #         break
    #     col_name = request.args.get(f"columns[{col_index}][data]")
    #     descending = request.args.get(f"order[{i}][dir]") == "desc"
    #     col = getattr(PoolCredits, col_name)
    #     if descending:
    #         col = col.desc()
    #     order.append(col)
    #     i += 1
    # if order:
    #     entries = entries.order_by(*order)

    # pagination
    start = request.args.get("start", type=int)
    length = request.args.get("length", type=int)
    daily_jv_entries = daily_jv_entries.offset(start).limit(length)

    # response
    return {
        "data": [
            {"bk": asdict(bank_statement), "jv": asdict(journal_flag)}
            for bank_statement, journal_flag in daily_jv_entries
        ],
        "recordsFiltered": total_filtered,
        "recordsTotal": entries_count,
        "draw": request.args.get("draw", type=int),
    }
