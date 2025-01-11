import datetime
from math import fabs

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
    create_engine,
    distinct,
    func,
    text,
    union,
)

from app.funds import funds_bp
from app.funds.funds_form import (
    AmountGivenToInvestmentForm,
    DailySummaryForm,
    FlagForm,
    FundsJVForm,
    FundsModifyDatesForm,
    MajorOutgoForm,
    OutflowForm,
    ReportsForm,
    UploadFileForm,
    JVFlagAddForm,
    FundsDeleteForm,
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
    "PENSION",
    "GRATUITY",
    "RO BHOPAL CROP",
    "RO NAGPUR CROP",
    "CITI OMP",
    "Lien by HDFC",
    "Other payments",
    # "BOA TPA",
]
outflow_amounts = [
    "amount_citi_health",
    "amount_mro1_health",
    "amount_axis_neft",
    "amount_citi_neft",
    "amount_tncmchis",
    "amount_axis_centralised_cheque",
    "amount_axis_centralised_cheque_521",
    "amount_axis_tds_gst",
    "amount_pension",
    "amount_gratuity",
    "amount_ro_bhopal_crop",
    "amount_ro_nagpur_crop",
    "amount_citi_omp",
    "amount_hdfc_lien",
    "amount_other_payments",
    # "amount_boa_tpa",
]


def display_inflow(input_date, inflow_description=None):
    inflow = db.session.query(
        func.sum(FundBankStatement.credit),
        func.sum(FundBankStatement.debit),
        func.sum(FundBankStatement.ledger_balance),
    ).filter(FundBankStatement.date_uploaded_date == input_date)
    if inflow_description:
        inflow = inflow.filter(FundBankStatement.flag_description == inflow_description)
        # if inflow_description in ["HDFC OPENING BAL", "HDFC CLOSING BAL"]:
        #     # Opening balance and closing balances values are stored in ledger_balance column
        #     print(type(inflow[0][1]))
        #     return inflow[0][1]

    return inflow[0][0] or 0


def fill_outflow(date, description=None):
    outflow = db.session.query(func.sum(FundDailyOutflow.outflow_amount)).filter(
        FundDailyOutflow.outflow_date == date
    )
    if description:
        outflow = outflow.filter(
            FundDailyOutflow.outflow_description == description
        ).first()
        return outflow[0] or 0

    return outflow[0][0] or 0


def return_prev_day_closing_balance(date: datetime, type: str):
    """Obsolete function. Please use 'get_previous_day_closing_balance_refactored' instead"""
    daily_summary = (
        db.session.query(FundDailySheet)
        .filter(FundDailySheet.date_current_date < date)
        .order_by(FundDailySheet.date_current_date.desc())
        .limit(1)
    ).first()

    if daily_summary:
        if type == "Investment":
            return daily_summary.float_amount_investment_closing_balance or 0
        elif type == "HDFC":
            return daily_summary.float_amount_hdfc_closing_balance or 0
    else:
        return 0


def get_daily_summary(input_date, requirement):
    """Obsolete function. Please use 'get_daily_summary_refactored' instead."""
    daily_sheet = FundDailySheet.query.filter(
        FundDailySheet.date_current_date == input_date
    ).first()
    if not daily_sheet:
        return 0

    if requirement == "net_investment":
        net_investment_amount = (daily_sheet.float_amount_given_to_investments or 0) - (
            daily_sheet.float_amount_taken_from_investments or 0
        )
        return net_investment_amount or 0
    elif requirement == "closing_balance":
        return daily_sheet.float_amount_hdfc_closing_balance or 0
    elif requirement == "investment_closing_balance":
        return daily_sheet.float_amount_investment_closing_balance or 0
    elif requirement == "investment_given":
        return daily_sheet.float_amount_given_to_investments or 0
    elif requirement == "investment_taken":
        return daily_sheet.float_amount_taken_from_investments or 0


