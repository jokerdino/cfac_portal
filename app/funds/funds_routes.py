import datetime
from math import fabs
import uuid

import pandas as pd
from dateutil.relativedelta import relativedelta
from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import (
    String,
    case,
    cast,
    #    create_engine,
    distinct,
    func,
    text,
    union,
    or_,
    and_,
)

from app.funds import funds_bp
from app.funds.funds_form import (
    AmountGivenToInvestmentForm,
    DailySummaryForm,
    FlagForm,
    FundsJVForm,
    FundsModifyDatesForm,
    MajorOutgoForm,
    #    OutflowForm,
    ReportsForm,
    UploadFileForm,
    JVFlagAddForm,
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
    FundJournalVoucherFlagSheet,
    FundMajorOutgo,
)
from app.coinsurance.coinsurance_model import CoinsuranceReceipts
from app.pool_credits.pool_credits_model import PoolCredits, PoolCreditsPortal

from app.pool_credits.pool_credits_portal import prepare_dataframe
from .funds_jv import filter_unidentified_credits
from extensions import db

from set_view_permissions import admin_required, fund_managers

outflow_labels = [
    "CITI HEALTH",
    "MRO1 HEALTH",
    "AXIS NEFT",
    "CITI NEFT",
    "TNCMCHIS",
    "AXIS CENTRALISED CHEQUE",
    "AXIS CENTRALISED CHEQUE 521",
    "AXIS TDS RO",
    "PENSION PAYMENT",
    "GRATUITY",
    "AXIS GST",
    "RO NAGPUR CROP",
    "CITI OMP",
    "HDFC Lien",
    "Other payments",
]

outflow_amounts = [
    f"amount_{field.lower().replace(' ', '_')}" for field in outflow_labels
]


def get_inflow(input_date, inflow_description=None):
    query = db.session.query(
        func.sum(FundBankStatement.credit),
        func.sum(FundBankStatement.debit),
        func.sum(FundBankStatement.ledger_balance),
    ).filter(FundBankStatement.date_uploaded_date == input_date)

    if inflow_description:
        query = query.filter(FundBankStatement.flag_description == inflow_description)

    total_credit, total_debit, total_ledger = query.first() or (0, 0, 0)

    # Special handling for balances
    if inflow_description in ("HDFC OPENING BAL", "HDFC CLOSING BAL"):
        return total_ledger or 0

    return total_credit or 0


def get_outflow(date, description=None):
    query = db.session.query(func.sum(FundDailyOutflow.outflow_amount)).filter(
        FundDailyOutflow.outflow_date == date
    )

    if description:
        query = query.filter(FundDailyOutflow.outflow_description == description)

    total_outflow = query.first()[0]  # first() returns a tuple like (sum_value,)
    return total_outflow or 0


def get_previous_day_closing_balance_refactored(input_date, requirement):
    daily_sheet = (
        db.session.query(FundDailySheet)
        .filter(FundDailySheet.date_current_date < input_date)
        .order_by(FundDailySheet.date_current_date.desc())
    ).first()

    if not daily_sheet:
        return 0

    return get_requirement(daily_sheet, requirement)


def get_daily_summary_refactored(input_date, requirement):
    daily_sheet = FundDailySheet.query.filter(
        FundDailySheet.date_current_date == input_date
    ).first()
    if not daily_sheet:
        return 0

    return get_requirement(daily_sheet, requirement)


def get_requirement(daily_sheet, requirement):
    requirement_dict = {
        "net_investment": daily_sheet.get_net_investment,
        "hdfc_closing_balance": daily_sheet.float_amount_hdfc_closing_balance or 0,
        "investment_closing_balance": daily_sheet.float_amount_investment_closing_balance
        or 0,
        "investment_given": daily_sheet.float_amount_given_to_investments or 0,
        "investment_taken": daily_sheet.float_amount_taken_from_investments or 0,
    }

    return requirement_dict.get(requirement, 0)


