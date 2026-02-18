import datetime
from dateutil.relativedelta import relativedelta


from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import (
    func,
    and_,
)

# from sqlalchemy.dialects.postgresql import insert


from app.funds import funds_bp
from app.funds.funds_form import (
    AmountGivenToInvestmentForm,
    DailySummaryForm,
    FlagForm,
    FundsModifyDatesForm,
    MajorOutgoForm,
    UploadFileForm,
    FundsDeleteForm,
    generate_outflow_form,
)
from app.funds.funds_model import (
    FundAmountGivenToInvestment,
    FundBankAccountNumbers,
    FundBankStatement,
    FundDailyOutflow,
    FundDailySheet,
    FundFlagSheet,
    FundMajorOutgo,
)

from .funds_utils import (
    get_daily_sheet,
    get_outflow_data,
    get_inflow,
    get_previous_day_closing_balance_refactored,
    get_outflow,
    get_inflow_total,
    get_daily_summary_refactored,
    get_ibt_details,
    populate_outflow_form_data,
    handle_outflow_form_submission,
    enable_update,
    fetch_inflow,
    fetch_outflow_labels,
    fetch_prev_daily_sheet,
)
from .funds_services import BankStatementService

from app.coinsurance.coinsurance_model import CoinsuranceReceipts
from app.pool_credits.pool_credits_model import PoolCredits, PoolCreditsPortal

from extensions import db

from set_view_permissions import fund_managers

# outflow_labels_old = [
#     "CITI HEALTH",
#     "AXIS HEALTH",
#     "MRO1 HEALTH",
#     "AXIS NEFT",
#     "CITI NEFT",
#     "TNCMCHIS",
#     "AXIS CENTRALISED CHEQUE",
#     "AXIS CENTRALISED CHEQUE 521",
#     "AXIS TDS RO",
#     "PENSION PAYMENT",
#     "GRATUITY",
#     "GRATUITY IDFC FIRST",
#     "AXIS GST",
#     "RO NAGPUR CROP",
#     "CITI OMP",
#     "HDFC Lien",
#     "Other payments",
# ]
# outflow_amounts = [
#     f"amount_{field.lower().replace(' ', '_')}" for field in outflow_labels
# ]


# @funds_bp.route("/outflow/labels")
# @login_required
# @fund_managers
# def populate_outflow_model():
#     insert_stmt = (
#         insert(FundOutflowLabel)
#         .values([{"outflow_label": label} for label in outflow_labels_old])
#         .on_conflict_do_nothing(index_elements=["outflow_label"])
#     )
#     result = db.session.execute(insert_stmt)
#     db.session.commit()

#     rows_inserted = result.rowcount

#     return f"{rows_inserted} rows inserted"


