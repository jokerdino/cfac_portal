# from datetime import datetime
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
from sqlalchemy import String, case, cast, create_engine, distinct, func, text, union

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

from app.pool_credits.pool_credits_portal import prepare_dataframe
from .funds_jv import filter_unidentified_credits

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
    from extensions import db

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
    from extensions import db

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
    from extensions import db

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

    #     if type(input_date) != datetime.date:
    #         input_date = input_date.date()

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
    from extensions import db

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
        "Investment": daily_sheet.float_amount_investment_closing_balance or 0,
        "investment_closing_balance": daily_sheet.float_amount_investment_closing_balance
        or 0,
        "investment_given": daily_sheet.float_amount_given_to_investments or 0,
        "investment_taken": daily_sheet.float_amount_taken_from_investments or 0,
    }

    return requirement_dict.get(requirement, 0)


def get_inflow_total(date):
    # daily_sheet = FundDailySheet.query.filter(
    #     FundDailySheet.date_current_date == date
    # ).first()

    inflow_total = (
        (display_inflow(date) or 0)
        + (return_prev_day_closing_balance(date, "HDFC") or 0)
        - (get_daily_summary(date, "investment_taken"))
    )

    return inflow_total


def get_ibt_details(outflow_description):

    outflow = FundBankAccountNumbers.query.filter(
        FundBankAccountNumbers.outflow_description == outflow_description
    )

    return outflow


@funds_bp.route("/", methods=["GET"])
@login_required
@fund_managers
def funds_home():
    # # check_for_fund_permission()
    from extensions import db

    query = db.session.query(distinct(FundBankStatement.date_uploaded_date)).order_by(
        FundBankStatement.date_uploaded_date.desc()
    )

    return render_template(
        "funds_home.html",
        query=query,
        display_inflow=display_inflow,
        display_outflow=fill_outflow,
        get_inflow_total=get_inflow_total,
        get_daily_summary=get_daily_summary_refactored,
    )