def get_previous_day_closing_balance_refactored(input_date, requirement):
    daily_sheet = (
        db.session.query(FundDailySheet)
        .filter(FundDailySheet.date_current_date < input_date)
        .order_by(FundDailySheet.date_current_date.desc())
        .limit(1)
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
        "HDFC": daily_sheet.float_amount_hdfc_closing_balance or 0,
        "closing_balance": daily_sheet.float_amount_hdfc_closing_balance or 0,
        "hdfc_closing_balance": daily_sheet.float_amount_hdfc_closing_balance or 0,
        "Investment": daily_sheet.float_amount_investment_closing_balance or 0,
        "investment_closing_balance": daily_sheet.float_amount_investment_closing_balance
        or 0,
        "investment_given": daily_sheet.float_amount_given_to_investments or 0,
        "investment_taken": daily_sheet.float_amount_taken_from_investments or 0,
    }

    return requirement_dict.get(requirement, 0)


def get_inflow_total(date):
    inflow_total = (
        (display_inflow(date) or 0)
        + (get_previous_day_closing_balance_refactored(date, "HDFC") or 0)
        - (get_daily_summary_refactored(date, "investment_taken"))
    )

    return inflow_total or 0


def get_ibt_details(outflow_description):
    outflow = FundBankAccountNumbers.query.filter(
        FundBankAccountNumbers.outflow_description == outflow_description
    ).first()

    return outflow


@funds_bp.route("/api/v1/data/funds", methods=["GET"])
@login_required
@fund_managers
def funds_home_data():
    # Query for paginated records
    subquery = (
        db.session.query(
            FundDailySheet.date_current_date.label("date_current_date"),
            func.sum(FundDailyOutflow.outflow_amount).label("outflow_amount"),
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
        )
        .join(
            FundDailyOutflow,
            FundDailySheet.date_current_date == FundDailyOutflow.outflow_date,
        )
        .group_by(
            FundDailySheet.date_current_date,
            FundDailySheet.float_amount_given_to_investments,
            FundDailySheet.float_amount_taken_from_investments,
            FundDailySheet.float_amount_investment_closing_balance,
            FundDailySheet.float_amount_hdfc_closing_balance,
        )
        .subquery()  # Convert this to a subquery
    )

    # Main query to join the subquery with FundBankStatement
    query = (
        db.session.query(
            FundBankStatement.date_uploaded_date,
            subquery.c.investment_given,
            subquery.c.investment_taken,
            subquery.c.investment_closing_balance,
            subquery.c.hdfc_closing_balance,
            subquery.c.outflow_amount,
        )
        .outerjoin(
            subquery,
            FundBankStatement.date_uploaded_date == subquery.c.date_current_date,
        )
        .group_by(
            FundBankStatement.date_uploaded_date,
            subquery.c.investment_given,
            subquery.c.investment_taken,
            subquery.c.investment_closing_balance,
            subquery.c.hdfc_closing_balance,
            subquery.c.outflow_amount,
        )
        .order_by(FundBankStatement.date_uploaded_date.desc())
    )
    total_records = query.count()
    # Filtered record count (same as total here unless filters are applied)
    records_filtered = query.count()
    start = request.args.get("start", type=int)
    length = request.args.get("length", type=int)

    query = query.offset(start).limit(length)

    # Format the data for DataTables
    data = [
        {
            "date_uploaded_date": row[0],
            "credit": get_inflow_total(row[0]),
            "outflow": row[5] or 0,
            "net_cashflow": (get_inflow_total(row[0])) - (row[5] or 0),
            "investment_given": row[1] or 0,
            "investment_taken": row[2] or 0,
            "net_investment": (row[1] or 0) - (row[2] or 0),
            "investment_closing_balance": row[3] or 0,
            "hdfc_closing_balance": row[4] or 0,
        }
        for row in query
    ]

    # return response
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
    return render_template("funds_home_api.html")