def get_inflow_total(date):
    inflow_total = (
        (get_inflow(date) or 0)
        + (
            get_previous_day_closing_balance_refactored(date, "hdfc_closing_balance")
            or 0
        )
        - (get_daily_summary_refactored(date, "investment_taken"))
    )

    return inflow_total or 0


def get_ibt_details(outflow_description):
    outflow = FundBankAccountNumbers.query.filter(
        FundBankAccountNumbers.outflow_description == outflow_description
    ).first()

    return outflow


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
    total_records = db.session.execute(count_query).scalar_one()
    records_filtered = total_records

    start = request.args.get("start", type=int)
    length = request.args.get("length", type=int)

    paginated_query = query.offset(start).limit(length)
    rows = db.session.execute(paginated_query).mappings().all()
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
            "upload_file_template.html",
            form=form,
            title="Upload bank statement (in .xlsx file format)",
        )

    try:
        df = parse_bank_statement(form.data["file_upload"])
        df = normalize_bank_statement(df)
        df = add_flag(df)

        if not verify_closing_balance(df):
            return render_template(
                "upload_file_template.html",
                form=form,
                title="Upload bank statement (in .xlsx file format)",
            )

        save_bank_statement_and_credits(df)

        return redirect(
            url_for(
                "funds.enter_outflow",
                date_string=datetime.date.today().strftime("%d%m%Y"),
            )
        )
    except Exception as e:
        flash(f"Error processing bank statement: {str(e)}")
        return render_template(
            "upload_file_template.html",
            form=form,
            title="Upload bank statement (in .xlsx file format)",
        )


def parse_bank_statement(file) -> pd.DataFrame:
    return pd.read_excel(
        file,
        parse_dates=["Book Date", "Value Date"],
        date_format="dd-mm-yyyy",
        dtype={
            "Description": str,
            "Ledger Balance": float,
            "Credit": float,
            "Debit": float,
            "Reference No": str,
            "Transaction Branch": str,
        },
    )