@funds_bp.route("/api/v2/data/funds", methods=["GET"])
@login_required
@fund_managers
def funds_home_data_v2():
    # Step 1: aggregate outflows by date
    outflow_agg = (
        db.select(
            FundDailyOutflow.outflow_date.label("date"),
            func.sum(FundDailyOutflow.outflow_amount).label("outflow_amount"),
        )
        .group_by(FundDailyOutflow.outflow_date)
        .subquery()
    )

    # Step 2: daily sheet with lag(prev_hdfc_balance)
    daily_with_prev = (
        db.select(
            FundDailySheet.date_current_date.label("date"),
            FundDailySheet.float_amount_given_to_investments.label("investment_given"),
            FundDailySheet.float_amount_taken_from_investments.label(
                "investment_taken"
            ),
            FundDailySheet.float_amount_investment_closing_balance.label(
                "investment_closing_balance"
            ),
            FundDailySheet.float_amount_hdfc_closing_balance.label(
                "hdfc_closing_balance"
            ),
            func.lag(FundDailySheet.float_amount_hdfc_closing_balance)
            .over(order_by=FundDailySheet.date_current_date)
            .label("prev_hdfc_balance"),
        )
    ).subquery()

    # Step 3: main query anchored on FundBankStatement
    query = (
        db.select(
            FundBankStatement.date_uploaded_date.label("date_uploaded_date"),
            (
                func.sum(FundBankStatement.credit)
                + func.coalesce(daily_with_prev.c.prev_hdfc_balance, 0)
                - func.coalesce(daily_with_prev.c.investment_taken, 0)
            ).label("credit"),
            func.coalesce(outflow_agg.c.outflow_amount, 0).label("outflow"),
            (
                func.sum(FundBankStatement.credit)
                + func.coalesce(daily_with_prev.c.prev_hdfc_balance, 0)
                - func.coalesce(daily_with_prev.c.investment_taken, 0)
                - func.coalesce(outflow_agg.c.outflow_amount, 0)
            ).label("net_cashflow"),
            func.coalesce(daily_with_prev.c.investment_given, 0).label(
                "investment_given"
            ),
            func.coalesce(daily_with_prev.c.investment_taken, 0).label(
                "investment_taken"
            ),
            (
                func.coalesce(daily_with_prev.c.investment_given, 0)
                - func.coalesce(daily_with_prev.c.investment_taken, 0)
            ).label("net_investment"),
            func.coalesce(daily_with_prev.c.investment_closing_balance, 0).label(
                "investment_closing_balance"
            ),
            func.coalesce(daily_with_prev.c.hdfc_closing_balance, 0).label(
                "hdfc_closing_balance"
            ),
        )
        .outerjoin(
            daily_with_prev,
            FundBankStatement.date_uploaded_date == daily_with_prev.c.date,
        )
        .outerjoin(
            outflow_agg,
            FundBankStatement.date_uploaded_date == outflow_agg.c.date,
        )
        .group_by(
            FundBankStatement.date_uploaded_date,
            daily_with_prev.c.prev_hdfc_balance,
            daily_with_prev.c.investment_given,
            daily_with_prev.c.investment_taken,
            daily_with_prev.c.investment_closing_balance,
            daily_with_prev.c.hdfc_closing_balance,
            outflow_agg.c.outflow_amount,
        )
        .order_by(FundBankStatement.date_uploaded_date.desc())
    )

    count_query = db.select(func.count()).select_from(query.subquery())
    total_records = db.session.scalar(count_query)
    records_filtered = total_records

    start = request.args.get("start", type=int)
    length = request.args.get("length", type=int)

    paginated_query = query.offset(start).limit(length)
    rows = db.session.execute(paginated_query).mappings()
    data = [dict(row) for row in rows]

    return {
        "draw": request.args.get("draw", type=int),
        "recordsTotal": total_records,
        "recordsFiltered": records_filtered,
        "data": data,
    }


@funds_bp.route("/home")
@login_required
@fund_managers
def funds_home_api():
    return render_template("funds_home_api_v2.html")


@funds_bp.route("/bank_statement/upload/", methods=["GET", "POST"])
@login_required
@fund_managers
def upload_bank_statement():
    """
    Upload and process a bank statement (.xlsx format):
    - Parse the uploaded file
    - Normalize data
    - Check closing balance accuracy
    - Insert into relevant DB tables
    """
    form = UploadFileForm()

    if not form.validate_on_submit():
        return render_template(
            "funds_form.html",
            form=form,
            title="Upload bank statement (in .xlsx file format)",
        )
    service = BankStatementService(db.session)
    try:
        service.process(
            form.data["file_upload"],
            current_user,
        )

        return redirect(
            url_for(
                "funds.enter_outflow",
                date_string=datetime.date.today().strftime("%d%m%Y"),
            )
        )

    except Exception as e:
        flash(f"Error processing bank statement: {str(e)}")
        return render_template(
            "funds_form.html",
            form=form,
            title="Upload bank statement (in .xlsx file format)",
        )


@funds_bp.route("/bank_statement/view/<string:date_string>/", methods=["GET"])
@login_required
@fund_managers
def view_bank_statement(date_string):
    param_date = datetime.datetime.strptime(date_string, "%d%m%Y")
    query = db.session.scalars(
        db.select(FundBankStatement)
        .where(FundBankStatement.date_uploaded_date == param_date)
        .order_by(FundBankStatement.id)
    )

    column_names = [
        "date_uploaded_date",
        "book_date",
        "description",
        "ledger_balance",
        "credit",
        "debit",
        "value_date",
        "reference_no",
        "flag_description",
    ]
    return render_template(
        "view_bank_statement.html", query=query, column_names=column_names
    )


@funds_bp.route("/flags/", methods=["GET"])
@login_required
@fund_managers
def view_flag_sheet():
    query = db.session.scalars(
        db.select(FundFlagSheet).order_by(FundFlagSheet.flag_description)
    )

    column_names = [
        "flag_description",
        "flag_reg_exp",
    ]
    return render_template(
        "flag_view_sheet.html", query=query, column_names=column_names
    )