@funds_bp.route("/", methods=["GET"])
@login_required
@fund_managers
def funds_home():
    query = db.session.query(distinct(FundBankStatement.date_uploaded_date)).order_by(
        FundBankStatement.date_uploaded_date.desc()
    )

    return render_template(
        "funds_home.html",
        query=query,
        # display_inflow=display_inflow,
        # display_outflow=fill_outflow,
        # get_inflow_total=get_inflow_total,
        # get_daily_summary=get_daily_summary_refactored,
    )


@funds_bp.route("/bank_statement/upload/", methods=["GET", "POST"])
@login_required
@fund_managers
def upload_bank_statement():
    form = UploadFileForm()

    if form.validate_on_submit():
        # collect bank statement from user upload
        bank_statement = form.data["file_upload"]

        # predetermined columns to be parsed as date types
        date_columns = ["Book Date", "Value Date"]
        df_bank_statement = pd.read_excel(
            bank_statement,
            parse_dates=date_columns,
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
        # strip space in end of names
        # lower case the column names
        # replace space with underscore

        df_bank_statement.columns = (
            df_bank_statement.columns.str.lower().str.replace(" ", "_").str.rstrip()
        )
        df_bank_statement["date_uploaded_date"] = datetime.date.today()
        df_bank_statement["date_created_date"] = datetime.datetime.now()
        df_bank_statement["created_by"] = current_user.username

        # debit entries to be moved to credit entries
        df_bank_statement.loc[df_bank_statement["debit"].notnull(), "credit"] = (
            df_bank_statement["debit"]
        )
        df_bank_statement.loc[df_bank_statement["debit"].notnull(), "debit"] = None

        # adding flag from flag_sheet table
        df_bank_statement = add_flag(df_bank_statement)

        closing_balance_prev_day = get_previous_day_closing_balance_refactored(
            datetime.date.today() + relativedelta(days=1), "HDFC"
        )
        # display_inflow(datetime.date.today())
        sum_credits = df_bank_statement["credit"].sum()
        sum_debits = df_bank_statement["debit"].sum()
        closing_balance_statement = df_bank_statement.loc[
            df_bank_statement["flag_description"] == "HDFC CLOSING BAL",
            "ledger_balance",
        ].item()

        net_amount = float(closing_balance_prev_day) + sum_credits + sum_debits
        if (fabs(float(net_amount) - float(closing_balance_statement))) > 0.001:
            flash(
                f"Amount is not tallying. As per uploaded bank statement, closing balance is: {closing_balance_statement}. However, closing balance as per existing entries and uploaded bank statement should be: {net_amount}"
            )
        # closing balance of previous day + today's credits - today's debit == closing balance of today's uploaded statement

        # closing balance of previous day + already uploaded credits - already uploaded debits + newly uploaded credits - newly uploaded debits == closing balance of currently uploaded statement

        # if above condition is ok, proceed

        else:
            engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
            # try:
            df_bank_statement.to_sql(
                "fund_bank_statement",
                engine,
                if_exists="append",
                index=False,
            )

            # upload other receipts to pool_credits table

            # filter other receipts
            df_other_receipts = df_bank_statement[
                df_bank_statement["flag_description"] == "OTHER RECEIPTS"
            ]

            # match it against JV table
            df_unidentified_credits = filter_unidentified_credits(
                df_other_receipts, engine
            )
            # if still assigned to others, to be uploaded to pool_credits table
            df_unidentified_credits.to_sql(
                "pool_credits", engine, if_exists="append", index=False
            )

            # prepare dataframe for uploading to pool credits portal

            df_pool_credits_portal = prepare_dataframe(df_unidentified_credits)
            df_pool_credits_portal.to_sql(
                "pool_credits_portal", engine, if_exists="append", index=False
            )

            create_or_update_daily_sheet(closing_balance_statement)

            # redirect to outflow form
            return redirect(
                url_for(
                    "funds.enter_outflow",
                    date_string=datetime.date.today().strftime("%d%m%Y"),
                )
            )
    return render_template(
        "upload_file_template.html",
        form=form,
        title="Upload bank statement (in .xlsx file format)",
    )


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
    engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
    df_flag_sheet = pd.read_sql("fund_flag_sheet", engine)
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


@funds_bp.route("/outflow/edit/<string:date_string>", methods=["GET", "POST"])
@login_required
@fund_managers
def enter_outflow(date_string):
    param_date = datetime.datetime.strptime(date_string, "%d%m%Y")
    flag_description = db.session.query(FundFlagSheet.flag_description)
    daily_sheet = FundDailySheet.query.filter(
        FundDailySheet.date_current_date == param_date
    ).first()

    investment_list = FundAmountGivenToInvestment.query.filter(
        (FundAmountGivenToInvestment.date_expected_date_of_return == param_date)
        | (
            (FundAmountGivenToInvestment.current_status == "Pending")
            & (FundAmountGivenToInvestment.date_expected_date_of_return < param_date)
        )
    )
    list_outgo = FundMajorOutgo.query.filter(
        (FundMajorOutgo.date_of_outgo == param_date)
        | (
            (FundMajorOutgo.current_status == "Pending")
            & (FundMajorOutgo.date_of_outgo < param_date)
        )
    )
    form = OutflowForm()
    if form.validate_on_submit():
        for key, amount in form.data.items():
            if ("amount" in key) and (amount is not None):
                create_or_update_outflow(param_date, key, amount)

        expected_date_of_return = form.data["expected_date_of_return"] or None
        amount_given_to_investment = form.data["given_to_investment"] or 0

        if (amount_given_to_investment > 0) and expected_date_of_return:
            # finding if any entry is present for the day
            given_to_investment = (
                FundAmountGivenToInvestment.query.filter(
                    FundAmountGivenToInvestment.date_given_to_investment == param_date
                )
                .order_by(FundAmountGivenToInvestment.date_expected_date_of_return)
                .first()
            )
            # summing up all the funds given to investment for the day
            # if the sum totals up, do not update the amount in given_to_investment table
            # otherwise, update the table

            sum_given_to_investment = (
                FundAmountGivenToInvestment.query.with_entities(
                    func.sum(
                        FundAmountGivenToInvestment.float_amount_given_to_investment
                    )
                )
                .filter(
                    FundAmountGivenToInvestment.date_given_to_investment == param_date
                )
                .first()
            )

            if not given_to_investment:
                # if entry for the date is not there, create new one

                # else find the existing entry and update it
                given_to_investment = FundAmountGivenToInvestment(
                    date_given_to_investment=param_date,
                    float_amount_given_to_investment=amount_given_to_investment,
                    text_remarks=f"From daily sheet {param_date.strftime('%d/%m/%Y')}",
                    date_expected_date_of_return=expected_date_of_return,
                    current_status="Pending",
                    created_by=current_user.username,
                    date_created_date=datetime.datetime.now(),
                )
                db.session.add(given_to_investment)

            # if the sum of all the funds given to investment for the day tallies with amount given in the form,
            # do not update the amount given to investment table
            # if the total does not tally, update the amount given to investment table

            elif sum_given_to_investment[0] != amount_given_to_investment:
                given_to_investment.date_expected_date_of_return = (
                    expected_date_of_return
                )
                # difference amount of sum and entered value will be updated in the table
                given_to_investment.float_amount_given_to_investment += (
                    amount_given_to_investment - sum_given_to_investment[0]
                )
                given_to_investment.updated_by = current_user.username
                given_to_investment.date_updated_date = datetime.datetime.now()

        # db.session.commit()
        daily_sheet.float_amount_given_to_investments = amount_given_to_investment
        daily_sheet.float_amount_taken_from_investments = display_inflow(
            param_date, "Drawn from investment"
        )  # amount_drawn_from_investment

        daily_sheet.float_amount_investment_closing_balance = (
            get_previous_day_closing_balance_refactored(param_date, "Investment")
            + amount_given_to_investment
            - display_inflow(param_date, "Drawn from investment")
        )

        # yesterday closing balance + inflow - outflow + investment_inflow - investment_outflow
        daily_sheet.float_amount_hdfc_closing_balance = (
            get_previous_day_closing_balance_refactored(param_date, "HDFC")
            + display_inflow(param_date)
            - fill_outflow(param_date)
            - amount_given_to_investment
        )
        daily_sheet.updated_by = current_user.username
        daily_sheet.date_updated_date = datetime.datetime.now()
        db.session.commit()

        return redirect(
            url_for(
                "funds.add_remarks",
                date_string=date_string,
            )
        )

    for item in outflow_amounts:
        form[item].data = fill_outflow(param_date, item)

    form.given_to_investment.data = (
        (daily_sheet.float_amount_given_to_investments or 0) if daily_sheet else 0
    )

    # if entry for date is present, please insert it

    given_to_investment = (
        FundAmountGivenToInvestment.query.filter(
            FundAmountGivenToInvestment.date_given_to_investment == param_date
        )
        .order_by(FundAmountGivenToInvestment.date_expected_date_of_return)
        .first()
    )
    if given_to_investment:
        form.expected_date_of_return.data = (
            given_to_investment.date_expected_date_of_return
        )

    return render_template(
        "enter_outflow.html",
        form=form,
        display_date=param_date,
        enable_update=enable_update,
        display_inflow=display_inflow,
        investment_list=investment_list,
        list_outgo=list_outgo,
        return_prev_day_closing_balance=get_previous_day_closing_balance_refactored,
        get_inflow_total=get_inflow_total,
        flag_description=flag_description,
        daily_sheet=daily_sheet,
    )


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
        enable_update=enable_update,
        display_inflow=display_inflow,
        display_outflow=fill_outflow,
        daily_sheet=daily_sheet,
        get_daily_summary=get_daily_summary_refactored,
        return_prev_day_closing_balance=get_previous_day_closing_balance_refactored,
        flag_description=flag_description,
        get_inflow_total=get_inflow_total,
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
        display_inflow=display_inflow,
        outflow_items=zip(outflow_labels, outflow_amounts),
        right_length=len(outflow_labels),
        display_outflow=fill_outflow,
        flag_description=flag_description,
        return_prev_day_closing_balance=get_previous_day_closing_balance_refactored,
        get_inflow_total=get_inflow_total,
        pdf=pdf,
        timedelta=datetime.timedelta,
        relativedelta=relativedelta,
        get_daily_summary=get_daily_summary_refactored,
        get_ibt_details=get_ibt_details,
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
        display_inflow=display_inflow,
        outflow_items=zip(outflow_labels, outflow_amounts),
        right_length=len(outflow_labels),
        display_outflow=fill_outflow,
        flag_description=flag_description,
        return_prev_day_closing_balance=get_previous_day_closing_balance_refactored,
        get_inflow_total=get_inflow_total,
        pdf=pdf,
        timedelta=datetime.timedelta,
        relativedelta=relativedelta,
        get_daily_summary=get_daily_summary_refactored,
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
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))

        df_flag_sheet["date_created_date"] = datetime.datetime.now()
        df_flag_sheet["created_by"] = current_user.username
        # try:
        df_flag_sheet.to_sql(
            "fund_flag_sheet",
            engine,
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
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))

        # df_flag_sheet["date_current_date"] = datetime.date.today()
        df_investment["date_created_date"] = datetime.datetime.now()
        df_investment["created_by"] = current_user.username
        # try:
        df_investment.to_sql(
            "fund_daily_sheet",
            engine,
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
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))

        df_bank_account["date_created_date"] = datetime.datetime.now()
        df_bank_account["created_by"] = current_user.username

        df_bank_account.to_sql(
            "fund_bank_account_numbers",
            engine,
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
        display_inflow=display_inflow,
        display_outflow=fill_outflow,
        get_inflow_total=get_inflow_total,
        get_daily_summary=get_daily_summary_refactored,
    )