def normalize_bank_statement(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.lower().str.replace(" ", "_")
    df["date_uploaded_date"] = datetime.date.today()
    df["date_created_date"] = datetime.datetime.now()
    df["created_by"] = current_user.username

    # assign same batch_id to all rows in this upload
    df["batch_id"] = str(uuid.uuid4())

    # Move debit values to credit, nullify debit
    mask = df["debit"].notnull()
    df.loc[mask, "credit"] = df.loc[mask, "debit"]
    df.loc[mask, "debit"] = None

    return df


def verify_closing_balance(df: pd.DataFrame) -> bool:
    closing_balance_prev = get_previous_day_closing_balance_refactored(
        datetime.date.today() + relativedelta(days=1), "hdfc_closing_balance"
    )

    sum_credits = df["credit"].sum()
    sum_debits = df["debit"].sum()

    try:
        closing_balance_stmt = df.loc[
            df["flag_description"] == "HDFC CLOSING BAL", "ledger_balance"
        ].item()
    except ValueError:
        flash("Closing balance entry not found in the uploaded statement.")
        return False

    expected_closing = float(closing_balance_prev) + sum_credits - sum_debits

    if fabs(expected_closing - closing_balance_stmt) > 0.001:
        flash(
            f"Mismatch in closing balance. Uploaded: {closing_balance_stmt}, Expected: {expected_closing}"
        )
        return False

    return True


def save_bank_statement_and_credits(df: pd.DataFrame):
    # Save full bank statement
    df.to_sql("fund_bank_statement", db.engine, if_exists="append", index=False)

    batch_id = df["batch_id"].iloc[0]

    stmt = (
        db.update(FundBankStatement)
        .values(flag_id=FundJournalVoucherFlagSheet.id)
        .where(
            FundBankStatement.flag_id.is_(None),
            FundBankStatement.batch_id == batch_id,
            FundBankStatement.description.contains(
                FundJournalVoucherFlagSheet.txt_description
            ),
        )
    )

    db.session.execute(stmt)
    db.session.commit()

    # Filter and process "Other Receipts"
    other_receipts = df[df["flag_description"] == "OTHER RECEIPTS"]
    unidentified_credits = filter_unidentified_credits(other_receipts)

    # Upload unidentified credits
    unidentified_credits.to_sql(
        "pool_credits", db.engine, if_exists="append", index=False
    )

    # Upload to pool credits portal
    df_portal = prepare_dataframe(unidentified_credits)
    df_portal.to_sql("pool_credits_portal", db.engine, if_exists="append", index=False)

    # Update daily sheet
    closing_balance = df.loc[
        df["flag_description"] == "HDFC CLOSING BAL", "ledger_balance"
    ].item()
    create_or_update_daily_sheet(closing_balance)


def create_or_update_daily_sheet(closing_balance_statement):
    daily_sheet = FundDailySheet.query.filter(
        FundDailySheet.date_current_date == datetime.date.today()
    ).first()

    # if there is no daily sheet created for the day, initiate blank daily sheet

    if not daily_sheet:
        daily_sheet = FundDailySheet()
        db.session.add(daily_sheet)

    daily_sheet.float_amount_hdfc_closing_balance = closing_balance_statement

    db.session.commit()


def add_flag(df_bank_statement):
    # obtain flag from database and store it as pandas dataframe
    df_flag_sheet = pd.read_sql("fund_flag_sheet", db.engine)
    df_flag_sheet = df_flag_sheet[["flag_description", "flag_reg_exp"]]

    # extract regular expression column into list
    reg_exp = df_flag_sheet["flag_reg_exp"].unique().tolist()

    # add new column flag_reg_exp wherever the description matches the regular_expression
    df_bank_statement["flag_reg_exp"] = df_bank_statement["description"].apply(
        lambda x: "".join([part for part in reg_exp if part in str(x)])
    )

    # use the newly created column to merge with uploaded bank_statement
    df_bank_statement = df_bank_statement.merge(
        df_flag_sheet, on="flag_reg_exp", how="left"
    )

    # Unidentified inflows to be marked as "Other receipts"
    df_bank_statement["flag_description"] = df_bank_statement[
        "flag_description"
    ].fillna("OTHER RECEIPTS")

    # drop the temporarily created column
    df_bank_statement = df_bank_statement.drop("flag_reg_exp", axis=1)

    return df_bank_statement


@funds_bp.route("/bank_statement/view/<string:date_string>/", methods=["GET"])
@login_required
@fund_managers
def view_bank_statement(date_string):
    param_date = datetime.datetime.strptime(date_string, "%d%m%Y")
    query = FundBankStatement.query.filter(
        FundBankStatement.date_uploaded_date == param_date
    ).order_by(FundBankStatement.id)

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
    query = FundFlagSheet.query.order_by(FundFlagSheet.flag_description)

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

    return render_template("jv_pattern_add.html", form=form, title="Add flag entry")


@funds_bp.route("/flags/edit/<int:flag_id>", methods=["POST", "GET"])
@login_required
@fund_managers
def edit_flag_entry(flag_id):
    flag = FundFlagSheet.query.get_or_404(flag_id)
    form = FlagForm(obj=flag)
    if form.validate_on_submit():
        form.populate_obj(flag)
        db.session.commit()
        return redirect(url_for("funds.view_flag_sheet"))

    return render_template("jv_pattern_add.html", form=form, title="Edit flag entry")


@funds_bp.route("/outflow/edit/<string:date_string>/", methods=["GET", "POST"])
@login_required
@fund_managers
def enter_outflow(date_string):
    param_date = datetime.datetime.strptime(date_string, "%d%m%Y")
    daily_sheet, investment_list, list_outgo, flag_description = get_outflow_data(
        param_date
    )

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
        flag_description=flag_description,
        daily_sheet=daily_sheet,
    )


def date_or_pending_filter(date_field, status_field, target_date):
    return or_(
        date_field == target_date,
        and_(status_field == "Pending", date_field < target_date),
    )