@funds_bp.route("/flags/add", methods=["POST", "GET"])
@login_required
@fund_managers
def add_flag_entry():
    form = FlagForm()
    if form.validate_on_submit():
        flag = FundFlagSheet()
        form.populate_obj(flag)
        db.session.add(flag)
        db.session.commit()
        return redirect(url_for("funds.view_flag_sheet"))

    return render_template("funds_form.html", form=form, title="Add flag entry")


@funds_bp.route("/flags/edit/<int:flag_id>", methods=["POST", "GET"])
@login_required
@fund_managers
def edit_flag_entry(flag_id):
    flag = db.get_or_404(FundFlagSheet, flag_id)
    form = FlagForm(obj=flag)
    if form.validate_on_submit():
        form.populate_obj(flag)
        db.session.commit()
        return redirect(url_for("funds.view_flag_sheet"))

    return render_template("funds_form.html", form=form, title="Edit flag entry")


@funds_bp.route("/outflow/edit/<string:date_string>/", methods=["GET", "POST"])
@login_required
@fund_managers
def enter_outflow(date_string):
    param_date = datetime.datetime.strptime(date_string, "%d%m%Y")

    inflow = fetch_inflow(param_date)
    daily_sheet, investment_list, list_outgo = get_outflow_data(param_date)
    prev_daily_sheet = fetch_prev_daily_sheet(param_date)
    outflow_labels = fetch_outflow_labels()

    DynamicOutflowForm = generate_outflow_form(outflow_labels)
    form = DynamicOutflowForm()

    if form.validate_on_submit():
        handle_outflow_form_submission(form, param_date, daily_sheet)
        return redirect(url_for("funds.add_remarks", date_string=date_string))

    populate_outflow_form_data(form, param_date, daily_sheet)

    return render_template(
        "enter_outflow.html",
        form=form,
        display_date=param_date,
        investment_list=investment_list,
        list_outgo=list_outgo,
        daily_sheet=daily_sheet,
        inflow=inflow,
        prev_daily_sheet=prev_daily_sheet,
    )


@funds_bp.route("/remarks/edit/<string:date_string>/", methods=["GET", "POST"])
@login_required
@fund_managers
def add_remarks(date_string):
    param_date = datetime.datetime.strptime(date_string, "%d%m%Y")
    flags = db.select(
        FundFlagSheet.flag_description.distinct().label("flag_description")
    ).subquery()
    inflow = db.session.execute(
        db.select(
            flags.c.flag_description.label("flag_description"),
            db.func.sum(db.func.coalesce(FundBankStatement.credit, 0)).label("amount"),
        )
        .select_from(flags)
        .outerjoin(
            FundBankStatement,
            and_(
                flags.c.flag_description == FundBankStatement.flag_description,
                FundBankStatement.date_uploaded_date == param_date,
            ),
        )
        .where(
            flags.c.flag_description.not_in(["HDFC CLOSING BAL", "HDFC OPENING BAL"]),
        )
        .group_by(flags.c.flag_description)
    ).all()
    outflow = db.session.execute(
        db.select(
            FundDailyOutflow.normalized_description,
            db.func.sum(FundDailyOutflow.outflow_amount).label("amount"),
        )
        .where(FundDailyOutflow.outflow_date == param_date)
        .group_by(FundDailyOutflow.normalized_description)
    ).all()
    daily_sheet = get_daily_sheet(param_date)
    prev_daily_sheet = db.session.scalar(
        db.select(FundDailySheet)
        .where(FundDailySheet.date_current_date < param_date)
        .order_by(FundDailySheet.date_current_date.desc())
    )
    form = DailySummaryForm(obj=daily_sheet)
    if form.validate_on_submit():
        form.populate_obj(daily_sheet)
        db.session.commit()
        return redirect(
            url_for(
                "funds.ibt",
                date_string=date_string,
                pdf="False",
            )
        )

    return render_template(
        "add_remarks.html",
        form=form,
        display_date=param_date,
        daily_sheet=daily_sheet,
        prev_daily_sheet=prev_daily_sheet,
        inflow=inflow,
        outflow=outflow,
    )