@funds_bp.route("/upload_statement", methods=["GET", "POST"])
@login_required
@fund_managers
def upload_bank_statement():
    # check_for_fund_permission()
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

        closing_balance_prev_day = return_prev_day_closing_balance(
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
        # print(net_amount, sum_credits, sum_debits, closing_balance_statement)
        # if (net_amount - closing_balance_statement)!= 0:
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
            from extensions import db

            # if there is no daily sheet created for the day, initiate blank daily sheet
            if not FundDailySheet.query.filter(
                FundDailySheet.date_current_date == datetime.date.today()
            ).first():
                daily_sheet = FundDailySheet(
                    date_current_date=datetime.date.today(),
                    created_by=current_user.username,
                    date_created_date=datetime.datetime.now(),
                )
                db.session.add(daily_sheet)
                db.session.commit()
            daily_sheet = FundDailySheet.query.filter(
                FundDailySheet.date_current_date == datetime.date.today()
            ).first()
            daily_sheet.float_amount_hdfc_closing_balance = closing_balance_statement
            db.session.commit()
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


@funds_bp.route("/view_bank_statement/<string:date_string>", methods=["GET"])
@login_required
@fund_managers
def view_bank_statement(date_string):
    # check_for_fund_permission()
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

    # check_for_fund_permission()
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
    # check_for_fund_permission()
    from extensions import db

    form = FlagForm()
    if form.validate_on_submit():
        flag = FundFlagSheet()
        form.populate_obj(flag)
        #     flag_description=form.data["flag_description"],
        #     flag_reg_exp=form.data["flag_regular_expression"],
        #     created_by=current_user.username,
        #     date_created_date=datetime.datetime.now(),
        # )
        db.session.add(flag)
        db.session.commit()
        return redirect(url_for("funds.view_flag_sheet"))

    return render_template("jv_pattern_add.html", form=form, title="Add flag entry")


@funds_bp.route("/flags/edit/<int:flag_id>", methods=["POST", "GET"])
@login_required
@fund_managers
def edit_flag_entry(flag_id):
    # check_for_fund_permission()
    from extensions import db

    flag = FundFlagSheet.query.get_or_404(flag_id)
    form = FlagForm(obj=flag)
    if form.validate_on_submit():
        # flag.flag_description = form.data["flag_description"]
        # flag.flag_reg_exp = form.data["flag_regular_expression"]

        # flag.updated_by = current_user.username
        # flag.date_updated_date = datetime.datetime.now()
        form.populate_obj(flag)
        db.session.commit()
        return redirect(url_for("funds.view_flag_sheet"))

    # form.flag_description.data = flag.flag_description
    # form.flag_regular_expression.data = flag.flag_reg_exp
    return render_template("jv_pattern_add.html", form=form, title="Edit flag entry")


@funds_bp.route("/enter_outflow/<string:date_string>", methods=["GET", "POST"])
@login_required
@fund_managers
def enter_outflow(date_string):
    # check_for_fund_permission()
    from extensions import db

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
    )  # go.asc())
    form = OutflowForm()
    if form.validate_on_submit():
        from extensions import db

        for key, amount in form.data.items():
            if ("amount" in key) and (amount is not None):
                write_to_database_outflow(param_date, key, amount)
        #  amount_drawn_from_investment = form.data["drawn_from_investment"] or 0

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
            return_prev_day_closing_balance(param_date, "Investment")
            + amount_given_to_investment
            - display_inflow(param_date, "Drawn from investment")
        )

        # yesterday closing balance + inflow - outflow + investment_inflow - investment_outflow
        daily_sheet.float_amount_hdfc_closing_balance = (
            return_prev_day_closing_balance(param_date, "HDFC")
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
        form[item].data = fill_outflow(param_date, item) or 0

    # form.drawn_from_investment.data = (
    #     (daily_sheet.float_amount_taken_from_investments or 0) if daily_sheet else 0
    # )
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


def write_to_database_outflow(date, key, amount):
    from extensions import db

    outflow_query = db.session.query(FundDailyOutflow).filter(
        FundDailyOutflow.outflow_date == date
    )
    if key:
        outflow_query = outflow_query.filter(
            FundDailyOutflow.outflow_description == key
        ).first()
        if outflow_query:
            outflow_query.outflow_amount = amount
            outflow_query.updated_by = current_user.username
            outflow_query.date_updated_date = datetime.datetime.now()
            db.session.commit()
        else:
            outflow = FundDailyOutflow(
                outflow_date=date,
                outflow_description=key,
                outflow_amount=amount,
                date_created_date=datetime.datetime.now(),
                created_by=current_user.username,
            )
            db.session.add(outflow)
            db.session.commit()


@funds_bp.route("/add_remarks/<string:date_string>", methods=["GET", "POST"])
@login_required
@fund_managers
def add_remarks(date_string):
    # check_for_fund_permission()
    from extensions import db

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
    # check_for_fund_permission()
    from extensions import db

    param_date = datetime.datetime.strptime(date_string, "%d%m%Y")

    daily_sheet = FundDailySheet.query.filter(
        FundDailySheet.date_current_date == param_date
    ).first()
    flag_description = db.session.query(FundFlagSheet.flag_description)

    return render_template(
        "ibt.html",
        display_date=param_date,
        # outflow=outflow,
        datetime=datetime,
        daily_sheet=daily_sheet,
        display_inflow=display_inflow,
        outflow_items=zip(outflow_labels, outflow_amounts),
        right_length=len(outflow_labels),
        # outflow_amounts=outflow_amounts,
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
    # check_for_fund_permission()
    from extensions import db

    param_date = datetime.datetime.strptime(date_string, "%d%m%Y")
    #    outflow = FundDailyOutflow.query.filter(FundDailyOutflow.outflow_date == param_date).first()
    daily_sheet = FundDailySheet.query.filter(
        FundDailySheet.date_current_date == param_date
    ).first()
    flag_description = db.session.query(FundFlagSheet.flag_description)

    # inflow = FundBankStatement.query.filter(FundBankStatement.date_uploaded_date == param_date)
    return render_template(
        "daily_summary.html",
        display_date=param_date,
        # outflow=outflow,
        datetime=datetime,
        daily_sheet=daily_sheet,
        display_inflow=display_inflow,
        outflow_items=zip(outflow_labels, outflow_amounts),
        right_length=len(outflow_labels),
        # outflow_amounts=outflow_amounts,
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
    # check_for_fund_permission()
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
    # check_for_fund_permission()
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
    # check_for_fund_permission()
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
    # check_for_fund_permission()
    from extensions import db

    form = MajorOutgoForm()
    if form.validate_on_submit():
        outgo = FundMajorOutgo()
        form.populate_obj(outgo)
        # outgo = FundMajorOutgo(
        #     date_of_outgo=form.data["date_of_outgo"],
        #     float_expected_outgo=form.data["amount_expected_outgo"],
        #     text_dept=form.data["department"],
        #     text_remarks=form.data["remarks"],
        #     current_status=form.data["current_status"],
        #     created_by=current_user.username,
        #     date_created_date=datetime.datetime.now(),
        # )
        db.session.add(outgo)
        db.session.commit()
        return redirect(url_for("funds.list_outgo"))

    return render_template("jv_pattern_add.html", form=form, title="Add new outgo")


@funds_bp.route("/outgo/edit/<int:outgo_id>/", methods=["POST", "GET"])
@login_required
@fund_managers
def edit_major_outgo(outgo_id):
    # check_for_fund_permission()
    from extensions import db

    outgo = FundMajorOutgo.query.get_or_404(outgo_id)
    form = MajorOutgoForm(obj=outgo)
    if form.validate_on_submit():
        form.populate_obj(outgo)
        # outgo.date_of_outgo = form.data["date_of_outgo"]
        # outgo.float_expected_outgo = form.data["amount_expected_outgo"]
        # outgo.text_dept = form.data["department"]
        # outgo.text_remarks = form.data["remarks"]
        # outgo.current_status = form.data["current_status"]
        # outgo.updated_by = current_user.username
        # outgo.date_updated_date = datetime.datetime.now()
        db.session.commit()
        return redirect(url_for("funds.list_outgo"))

    # form.date_of_outgo.data = outgo.date_of_outgo
    # form.amount_expected_outgo.data = outgo.float_expected_outgo
    # form.department.data = outgo.text_dept
    # form.remarks.data = outgo.text_remarks
    # form.current_status.data = outgo.current_status
    return render_template("jv_pattern_add.html", form=form, title="Edit outgo")


@funds_bp.route("/outgo/", methods=["GET"])
@login_required
@fund_managers
def list_outgo():
    # check_for_fund_permission()
    list_outgo = FundMajorOutgo.query.order_by(FundMajorOutgo.date_of_outgo.asc())

    return render_template("outgo_list.html", list_outgo=list_outgo)


@funds_bp.route("/investment/add", methods=["POST", "GET"])
@login_required
@fund_managers
def add_amount_given_to_investment():
    # check_for_fund_permission()
    from extensions import db

    form = AmountGivenToInvestmentForm()
    if form.validate_on_submit():
        investment = FundAmountGivenToInvestment()
        form.populate_obj(investment)
        # date_given = form.data["date_given_to_investment"]
        # amount_given = form.data["amount_given_to_investment"]
        # expected_date_of_return = form.data["expected_date_of_return"]
        # remarks = form.data["remarks"]
        # current_status = form.data["current_status"]
        # given_to_investment = FundAmountGivenToInvestment(
        #     date_given_to_investment=date_given,
        #     float_amount_given_to_investment=amount_given,
        #     text_remarks=remarks,
        #     date_expected_date_of_return=expected_date_of_return,
        #     current_status=current_status,
        #     created_by=current_user.username,
        #     date_created_date=datetime.datetime.now(),
        # )
        db.session.add(investment)
        db.session.commit()
        return redirect(url_for("funds.list_amount_given_to_investment"))

    # return render_template("investment_edit_amount.html", form=form)
    return render_template(
        "jv_pattern_add.html", form=form, title="Enter investment amount"
    )


@funds_bp.route("/investment/edit/<int:investment_id>/", methods=["POST", "GET"])
@login_required
@fund_managers
def edit_amount_given_to_investment(investment_id):
    # check_for_fund_permission()
    from extensions import db

    investment = FundAmountGivenToInvestment.query.get_or_404(investment_id)

    form = AmountGivenToInvestmentForm(obj=investment)
    if form.validate_on_submit():
        # investment.date_given_to_investment = form.data["date_given_to_investment"]
        # investment.float_amount_given_to_investment = form.data[
        #     "amount_given_to_investment"
        # ]
        # investment.date_expected_date_of_return = form.data["expected_date_of_return"]
        # investment.text_remarks = form.data["remarks"] or None
        # investment.current_status = form.data["current_status"]
        # investment.updated_by = current_user.username
        # investment.date_updated_date = datetime.datetime.now()
        form.populate_obj(investment)
        db.session.commit()
        return redirect(url_for("funds.list_amount_given_to_investment"))
    # form.date_given_to_investment.data = investment.date_given_to_investment
    # form.amount_given_to_investment.data = investment.float_amount_given_to_investment
    # form.expected_date_of_return.data = investment.date_expected_date_of_return
    # form.remarks.data = investment.text_remarks
    # form.current_status.data = investment.current_status
    return render_template(
        "jv_pattern_add.html", form=form, title="Edit investment amount"
    )


@funds_bp.route("/investment/")
@login_required
@fund_managers
def list_amount_given_to_investment():
    # check_for_fund_permission()
    investment_list = FundAmountGivenToInvestment.query.order_by(
        FundAmountGivenToInvestment.date_expected_date_of_return.asc()
    )

    return render_template("investment_list.html", investment_list=investment_list)


@funds_bp.route("/modify_dates", methods=["POST", "GET"])
@login_required
@fund_managers
def modify_dates():
    # check_for_fund_permission()
    from extensions import db

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
