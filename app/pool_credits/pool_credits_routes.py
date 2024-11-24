from datetime import datetime
from dataclasses import asdict

from sqlalchemy import (
    and_,
    func,
    case,
    cast,
    String,
    create_engine,
)


from flask import (
    abort,
    flash,
    redirect,
    render_template,
    url_for,
    request,
    current_app,
    send_from_directory,
)
from flask_login import current_user, login_required

import pandas as pd
from . import pool_credits_bp
from .pool_credits_form import UpdatePoolCreditsForm, FilterMonthForm
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


# http://0.0.0.0:8080/pool_credits/api/data/pool_credits_portal/?date_added=2024-08-26T15:11:11Z
# http://0.0.0.0:8080/pool_credits/api/v1/data/pool_credits_portal/?created_date__gte=2024-11-02T20:01
# http://0.0.0.0:8080/pool_credits/api/v1/data/pool_credits_portal/?created_date__gte=2024-11-02T20:00


@pool_credits_bp.route("/api/v1/data/pool_credits_portal/", methods=["GET"])
def pool_credits_portal():
    """
    API endpoint to query PoolCreditsPortal entries.

    The endpoint takes query parameters to filter the results. The following
    parameters are supported:

    - amount_credit__{op}: Filter by amount credit. {op} can be one of gt, lt,
      ge, le, eq, ne.
    - reference_no__{op}: Filter by reference number. {op} can be one of
      contains, startswith, endswith, eq, ne.
    - value_date__{op}: Filter by value date. {op} can be one of gt, lt, ge,
      le, eq, ne.
    - remitter__{op}: Filter by remitter. {op} can be one of contains,
      startswith, endswith, eq, ne.
    - created_date__{op}: Filter by created date. {op} can be one of gt, lt,
      ge, le, eq, ne.
    - id__{op}: Filter by id. {op} can be one of eq, ne.

    The response will be a JSON object with the following keys:

    - recordsTotal: The total number of records.
    - data: A list of dictionaries, each representing a PoolCreditsPortal entry.

    Example:
    curl -X GET "http://localhost:8080/pool_credits/api/v1/data/pool_credits_portal/?amount_credit__gt=1000&created_date__ge=2024-08-26T15:11:11Z"
    """

    query = db.session.query(PoolCreditsPortal)
    query_params = request.args

    filters = {}
    for key, value in query_params.items():
        # Split the key into the column name and the operator
        key_components = key.split("__", 1)
        param_name = key_components[0]
        operator = key_components[1] if len(key_components) > 1 else "gte"

        # Store the parameter name and value along with the operator in the
        # filters dictionary
        filters[param_name] = {"operator": operator, "value": value}

    # Define a dictionary to map the parameter names to the corresponding
    # column names in the PoolCreditsPortal table
    filters_to_apply: dict[str, str] = {
        "amount_credit": "amount_credit",
        "reference_no": "txt_reference_number",
        "value_date": "date_value_date",
        "remitter": "txt_name_of_remitter",
        "created_date": "date_created_date",
        "id": "id",
    }

    # Iterate over the filters and apply them to the query
    for filter_key, column_name in filters_to_apply.items():
        filter_value = get_value(filters, filter_key)
        if filter_value:
            query = dynamic_query_column(query, column_name, filter_value)

    # Count the total number of records matching the query
    total_records = query.count()

    # Fetch the data from the query and convert it to a list of dictionaries
    data = [asdict(entry) for entry in query]

    # Return a JSON response with the total records and the data
    return {
        "recordsTotal": total_records,
        "data": data,
    }


def get_value(params, param_name):
    """Return the value of a parameter from the request query string."""
    param = params.get(param_name)
    return param if param is not None else False


def dynamic_query_column(entries, column_name, params):
    operator = params.get("operator", "gte")
    value = params["value"]

    column_attr = getattr(PoolCreditsPortal, column_name)

    if operator == "eq":
        entries = entries.filter(column_attr == value)
    elif operator == "gt":
        entries = entries.filter(column_attr > value)
    elif operator == "gte":
        entries = entries.filter(column_attr >= value)
    elif operator == "lt":
        entries = entries.filter(column_attr < value)
    elif operator == "lte":
        entries = entries.filter(column_attr <= value)
    elif operator == "like":
        entries = entries.filter(column_attr.like(f"%{value}%"))
    elif operator == "ilike":
        entries = entries.filter(column_attr.ilike(f"%{value}%"))
    elif operator == "not":
        entries = entries.filter(column_attr != value)

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

    elif status == "confirmed":
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


@pool_credits_bp.route("/identified/")
@login_required
@ro_user_only
def identified_entries():

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


@pool_credits_bp.route("/download/", methods=["POST", "GET"])
@login_required
@ro_user_only
def download_monthly():

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
    )
    filter_month = daily_jv_entries.with_entities(FundBankStatement.period).distinct()

    form = FilterMonthForm()
    list_period = [datetime.strptime(item[0], "%Y-%m") for item in filter_month]
    list_period.sort(reverse=True)
    form.month.choices = [month.strftime("%B-%y") for month in list_period]

    if form.validate_on_submit():
        filter_period = datetime.strptime(form.month.data, "%B-%y")
        entries = daily_jv_entries.filter(
            FundBankStatement.period == filter_period.strftime("%Y-%m")
        )

        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
        conn = engine.connect()
        df_funds = pd.read_sql_query(entries.statement, conn)
        df_funds = df_funds[
            [
                "book_date",
                "description",
                "credit",
                "value_date",
                "reference_no",
                "txt_description",
                "txt_flag",
                "txt_gl_code",
                "txt_sl_code",
            ]
        ]

        datetime_string = datetime.now()
        with pd.ExcelWriter(
            f"download_data/pool_credits/HDFC_Pool_credits_{datetime_string:%d%m%Y%H%M%S}.xlsx"
        ) as writer:
            df_funds.to_excel(writer, sheet_name="Inflow", index=False)
            format_workbook = writer.book
            format_currency = format_workbook.add_format({"num_format": "##,##,#0.00"})

            format_worksheet = writer.sheets["Inflow"]
            format_worksheet.set_column("C:C", 11, format_currency)

            format_worksheet.autofit()
            format_worksheet.autofilter("A1:I2")
            format_worksheet.freeze_panes(1, 0)

        return send_from_directory(
            directory="download_data/pool_credits/",
            path=f"HDFC_Pool_credits_{datetime_string:%d%m%Y%H%M%S}.xlsx",
            download_name=f"HDFC_Pool_credits_{filter_period.strftime("%B-%y")}.xlsx",
            as_attachment=True,
        )

    return render_template("download_monthly.html", form=form)