@funds_bp.route("/ibt/<string:date_string>/<string:pdf>", methods=["GET"])
@login_required
@fund_managers
def ibt(date_string, pdf="False"):
    param_date = datetime.datetime.strptime(date_string, "%d%m%Y")

    daily_sheet = get_daily_sheet(param_date)
    prev_daily_sheet = db.session.scalar(
        db.select(FundDailySheet)
        .where(FundDailySheet.date_current_date < param_date)
        .order_by(FundDailySheet.date_current_date.desc())
    )

    flags = db.select(
        FundFlagSheet.flag_description.distinct().label("flag_description")
    ).subquery()
    inflow = db.session.execute(
        db.select(
            flags.c.flag_description.label("flag_description"),
            db.literal("HDFC").label("bank_name"),
            db.literal("RTGS").label("type"),
            db.literal("").label("account_number"),
            db.func.sum(db.func.coalesce(FundBankStatement.credit, 0)).label("amount"),
        )
        .select_from(flags)
        .outerjoin(
            FundBankStatement,
            and_(
                flags.c.flag_description == FundBankStatement.flag_description,
                FundBankStatement.date_uploaded_date == param_date,
            ),
        )
        .where(
            flags.c.flag_description.not_in(
                ["Drawn from investment", "HDFC CLOSING BAL", "HDFC OPENING BAL"]
            ),
        )
        .group_by(flags.c.flag_description)
    ).all()

    outflow_other_than_axis_neft = (
        db.select(
            FundDailyOutflow.normalized_description.label("normalized_description"),
            FundBankAccountNumbers.bank_name,
            FundBankAccountNumbers.bank_type,
            FundBankAccountNumbers.bank_account_number,
            db.func.coalesce(db.func.sum(FundDailyOutflow.outflow_amount), 0).label(
                "amount"
            ),
        )
        .outerjoin(
            FundBankAccountNumbers,
            FundBankAccountNumbers.outflow_description
            == FundDailyOutflow.normalized_description,
        )
        .where(
            and_(
                FundDailyOutflow.outflow_date == param_date,
                FundDailyOutflow.normalized_description.not_in(
                    ["AXIS NEFT", "MRO1 HEALTH", "TNCMCHIS"]
                ),
            )
        )
        .group_by(
            FundDailyOutflow.normalized_description,
            FundBankAccountNumbers.bank_name,
            FundBankAccountNumbers.bank_type,
            FundBankAccountNumbers.bank_account_number,
        )
        .order_by(FundDailyOutflow.normalized_description)
    )

    outflow_axis_neft = db.select(
        db.literal("AXIS NEFT").label("normalized_description"),
        db.literal("AXIS").label("bank_name"),
        db.literal("AXIS NEFT").label("bank_type"),
        db.literal("914020047605659").label("bank_account_number"),
        db.func.coalesce(db.func.sum(FundDailyOutflow.outflow_amount), 0).label(
            "amount"
        ),
    ).where(
        and_(
            FundDailyOutflow.outflow_date == param_date,
            FundDailyOutflow.normalized_description.in_(
                ["AXIS NEFT", "MRO1 HEALTH", "TNCMCHIS"]
            ),
        )
    )
    outflow = db.session.execute(
        db.union_all(outflow_other_than_axis_neft, outflow_axis_neft)
    ).all()

    return render_template(
        "ibt.html",
        display_date=param_date,
        datetime=datetime,
        daily_sheet=daily_sheet,
        prev_daily_sheet=prev_daily_sheet,
        pdf=pdf,
        inflow=inflow,
        outflow=outflow,
    )


@funds_bp.route("/daily_summary/<string:date_string>/<string:pdf>", methods=["GET"])
@login_required
@fund_managers
def daily_summary(date_string, pdf="False"):
    param_date = datetime.datetime.strptime(date_string, "%d%m%Y")
    daily_sheet = get_daily_sheet(param_date)
    prev_daily_sheet = db.session.scalar(
        db.select(FundDailySheet)
        .where(FundDailySheet.date_current_date < param_date)
        .order_by(FundDailySheet.date_current_date.desc())
    )

    prev_year_date = param_date - relativedelta(years=1)
    prev_year_daily_sheet = db.session.scalar(
        db.select(FundDailySheet)
        .where(FundDailySheet.date_current_date <= prev_year_date)
        .order_by(FundDailySheet.date_current_date.desc())
    )
    flags = db.select(
        FundFlagSheet.flag_description.distinct().label("flag_description")
    ).subquery()
    inflow = db.session.execute(
        db.select(
            flags.c.flag_description.label("flag_description"),
            db.func.sum(db.func.coalesce(FundBankStatement.credit, 0)).label("amount"),
        )
        .select_from(flags)
        .outerjoin(
            FundBankStatement,
            and_(
                flags.c.flag_description == FundBankStatement.flag_description,
                FundBankStatement.date_uploaded_date == param_date,
            ),
        )
        .where(
            flags.c.flag_description.not_in(
                ["Drawn from investment", "HDFC CLOSING BAL", "HDFC OPENING BAL"]
            ),
        )
        .group_by(flags.c.flag_description)
    ).all()

    outflow = db.session.execute(
        db.select(
            FundDailyOutflow.normalized_description,
            db.func.sum(FundDailyOutflow.outflow_amount).label("amount"),
        )
        .where(FundDailyOutflow.outflow_date == param_date)
        .group_by(FundDailyOutflow.normalized_description)
    ).all()

    return render_template(
        "daily_summary.html",
        display_date=param_date,
        datetime=datetime,
        daily_sheet=daily_sheet,
        prev_daily_sheet=prev_daily_sheet,
        pdf=pdf,
        inflow=inflow,
        outflow=outflow,
        prev_year_daily_sheet=prev_year_daily_sheet,
        prev_year_date=prev_year_date,
    )


