from datetime import datetime
from decimal import Decimal
from io import BytesIO


from flask import (
    abort,
    flash,
    redirect,
    render_template,
    url_for,
    request,
    send_file,
)
from flask_login import current_user, login_required

import pandas as pd
from . import pool_credits_bp
from .pool_credits_form import UpdatePoolCreditsForm, FilterMonthForm
from .pool_credits_model import (
    PoolCredits,
    PoolCreditsPortal,
    PoolCreditsJournalVoucher,
)

from app.funds.funds_model import FundBankStatement, FundJournalVoucherFlagSheet

from extensions import db
from set_view_permissions import ro_user_only, admin_required


@pool_credits_bp.route("/<string:status>/", methods=["POST", "GET"])
@login_required
@ro_user_only
def pool_credits_list_identified_api(status):
    if request.method == "POST":
        list_pool_keys = request.form.getlist("pool_keys")
        list_pool_keys = [int(key) for key in list_pool_keys]
        if list_pool_keys:
            update_stmt = (
                db.update(PoolCredits)
                .where(PoolCredits.id.in_(list_pool_keys))
                .values(bool_jv_passed=True)
            )
            result = db.session.execute(update_stmt)
            db.session.commit()
            flash(f"{result.rowcount} rows updated.")

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
      gte, lte, eq, ne.
    - reference_no__{op}: Filter by reference number. {op} can be one of
      like, ilike, eq, ne.
    - value_date__{op}: Filter by value date. {op} can be one of gt, lt, gte,
      lte, eq, ne.
    - remitter__{op}: Filter by remitter. {op} can be one of like, ilike, eq, ne.
    - created_date__{op}: Filter by created date. {op} can be one of gt, lt,
      gte, lte, eq, ne.
    - id__{op}: Filter by id. {op} can be one of eq, ne.

    The response will be a JSON object with the following keys:

    - recordsTotal: The total number of records.
    - data: A list of dictionaries, each representing a PoolCreditsPortal entry.

    Example:
    curl -X GET "http://localhost:8080/pool_credits/api/v1/data/pool_credits_portal/?amount_credit__gt=1000&created_date__gte=2024-08-26T15:11:11Z"
    """

    query = db.select(
        PoolCreditsPortal.id,
        PoolCreditsPortal.date_value_date,
        PoolCreditsPortal.amount_credit,
        PoolCreditsPortal.txt_name_of_remitter,
        PoolCreditsPortal.date_created_date,
        db.literal("000100").label("office_code"),
        PoolCreditsPortal.txt_reference_number.label("reference_number"),
    )
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
    total_records = db.session.scalar(
        db.select(db.func.count()).select_from(query.subquery())
    )

    # Fetch the data from the query and convert it to a list of dictionaries
    result = db.session.execute(query).mappings()
    data = [dict(row) for row in result]

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
    col_type = column_attr.type

    # ✅ Cast based on column type
    if isinstance(col_type, db.Numeric):
        value = Decimal(value)

    elif isinstance(col_type, db.DateTime):
        value = datetime.fromisoformat(value)  # "2024-05-01T12:00:00"

    elif isinstance(col_type, db.Date):
        value = datetime.fromisoformat(value).date()  # "2024-05-01"

    if operator == "eq":
        entries = entries.where(column_attr == value)
    elif operator == "gt":
        entries = entries.where(column_attr > value)
    elif operator == "gte":
        entries = entries.where(column_attr >= value)
    elif operator == "lt":
        entries = entries.where(column_attr < value)
    elif operator == "lte":
        entries = entries.where(column_attr <= value)
    elif operator == "like":
        entries = entries.where(column_attr.like(f"%{value}%"))
    elif operator == "ilike":
        entries = entries.where(column_attr.ilike(f"%{value}%"))
    elif operator == "ne":
        entries = entries.where(column_attr != value)

    return entries


@pool_credits_bp.route("/api/v1/data/<string:status>/", methods=["GET"])
@login_required
@ro_user_only
def get_data(status):
    START_DATE = datetime(2024, 10, 1)
    base_filter = [PoolCredits.value_date >= START_DATE]

    stmt = db.select(
        PoolCredits.id,
        PoolCredits.str_regional_office_code,
        db.func.to_char(PoolCredits.book_date, "YYYY-MM-DD").label("book_date"),
        db.func.to_char(PoolCredits.value_date, "YYYY-MM-DD").label("value_date"),
        PoolCredits.credit,
        PoolCredits.value_date,
        PoolCredits.description,
        PoolCredits.reference_no,
    ).where(*base_filter)
    if status == "unidentified":
        stmt = stmt.where(PoolCredits.str_regional_office_code.is_(None))

    elif status == "confirmed":
        stmt = stmt.where(
            (PoolCredits.str_regional_office_code.is_not(None))
            & (PoolCredits.bool_jv_passed.is_(False))
        )
    elif status == "jv_passed":
        stmt = stmt.where(
            (PoolCredits.str_regional_office_code.is_not(None))
            & (PoolCredits.bool_jv_passed.is_(True))
        )

    # order by date of creation and ID descending order
    # entries = entries.order_by(
    #     PoolCredits.date_created_date.desc(), PoolCredits.id.desc()
    # )

    # filter only entries uploaded after Oct-2024

    entries_count = db.session.scalar(
        db.select(db.func.count()).select_from(stmt.subquery())
    )

    # search filter
    search = request.args.get("search[value]")
    if search:
        search_terms = search.strip().split()  # split by spaces
        for term in search_terms:
            stmt = stmt.where(
                db.or_(
                    db.cast(PoolCredits.book_date, db.String).like(f"%{term}%"),
                    PoolCredits.description.ilike(f"%{term}%"),
                    db.cast(PoolCredits.credit, db.String).like(f"%{term}%"),
                    db.cast(PoolCredits.debit, db.String).like(f"%{term}%"),
                    db.cast(PoolCredits.value_date, db.String).like(f"%{term}%"),
                    PoolCredits.reference_no.ilike(f"%{term}%"),
                    db.cast(PoolCredits.str_regional_office_code, db.String).ilike(
                        f"%{term}%"
                    ),
                )
            )

    total_filtered = db.session.scalar(
        db.select(db.func.count()).select_from(stmt.subquery())
    )

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
        stmt = stmt.order_by(*order)

    # pagination
    start = request.args.get("start", type=int)
    length = request.args.get("length", type=int)
    stmt = stmt.offset(start).limit(length)
    entries = db.session.execute(stmt).mappings()
    # response
    return {
        "data": [dict(entry) for entry in entries],
        "recordsFiltered": total_filtered,
        "recordsTotal": entries_count,
        "draw": request.args.get("draw", type=int),
    }


@pool_credits_bp.route("/edit/<int:id>/", methods=["POST", "GET"])
@login_required
@ro_user_only
def update_pool_credit(id):
    entry = db.get_or_404(PoolCredits, id)
    form = UpdatePoolCreditsForm(obj=entry)
    if current_user.user_type != "admin":
        form.str_regional_office_code.choices = [current_user.ro_code]
    elif current_user.user_type == "admin":
        ro_choices_list = db.select(
            db.func.distinct(PoolCreditsJournalVoucher.str_regional_office_code)
        ).order_by(PoolCreditsJournalVoucher.str_regional_office_code)
        ro_choices = db.session.scalars(ro_choices_list)
        form.str_regional_office_code.choices = [choice for choice in ro_choices]
    if entry.bool_jv_passed:
        flash("JV has already been passed.")
    elif form.validate_on_submit():
        form.populate_obj(entry)
        db.session.commit()
        # AJAX success response
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return {"success": True}

        return redirect(url_for("pool_credits.view_pool_credit", id=id))

    template = (
        "_edit_modal_form.html"
        if request.headers.get("X-Requested-With") == "XMLHttpRequest"
        else "pool_credits_edit.html"
    )

    return render_template(template, entry=entry, form=form)


@pool_credits_bp.route("/view/<int:id>/")
@login_required
@ro_user_only
def view_pool_credit(id):
    entry = db.get_or_404(PoolCredits, id)

    return render_template("pool_credits_view.html", entry=entry)


@pool_credits_bp.route("/summary/")
@login_required
@admin_required
def view_pool_credit_summary():
    case_unidentified = db.func.sum(
        db.case(
            (
                PoolCredits.str_regional_office_code.is_(None),
                PoolCredits.credit,
            ),
            else_=0,
        )
    ).label("Unidentified")

    case_identified = db.func.sum(
        db.case(
            (
                (PoolCredits.str_regional_office_code.is_not(None))
                & (PoolCredits.bool_jv_passed.is_(False)),
                PoolCredits.credit,
            ),
            else_=0,
        )
    ).label("Identified")

    case_jv_passed = db.func.sum(
        db.case(
            (
                PoolCredits.bool_jv_passed.is_(True),
                PoolCredits.credit,
            ),
            else_=0,
        )
    ).label("JV passed")

    START_DATE = datetime(2024, 10, 1)
    stmt = (
        db.select(PoolCredits.month, case_unidentified, case_identified, case_jv_passed)
        .group_by(
            PoolCredits.month,
        )
        .order_by(
            PoolCredits.month.desc(),
        )
        .where(PoolCredits.value_date >= START_DATE)
    )
    summary_query = db.session.execute(stmt)
    return render_template("summary_view.html", query=summary_query)


@pool_credits_bp.route("/daily_jv/")
@pool_credits_bp.route("/identified/")
@login_required
@ro_user_only
def identified_entries():
    return render_template("daily_jv_entries_v2.html")


@pool_credits_bp.route("/api/v2/data/daily_jv")
@login_required
@ro_user_only
def daily_jv_entries_v2():
    # query
    START_DATE = datetime(2024, 10, 1)
    base_filters = [
        FundBankStatement.flag_description == "OTHER RECEIPTS",
        FundBankStatement.value_date >= START_DATE,
    ]
    query = (
        db.select(
            db.func.to_char(FundBankStatement.book_date, "YYYY-MM-DD").label(
                "book_date"
            ),
            FundBankStatement.description,
            FundBankStatement.credit,
            db.func.to_char(FundBankStatement.value_date, "YYYY-MM-DD").label(
                "value_date"
            ),
            FundBankStatement.reference_no,
            FundJournalVoucherFlagSheet.txt_description,
            FundJournalVoucherFlagSheet.txt_flag,
            FundJournalVoucherFlagSheet.txt_gl_code,
            FundJournalVoucherFlagSheet.txt_sl_code,
        )
        .join(
            FundBankStatement.flag,
        )
        .where(*base_filters)
        .order_by(FundBankStatement.id.desc())
    )

    entries_count = db.session.scalar(
        db.select(db.func.count(FundBankStatement.id))
        .join(
            FundBankStatement.flag,
        )
        .where(*base_filters)
    )

    # search
    search = request.args.get("search[value]")
    if search:
        search_terms = search.strip().split()  # split by spaces
        for term in search_terms:
            query = query.where(
                db.or_(
                    db.cast(FundBankStatement.book_date, db.String).like(f"%{term}%"),
                    FundBankStatement.description.ilike(f"%{term}%"),
                    db.cast(FundBankStatement.credit, db.String).like(f"%{term}%"),
                    db.cast(FundBankStatement.value_date, db.String).like(f"%{term}%"),
                    FundBankStatement.reference_no.ilike(f"%{term}%"),
                    FundJournalVoucherFlagSheet.txt_description.ilike(f"%{term}%"),
                    FundJournalVoucherFlagSheet.txt_flag.ilike(f"%{term}%"),
                    db.cast(FundJournalVoucherFlagSheet.txt_gl_code, db.String).like(
                        f"%{term}%"
                    ),
                    db.cast(FundJournalVoucherFlagSheet.txt_sl_code, db.String).like(
                        f"%{term}%"
                    ),
                )
            )

    total_filtered = db.session.scalar(
        db.select(db.func.count()).select_from(query.subquery())
    )

    # pagination
    start = request.args.get("start", type=int)
    length = request.args.get("length", type=int)
    paginated_query = query.offset(start).limit(length)
    rows = db.session.execute(paginated_query).mappings()
    data = [dict(row) for row in rows]

    # response
    return {
        "data": data,
        "recordsFiltered": total_filtered,
        "recordsTotal": entries_count,
        "draw": request.args.get("draw", type=int),
    }


@pool_credits_bp.route("/download/", methods=["POST", "GET"])
@login_required
@ro_user_only
def download_monthly():
    START_DATE = datetime(2024, 10, 1)
    base_filters = [
        FundBankStatement.flag_description == "OTHER RECEIPTS",
        FundBankStatement.value_date >= START_DATE,
    ]
    query = (
        db.select(
            db.func.to_char(FundBankStatement.book_date, "YYYY-MM-DD").label(
                "book_date"
            ),
            FundBankStatement.description,
            FundBankStatement.credit,
            db.func.to_char(FundBankStatement.value_date, "YYYY-MM-DD").label(
                "value_date"
            ),
            FundBankStatement.reference_no,
            FundJournalVoucherFlagSheet.txt_description.label("pattern"),
            FundJournalVoucherFlagSheet.txt_flag.label("flag"),
            FundJournalVoucherFlagSheet.txt_gl_code.label("gl_code"),
            FundJournalVoucherFlagSheet.txt_sl_code.label("sl_code"),
        )
        .join(
            FundBankStatement.flag,
        )
        .where(*base_filters)
        .order_by(FundBankStatement.id.desc())
    )

    period_query = (
        db.select(
            db.func.distinct(FundBankStatement.period),
        )
        .join(
            FundBankStatement.flag,
        )
        .where(*base_filters)
        .order_by(FundBankStatement.period.desc())
    )

    periods = db.session.scalars(period_query)

    form = FilterMonthForm()
    list_period = [datetime.strptime(p, "%Y-%m") for p in periods]
    form.month.choices = [month.strftime("%B-%y") for month in list_period]

    if form.validate_on_submit():
        filter_period = datetime.strptime(form.month.data, "%B-%y")
        entries = query.where(
            FundBankStatement.period == filter_period.strftime("%Y-%m")
        )
        with db.engine.connect() as conn:
            df_funds = pd.read_sql(entries, conn)

        output = BytesIO()
        with pd.ExcelWriter(output) as writer:
            df_funds.to_excel(writer, sheet_name="Inflow", index=False)
            format_workbook = writer.book
            format_currency = format_workbook.add_format({"num_format": "##,##,#0.00"})

            format_worksheet = writer.sheets["Inflow"]
            format_worksheet.set_column("C:C", 11, format_currency)

            format_worksheet.autofit()
            format_worksheet.autofilter("A1:I2")
            format_worksheet.freeze_panes(1, 0)
        output.seek(0)
        return send_file(
            output,
            download_name=f"HDFC_Pool_credits_{filter_period.strftime('%B-%y')}.xlsx",
            as_attachment=True,
        )

    return render_template("download_monthly.html", form=form)