def get_outflow_data(param_date):
    daily_sheet = FundDailySheet.query.filter_by(date_current_date=param_date).first()

    investment_list = FundAmountGivenToInvestment.query.filter(
        date_or_pending_filter(
            FundAmountGivenToInvestment.date_expected_date_of_return,
            FundAmountGivenToInvestment.current_status,
            param_date,
        )
    )

    list_outgo = FundMajorOutgo.query.filter(
        date_or_pending_filter(
            FundMajorOutgo.date_of_outgo, FundMajorOutgo.current_status, param_date
        )
    )
    flag_description = db.session.query(FundFlagSheet.flag_description)
    return daily_sheet, investment_list, list_outgo, flag_description


def handle_outflow_form_submission(form, param_date, daily_sheet):
    for key, amount in form.data.items():
        if ("amount" in key) and (amount is not None):
            create_or_update_outflow(param_date, key, amount)

    amount_given = form.data.get("given_to_investment", 0)
    expected_date = form.data.get("expected_date_of_return")

    if amount_given > 0 and expected_date:
        update_given_to_investment_entry(param_date, amount_given, expected_date)

    update_daily_sheet_with_outflow(daily_sheet, param_date, amount_given)
    db.session.commit()


def update_given_to_investment_entry(param_date, amount, expected_date):
    entry = (
        FundAmountGivenToInvestment.query.filter_by(date_given_to_investment=param_date)
        .order_by(FundAmountGivenToInvestment.date_expected_date_of_return)
        .first()
    )

    total_investment = (
        db.session.query(
            func.sum(FundAmountGivenToInvestment.float_amount_given_to_investment)
        )
        .filter_by(date_given_to_investment=param_date)
        .scalar()
        or 0
    )

    if not entry:
        new_entry = FundAmountGivenToInvestment(
            date_given_to_investment=param_date,
            float_amount_given_to_investment=amount,
            text_remarks=f"From daily sheet {param_date.strftime('%d/%m/%Y')}",
            date_expected_date_of_return=expected_date,
            current_status="Pending",
        )
        db.session.add(new_entry)
    elif total_investment != amount:
        entry.date_expected_date_of_return = expected_date
        entry.float_amount_given_to_investment += amount - total_investment


def update_daily_sheet_with_outflow(daily_sheet, param_date, amount_given):
    daily_sheet.float_amount_given_to_investments = amount_given
    drawn_amount = get_inflow(param_date, "Drawn from investment")
    daily_sheet.float_amount_taken_from_investments = drawn_amount

    daily_sheet.float_amount_investment_closing_balance = (
        get_previous_day_closing_balance_refactored(
            param_date, "investment_closing_balance"
        )
        + amount_given
        - drawn_amount
    )

    daily_sheet.float_amount_hdfc_closing_balance = (
        get_previous_day_closing_balance_refactored(param_date, "hdfc_closing_balance")
        + get_inflow(param_date)
        - get_outflow(param_date)
        - amount_given
    )


def populate_outflow_form_data(form, param_date, daily_sheet):
    for item in outflow_amounts:
        form[item].data = get_outflow(param_date, item)

    # form.given_to_investment.data = daily_sheet.float_amount_given_to_investments or 0
    form.given_to_investment.data = (
        getattr(daily_sheet, "float_amount_given_to_investments", 0) or 0
    )

    entry = (
        FundAmountGivenToInvestment.query.filter_by(date_given_to_investment=param_date)
        .order_by(FundAmountGivenToInvestment.date_expected_date_of_return)
        .first()
    )

    if entry:
        form.expected_date_of_return.data = entry.date_expected_date_of_return


def enable_update(date):
    return datetime.date.today() == date.date()


def create_or_update_outflow(outflow_date, outflow_description, outflow_amount):
    outflow = (
        db.session.query(FundDailyOutflow)
        .filter(
            (FundDailyOutflow.outflow_date == outflow_date)
            & (FundDailyOutflow.outflow_description == outflow_description)
        )
        .first()
    )

    if not outflow:
        outflow = FundDailyOutflow(
            outflow_date=outflow_date, outflow_description=outflow_description
        )

        db.session.add(outflow)
    outflow.outflow_amount = outflow_amount
    db.session.commit()