# @funds_bp.route("/flags/upload", methods=["GET", "POST"])
# @login_required
# @fund_managers
# def upload_flag_sheet():
#     # uploading preconfigured flag sheet from CSV file
#     form = UploadFileForm()
#     if form.validate_on_submit():
#         flag_sheet = form.data["file_upload"]
#         df_flag_sheet = pd.read_excel(flag_sheet)

#         df_flag_sheet["date_created_date"] = datetime.datetime.now()
#         df_flag_sheet["created_by"] = current_user.username
#         # try:
#         df_flag_sheet.to_sql(
#             "fund_flag_sheet",
#             db.engine,
#             if_exists="append",
#             index=False,
#         )
#         flash("Flag sheet has been uploaded successfully.")
#     return render_template(
#         "upload_file_template.html", form=form, title="Upload flag sheet"
#     )


# @funds_bp.route("/upload_investment_balance", methods=["GET", "POST"])
# @login_required
# @fund_managers
# def upload_investment_balance():
#     # uploading closing balance of previous year for reference
#     form = UploadFileForm()

#     if form.validate_on_submit():
#         investment_balance = form.data["file_upload"]
#         df_investment = pd.read_excel(investment_balance)

#         df_investment["date_created_date"] = datetime.datetime.now()
#         df_investment["created_by"] = current_user.username
#         # try:
#         df_investment.to_sql(
#             "fund_daily_sheet",
#             db.engine,
#             if_exists="append",
#             index=False,
#         )
#         flash("Closing balance of investment has been uploaded successfully.")
#     return render_template(
#         "upload_file_template.html",
#         form=form,
#         title="Upload closing balance of investment",
#     )


# @funds_bp.route("/upload_bank_account_number", methods=["GET", "POST"])
# @login_required
# @fund_managers
# def upload_bank_account_number():
#     # uploading closing balance of previous year for reference
#     form = UploadFileForm()

#     if form.validate_on_submit():
#         bank_account_number = form.data["file_upload"]
#         df_bank_account = pd.read_excel(
#             bank_account_number, dtype={"bank_account_number": str}
#         )

#         df_bank_account["date_created_date"] = datetime.datetime.now()
#         df_bank_account["created_by"] = current_user.username

#         df_bank_account.to_sql(
#             "fund_bank_account_numbers",
#             db.engine,
#             if_exists="append",
#             index=False,
#         )
#         flash("Bank account numbers have been uploaded successfully.")
#     return render_template(
#         "upload_file_template.html",
#         form=form,
#         title="Upload bank account numbers",
#     )


@funds_bp.route("/outgo/add", methods=["POST", "GET"])
@login_required
@fund_managers
def add_major_outgo():
    form = MajorOutgoForm()
    if form.validate_on_submit():
        outgo = FundMajorOutgo()
        form.populate_obj(outgo)
        db.session.add(outgo)
        db.session.commit()
        return redirect(url_for("funds.list_outgo"))

    return render_template("funds_form.html", form=form, title="Add new outgo")


@funds_bp.route("/outgo/edit/<int:outgo_id>/", methods=["POST", "GET"])
@login_required
@fund_managers
def edit_major_outgo(outgo_id):
    outgo = db.get_or_404(FundMajorOutgo, outgo_id)
    form = MajorOutgoForm(obj=outgo)
    if form.validate_on_submit():
        form.populate_obj(outgo)
        db.session.commit()
        return redirect(url_for("funds.list_outgo"))

    return render_template("funds_form.html", form=form, title="Edit outgo")


@funds_bp.route("/outgo/", methods=["GET"])
@login_required
@fund_managers
def list_outgo():
    list_outgo = db.session.scalars(
        db.select(FundMajorOutgo).order_by(FundMajorOutgo.date_of_outgo.asc())
    )

    return render_template("outgo_list.html", list_outgo=list_outgo)