@funds_bp.route("/remarks/edit/<string:date_string>/", methods=["GET", "POST"])
@login_required
@fund_managers
def add_remarks(date_string):
    flag_description = db.session.query(FundFlagSheet.flag_description)
    param_date = datetime.datetime.strptime(date_string, "%d%m%Y")
    daily_sheet = FundDailySheet.query.filter(
        FundDailySheet.date_current_date == param_date
    ).first()
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
        flag_description=flag_description,
        outflow_items=zip(outflow_labels, outflow_amounts),
    )


@funds_bp.route("/ibt/<string:date_string>/<string:pdf>", methods=["GET"])
@login_required
@fund_managers
def ibt(date_string, pdf="False"):
    param_date = datetime.datetime.strptime(date_string, "%d%m%Y")

    daily_sheet = FundDailySheet.query.filter(
        FundDailySheet.date_current_date == param_date
    ).first()
    flag_description = db.session.query(FundFlagSheet.flag_description)

    return render_template(
        "ibt.html",
        display_date=param_date,
        datetime=datetime,
        daily_sheet=daily_sheet,
        outflow_items=zip(outflow_labels, outflow_amounts),
        right_length=len(outflow_labels),
        flag_description=flag_description,
        pdf=pdf,
    )


@funds_bp.route("/daily_summary/<string:date_string>/<string:pdf>", methods=["GET"])
@login_required
@fund_managers
def daily_summary(date_string, pdf="False"):
    param_date = datetime.datetime.strptime(date_string, "%d%m%Y")
    daily_sheet = FundDailySheet.query.filter(
        FundDailySheet.date_current_date == param_date
    ).first()
    flag_description = db.session.query(FundFlagSheet.flag_description)

    return render_template(
        "daily_summary.html",
        display_date=param_date,
        datetime=datetime,
        daily_sheet=daily_sheet,
        outflow_items=zip(outflow_labels, outflow_amounts),
        right_length=len(outflow_labels),
        flag_description=flag_description,
        pdf=pdf,
    )


@funds_bp.route("/flags/upload", methods=["GET", "POST"])
@login_required
@fund_managers
def upload_flag_sheet():
    # uploading preconfigured flag sheet from CSV file
    form = UploadFileForm()
    if form.validate_on_submit():
        flag_sheet = form.data["file_upload"]
        df_flag_sheet = pd.read_excel(flag_sheet)

        df_flag_sheet["date_created_date"] = datetime.datetime.now()
        df_flag_sheet["created_by"] = current_user.username
        # try:
        df_flag_sheet.to_sql(
            "fund_flag_sheet",
            db.engine,
            if_exists="append",
            index=False,
        )
        flash("Flag sheet has been uploaded successfully.")
    return render_template(
        "upload_file_template.html", form=form, title="Upload flag sheet"
    )


@funds_bp.route("/upload_investment_balance", methods=["GET", "POST"])
@login_required
@fund_managers
def upload_investment_balance():
    # uploading closing balance of previous year for reference
    form = UploadFileForm()

    if form.validate_on_submit():
        investment_balance = form.data["file_upload"]
        df_investment = pd.read_excel(investment_balance)

        df_investment["date_created_date"] = datetime.datetime.now()
        df_investment["created_by"] = current_user.username
        # try:
        df_investment.to_sql(
            "fund_daily_sheet",
            db.engine,
            if_exists="append",
            index=False,
        )
        flash("Closing balance of investment has been uploaded successfully.")
    return render_template(
        "upload_file_template.html",
        form=form,
        title="Upload closing balance of investment",
    )


@funds_bp.route("/upload_bank_account_number", methods=["GET", "POST"])
@login_required
@fund_managers
def upload_bank_account_number():
    # uploading closing balance of previous year for reference
    form = UploadFileForm()

    if form.validate_on_submit():
        bank_account_number = form.data["file_upload"]
        df_bank_account = pd.read_excel(
            bank_account_number, dtype={"bank_account_number": str}
        )

        df_bank_account["date_created_date"] = datetime.datetime.now()
        df_bank_account["created_by"] = current_user.username

        df_bank_account.to_sql(
            "fund_bank_account_numbers",
            db.engine,
            if_exists="append",
            index=False,
        )
        flash("Bank account numbers have been uploaded successfully.")
    return render_template(
        "upload_file_template.html",
        form=form,
        title="Upload bank account numbers",
    )


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

    return render_template("jv_pattern_add.html", form=form, title="Add new outgo")


@funds_bp.route("/outgo/edit/<int:outgo_id>/", methods=["POST", "GET"])
@login_required
@fund_managers
def edit_major_outgo(outgo_id):
    outgo = FundMajorOutgo.query.get_or_404(outgo_id)
    form = MajorOutgoForm(obj=outgo)
    if form.validate_on_submit():
        form.populate_obj(outgo)
        db.session.commit()
        return redirect(url_for("funds.list_outgo"))

    return render_template("jv_pattern_add.html", form=form, title="Edit outgo")


@funds_bp.route("/outgo/", methods=["GET"])
@login_required
@fund_managers
def list_outgo():
    list_outgo = FundMajorOutgo.query.order_by(FundMajorOutgo.date_of_outgo.asc())

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
        "jv_pattern_add.html", form=form, title="Enter investment amount"
    )


@funds_bp.route("/investment/edit/<int:investment_id>/", methods=["POST", "GET"])
@login_required
@fund_managers
def edit_amount_given_to_investment(investment_id):
    investment = FundAmountGivenToInvestment.query.get_or_404(investment_id)

    form = AmountGivenToInvestmentForm(obj=investment)
    if form.validate_on_submit():
        form.populate_obj(investment)
        db.session.commit()
        return redirect(url_for("funds.list_amount_given_to_investment"))
    return render_template(
        "jv_pattern_add.html", form=form, title="Edit investment amount"
    )


@funds_bp.route("/investment/")
@login_required
@fund_managers
def list_amount_given_to_investment():
    investment_list = FundAmountGivenToInvestment.query.order_by(
        FundAmountGivenToInvestment.date_expected_date_of_return.asc()
    )

    return render_template("investment_list.html", investment_list=investment_list)


@funds_bp.route("/modify_dates", methods=["POST", "GET"])
@login_required
@fund_managers
def modify_dates():
    form = FundsModifyDatesForm()

    if form.validate_on_submit():
        old_date = form.old_date.data
        new_date = form.new_date.data

        bank_statement = FundBankStatement.query.filter(
            FundBankStatement.date_uploaded_date == old_date
        )
        daily_outflow = FundDailyOutflow.query.filter(
            FundDailyOutflow.outflow_date == old_date
        )
        daily_sheet = FundDailySheet.query.filter(
            FundDailySheet.date_current_date == old_date
        )

        for item in bank_statement:
            item.date_uploaded_date = new_date
        for item in daily_outflow:
            item.outflow_date = new_date
        for item in daily_sheet:
            item.date_current_date = new_date

        db.session.commit()

        flash(f"Dates have been changed from {old_date} to {new_date}.")

    return render_template("modify_dates.html", form=form)


@funds_bp.route("/delete_date", methods=["POST", "GET"])
@login_required
@fund_managers
def delete_date():
    form = FundsDeleteForm()

    if form.validate_on_submit():
        delete_date = form.delete_date.data
        db.session.query(FundBankStatement).filter(
            FundBankStatement.date_uploaded_date == delete_date
        ).delete()
        db.session.query(FundDailyOutflow).filter(
            FundDailyOutflow.outflow_date == delete_date
        ).delete()
        db.session.query(FundDailySheet).filter(
            FundDailySheet.date_current_date == delete_date
        ).delete()

        db.session.query(CoinsuranceReceipts).filter(
            func.date(CoinsuranceReceipts.created_on) == delete_date
        ).delete()
        db.session.query(PoolCredits).filter(
            func.date(PoolCredits.date_created_date) == delete_date
        ).delete()
        db.session.query(PoolCreditsPortal).filter(
            func.date(PoolCreditsPortal.date_created_date) == delete_date
        ).delete()

        db.session.commit()
        flash(f"{delete_date} has been deleted.")

    return render_template("delete_date.html", form=form)


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