@funds_bp.route("/investment/add", methods=["POST", "GET"])
@login_required
@fund_managers
def add_amount_given_to_investment():
    form = AmountGivenToInvestmentForm()
    if form.validate_on_submit():
        investment = FundAmountGivenToInvestment()
        form.populate_obj(investment)
        db.session.add(investment)
        db.session.commit()
        return redirect(url_for("funds.list_amount_given_to_investment"))

    return render_template(
        "funds_form.html", form=form, title="Enter investment amount"
    )


@funds_bp.route("/investment/edit/<int:investment_id>/", methods=["POST", "GET"])
@login_required
@fund_managers
def edit_amount_given_to_investment(investment_id):
    investment = db.get_or_404(FundAmountGivenToInvestment, investment_id)

    form = AmountGivenToInvestmentForm(obj=investment)
    if form.validate_on_submit():
        form.populate_obj(investment)
        db.session.commit()
        return redirect(url_for("funds.list_amount_given_to_investment"))
    return render_template("funds_form.html", form=form, title="Edit investment amount")


@funds_bp.route("/investment/")
@login_required
@fund_managers
def list_amount_given_to_investment():
    investment_list = db.session.scalars(
        db.select(FundAmountGivenToInvestment).order_by(
            FundAmountGivenToInvestment.date_expected_date_of_return.asc()
        )
    )

    return render_template("investment_list.html", investment_list=investment_list)


@funds_bp.route("/modify_dates", methods=["POST", "GET"])
@login_required
@fund_managers
def modify_dates():
    form = FundsModifyDatesForm()

    if form.validate_on_submit():
        old_date = form.existing_date.data
        new_date = form.new_date.data

        bank_stmt = (
            db.update(FundBankStatement)
            .where(FundBankStatement.date_uploaded_date == old_date)
            .values(date_uploaded_date=new_date)
        )
        db.session.execute(bank_stmt)
        daily_outflow = (
            db.update(FundDailyOutflow)
            .where(FundDailyOutflow.outflow_date == old_date)
            .values(outflow_date=new_date)
        )
        db.session.execute(daily_outflow)
        daily_sheet = (
            db.update(FundDailySheet)
            .where(FundDailySheet.date_current_date == old_date)
            .values(date_current_date=new_date)
        )
        db.session.execute(daily_sheet)
        db.session.commit()

        flash(f"Dates have been changed from {old_date} to {new_date}.")

    return render_template("funds_form.html", form=form, title="Modify dates")


@funds_bp.route("/delete_date", methods=["POST", "GET"])
@login_required
@fund_managers
def delete_date():
    form = FundsDeleteForm()

    if form.validate_on_submit():
        delete_date = form.delete_date.data

        bank_stmt = db.delete(FundBankStatement).where(
            FundBankStatement.date_uploaded_date == delete_date
        )
        daily_outflow = db.delete(FundDailyOutflow).where(
            FundDailyOutflow.outflow_date == delete_date
        )
        daily_sheet = db.delete(FundDailySheet).where(
            FundDailySheet.date_current_date == delete_date
        )

        db.session.execute(bank_stmt)
        db.session.execute(daily_outflow)
        db.session.execute(daily_sheet)

        coinsurance_receipts = db.delete(CoinsuranceReceipts).where(
            db.func.date(CoinsuranceReceipts.created_on) == delete_date
        )
        pool_credits = db.delete(PoolCredits).where(
            db.func.date(PoolCredits.date_created_date) == delete_date
        )
        pool_credits_portal = db.delete(PoolCreditsPortal).where(
            db.func.date(PoolCreditsPortal.date_created_date) == delete_date
        )

        db.session.execute(coinsurance_receipts)
        db.session.execute(pool_credits)
        db.session.execute(pool_credits_portal)
        db.session.commit()
        flash(f"{delete_date} has been deleted.")

    return render_template("funds_form.html", form=form, title="Delete dates")


@funds_bp.context_processor
def funds_context():
    return dict(
        display_inflow=get_inflow,
        display_outflow=get_outflow,
        enable_update=enable_update,
        get_inflow_total=get_inflow_total,
        get_daily_summary=get_daily_summary_refactored,
        return_prev_day_closing_balance=get_previous_day_closing_balance_refactored,
        get_ibt_details=get_ibt_details,
        timedelta=datetime.timedelta,
        relativedelta=relativedelta,
    )
