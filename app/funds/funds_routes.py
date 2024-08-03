# from datetime import datetime
import datetime
from math import fabs

import pandas as pd
from dateutil.relativedelta import relativedelta
from flask import (
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
def funds_home():
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
        get_daily_summary=get_daily_summary,
    )


@funds_bp.route("/upload_statement", methods=["GET", "POST"])
@login_required
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
        # else break

        #        if False:
        #           flash("data does not work.")
        elif True:
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
        "upload_file_template.html", form=form, title="Upload bank statement"
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


@funds_bp.route("/view_flag_sheet", methods=["GET"])
@login_required
def view_flag_sheet():

    query = FundFlagSheet.query.order_by(FundFlagSheet.flag_description)

    column_names = [
        "flag_description",
        "flag_reg_exp",
    ]
    return render_template(
        "flag_view_sheet.html", query=query, column_names=column_names
    )


@funds_bp.route("/add_flag", methods=["POST", "GET"])
@login_required
def add_flag_entry():
    from extensions import db

    form = FlagForm()
    if form.validate_on_submit():
        flag = FundFlagSheet(
            flag_description=form.data["flag_description"],
            flag_reg_exp=form.data["flag_regular_expression"],
            created_by=current_user.username,
            date_created_date=datetime.datetime.now(),
        )
        db.session.add(flag)
        db.session.commit()
        return redirect(url_for("funds.view_flag_sheet"))

    return render_template("flag_edit_entry.html", form=form, title="Add flag entry")


@funds_bp.route("/edit_flag/<int:flag_id>", methods=["POST", "GET"])
@login_required
def edit_flag_entry(flag_id):
    from extensions import db

    flag = FundFlagSheet.query.get_or_404(flag_id)
    form = FlagForm()
    if form.validate_on_submit():
        flag.flag_description = form.data["flag_description"]
        flag.flag_reg_exp = form.data["flag_regular_expression"]

        flag.updated_by = current_user.username
        flag.date_updated_date = datetime.datetime.now()

        db.session.commit()
        return redirect(url_for("funds.view_flag_sheet"))

    form.flag_description.data = flag.flag_description
    form.flag_regular_expression.data = flag.flag_reg_exp
    return render_template("flag_edit_entry.html", form=form, title="Edit flag entry")


@funds_bp.route("/enter_outflow/<string:date_string>", methods=["GET", "POST"])
@login_required
def enter_outflow(date_string):
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
        return_prev_day_closing_balance=return_prev_day_closing_balance,
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
def add_remarks(date_string):
    from extensions import db

    form = DailySummaryForm()
    flag_description = db.session.query(FundFlagSheet.flag_description)
    param_date = datetime.datetime.strptime(date_string, "%d%m%Y")
    daily_sheet = FundDailySheet.query.filter(
        FundDailySheet.date_current_date == param_date
    ).first()
    if form.validate_on_submit():
        daily_sheet.text_major_collections = form.data["major_receipts"]
        daily_sheet.text_major_payments = form.data["major_payments"]
        daily_sheet.text_person1_name = form.data["person1_name"]
        daily_sheet.text_person1_designation = form.data["person1_designation"]
        daily_sheet.text_person2_name = form.data["person2_name"]
        daily_sheet.text_person2_designation = form.data["person2_designation"]

        daily_sheet.text_person3_name = form.data["person3_name"]
        daily_sheet.text_person3_designation = form.data["person3_designation"]
        daily_sheet.text_person4_name = form.data["person4_name"]
        daily_sheet.text_person4_designation = form.data["person4_designation"]

        daily_sheet.updated_by = current_user.username
        daily_sheet.date_updated_date = datetime.datetime.now()

        db.session.commit()
        return redirect(
            url_for(
                "funds.ibt",
                date_string=date_string,
                pdf="False",
            )
        )
    form.major_receipts.data = (
        (daily_sheet.text_major_collections or None) if daily_sheet else None
    )
    form.major_payments.data = (
        (daily_sheet.text_major_payments or None) if daily_sheet else None
    )

    form.person1_name.data = (
        (daily_sheet.text_person1_name or None) if daily_sheet else None
    )
    form.person1_designation.data = (
        (daily_sheet.text_person1_designation or None) if daily_sheet else None
    )

    form.person2_name.data = (
        (daily_sheet.text_person2_name or None) if daily_sheet else None
    )
    form.person2_designation.data = (
        (daily_sheet.text_person2_designation or None) if daily_sheet else None
    )

    form.person3_name.data = (
        (daily_sheet.text_person3_name or None) if daily_sheet else None
    )
    form.person3_designation.data = (
        (daily_sheet.text_person3_designation or None) if daily_sheet else None
    )

    form.person4_name.data = (
        (daily_sheet.text_person4_name or None) if daily_sheet else None
    )
    form.person4_designation.data = (
        (daily_sheet.text_person4_designation or None) if daily_sheet else None
    )

    return render_template(
        "add_remarks.html",
        form=form,
        display_date=param_date,
        enable_update=enable_update,
        display_inflow=display_inflow,
        display_outflow=fill_outflow,
        daily_sheet=daily_sheet,
        get_daily_summary=get_daily_summary,
        return_prev_day_closing_balance=return_prev_day_closing_balance,
        flag_description=flag_description,
        get_inflow_total=get_inflow_total,
        outflow_items=zip(outflow_labels, outflow_amounts),
    )


@funds_bp.route("/ibt/<string:date_string>/<string:pdf>", methods=["GET"])
@login_required
def ibt(date_string, pdf="False"):
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
        return_prev_day_closing_balance=return_prev_day_closing_balance,
        get_inflow_total=get_inflow_total,
        pdf=pdf,
        timedelta=datetime.timedelta,
        relativedelta=relativedelta,
        get_daily_summary=get_daily_summary,
        get_ibt_details=get_ibt_details,
    )


@funds_bp.route("/daily_summary/<string:date_string>/<string:pdf>", methods=["GET"])
@login_required
def daily_summary(date_string, pdf="False"):
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
        return_prev_day_closing_balance=return_prev_day_closing_balance,
        get_inflow_total=get_inflow_total,
        pdf=pdf,
        timedelta=datetime.timedelta,
        relativedelta=relativedelta,
        get_daily_summary=get_daily_summary,
    )


# @funds_bp.route("/daily_summary/pdf/<string:date_string>", methods=["GET"])
# @login_required
# def daily_summary_pdf(date_string):
#     from extensions import db

#     param_date = datetime.datetime.strptime(date_string, "%d%m%Y")
#     #    outflow = FundDailyOutflow.query.filter(FundDailyOutflow.outflow_date == param_date).first()
#     daily_sheet = FundDailySheet.query.filter(
#         FundDailySheet.date_current_date == param_date
#     ).first()
#     flag_description = db.session.query(FundFlagSheet.flag_description)
#     #    print(flag_description)
#     # inflow = FundBankStatement.query.filter(FundBankStatement.date_uploaded_date == param_date)
#     return render_template(
#         "daily_summary.html",
#         display_date=param_date,
#         # outflow=outflow,
#         daily_sheet=daily_sheet,
#         display_inflow=display_inflow,
#         outflow_items=zip(outflow_labels, outflow_amounts),
#         right_length=len(outflow_labels),
#         # outflow_amounts=outflow_amounts,
#         display_outflow=fill_outflow,
#         flag_description=flag_description,
#         return_prev_day_closing_balance=return_prev_day_closing_balance,
#         get_inflow_total=get_inflow_total,
#         pdf=True,
#         timedelta=datetime.timedelta,
#     )


@funds_bp.route("/upload_flag_sheet", methods=["GET", "POST"])
@login_required
def upload_flag_sheet():
    # uploading preconfigured flag sheet from CSV file
    form = UploadFileForm()
    if form.validate_on_submit():
        flag_sheet = form.data["file_upload"]
        df_flag_sheet = pd.read_csv(flag_sheet)
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
def upload_investment_balance():
    # uploading closing balance of previous year for reference
    form = UploadFileForm()

    if form.validate_on_submit():
        investment_balance = form.data["file_upload"]
        df_investment = pd.read_csv(investment_balance)
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
def upload_bank_account_number():
    # uploading closing balance of previous year for reference
    form = UploadFileForm()

    if form.validate_on_submit():
        bank_account_number = form.data["file_upload"]
        df_bank_account = pd.read_csv(
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


@funds_bp.route("/add_outgo/", methods=["POST", "GET"])
@login_required
def add_major_outgo():
    from extensions import db

    form = MajorOutgoForm()
    if form.validate_on_submit():
        outgo = FundMajorOutgo(
            date_of_outgo=form.data["date_of_outgo"],
            float_expected_outgo=form.data["amount_expected_outgo"],
            text_dept=form.data["department"],
            text_remarks=form.data["remarks"],
            current_status=form.data["current_status"],
            created_by=current_user.username,
            date_created_date=datetime.datetime.now(),
        )
        db.session.add(outgo)
        db.session.commit()
        return redirect(url_for("funds.list_outgo"))

    return render_template("outgo_edit.html", form=form)


@funds_bp.route("/edit/outgo/<int:outgo_id>/", methods=["POST", "GET"])
@login_required
def edit_major_outgo(outgo_id):
    from extensions import db

    outgo = FundMajorOutgo.query.get_or_404(outgo_id)
    form = MajorOutgoForm()
    if form.validate_on_submit():
        outgo.date_of_outgo = form.data["date_of_outgo"]
        outgo.float_expected_outgo = form.data["amount_expected_outgo"]
        outgo.text_dept = form.data["department"]
        outgo.text_remarks = form.data["remarks"]
        outgo.current_status = form.data["current_status"]
        outgo.updated_by = current_user.username
        outgo.date_updated_date = datetime.datetime.now()
        db.session.commit()
        return redirect(url_for("funds.list_outgo"))

    form.date_of_outgo.data = outgo.date_of_outgo
    form.amount_expected_outgo.data = outgo.float_expected_outgo
    form.department.data = outgo.text_dept
    form.remarks.data = outgo.text_remarks
    form.current_status.data = outgo.current_status
    return render_template("outgo_edit.html", form=form)


@funds_bp.route("/list_outgo/", methods=["GET"])
@login_required
def list_outgo():
    list_outgo = FundMajorOutgo.query.order_by(FundMajorOutgo.date_of_outgo.asc())

    return render_template("outgo_list.html", list_outgo=list_outgo)


@funds_bp.route("/add_amount_investment", methods=["POST", "GET"])
@login_required
def add_amount_given_to_investment():
    from extensions import db

    form = AmountGivenToInvestmentForm()
    if form.validate_on_submit():
        date_given = form.data["date_given_to_investment"]
        amount_given = form.data["amount_given_to_investment"]
        expected_date_of_return = form.data["expected_date_of_return"]
        remarks = form.data["remarks"]
        current_status = form.data["current_status"]
        given_to_investment = FundAmountGivenToInvestment(
            date_given_to_investment=date_given,
            float_amount_given_to_investment=amount_given,
            text_remarks=remarks,
            date_expected_date_of_return=expected_date_of_return,
            current_status=current_status,
            created_by=current_user.username,
            date_created_date=datetime.datetime.now(),
        )
        db.session.add(given_to_investment)
        db.session.commit()
        return redirect(url_for("funds.list_amount_given_to_investment"))

    return render_template("investment_edit_amount.html", form=form)


@funds_bp.route("/edit_amount_investment/<int:investment_id>", methods=["POST", "GET"])
@login_required
def edit_amount_given_to_investment(investment_id):
    from extensions import db

    investment = FundAmountGivenToInvestment.query.get_or_404(investment_id)

    form = AmountGivenToInvestmentForm()
    if form.validate_on_submit():
        investment.date_given_to_investment = form.data["date_given_to_investment"]
        investment.float_amount_given_to_investment = form.data[
            "amount_given_to_investment"
        ]
        investment.date_expected_date_of_return = form.data["expected_date_of_return"]
        investment.text_remarks = form.data["remarks"] or None
        investment.current_status = form.data["current_status"]
        investment.updated_by = current_user.username
        investment.date_updated_date = datetime.datetime.now()
        db.session.commit()
        return redirect(url_for("funds.list_amount_given_to_investment"))
    form.date_given_to_investment.data = investment.date_given_to_investment
    form.amount_given_to_investment.data = investment.float_amount_given_to_investment
    form.expected_date_of_return.data = investment.date_expected_date_of_return
    form.remarks.data = investment.text_remarks
    form.current_status.data = investment.current_status
    return render_template("investment_edit_amount.html", form=form)


@funds_bp.route("/list_amount_investment/")
@login_required
def list_amount_given_to_investment():
    investment_list = FundAmountGivenToInvestment.query.order_by(
        FundAmountGivenToInvestment.date_expected_date_of_return.asc()
    )

    return render_template("investment_list.html", investment_list=investment_list)


@funds_bp.route("/reports", methods=["POST", "GET"])
@login_required
def funds_reports():
    from extensions import db

    form = ReportsForm()
    if form.validate_on_submit():
        # if no start date is provided, default to 01/04/2024
        start_date = form.data["start_date"] or datetime.date(2024, 4, 1)
        # if no end date is provided, default to today
        end_date = form.data["end_date"] or datetime.date.today()
        inflow = form.data["check_inflow"]
        outflow = form.data["check_outflow"]
        investments = form.data["check_investments"]
        major_payments = form.data["check_major_payments"]
        major_receipts = form.data["check_major_receipts"]

        #        print(start_date, end_date)
        all_queries = []
        if inflow:
            case_inflow = case((FundBankStatement.credit != 0, "Inflow"), else_="")
            inflow_query = (
                db.session.query(FundBankStatement)
                .with_entities(
                    FundBankStatement.value_date,
                    FundBankStatement.flag_description,
                    FundBankStatement.description,
                    cast(FundBankStatement.credit, String),
                    case_inflow,
                )
                .filter(
                    (
                        (FundBankStatement.value_date >= start_date)
                        & (FundBankStatement.value_date <= end_date)
                    )
                    & (FundBankStatement.credit != 0)
                    & (FundBankStatement.flag_description != "Drawn from investment")
                )
            )
            all_queries.append(inflow_query)
            # query = inflow_query
        if outflow:
            case_outflow = case(
                (FundDailyOutflow.outflow_amount > 0, "Outflow"), else_=""
            )
            outflow_query = (
                db.session.query(FundDailyOutflow)
                .with_entities(
                    FundDailyOutflow.outflow_date,
                    FundDailyOutflow.outflow_description,
                    FundDailyOutflow.outflow_description,
                    cast(FundDailyOutflow.outflow_amount, String),
                    case_outflow,
                )
                .filter(
                    (FundDailyOutflow.outflow_date >= start_date)
                    & (FundDailyOutflow.outflow_date <= end_date)
                    & (FundDailyOutflow.outflow_amount > 0)
                )
            )
            all_queries.append(outflow_query)
        # query = inflow_query.union(outflow_query)
        if investments:
            case_investment_given = case(
                (
                    FundDailySheet.float_amount_given_to_investments > 0,
                    "Given to investment",
                ),
                else_="",
            )
            case_investment_taken = case(
                (
                    FundDailySheet.float_amount_taken_from_investments > 0,
                    "Taken from investments",
                ),
                else_="",
            )
            investment_given_query = (
                db.session.query(FundDailySheet)
                .with_entities(
                    FundDailySheet.date_current_date,
                    case_investment_given,
                    case_investment_given,
                    cast(FundDailySheet.float_amount_given_to_investments, String),
                    case_investment_given,
                )
                .filter(
                    (FundDailySheet.date_current_date >= start_date)
                    & (FundDailySheet.date_current_date <= end_date)
                    & (FundDailySheet.float_amount_given_to_investments > 0)
                )
            )
            investment_taken_query = (
                db.session.query(FundDailySheet)
                .with_entities(
                    FundDailySheet.date_current_date,
                    case_investment_taken,
                    case_investment_taken,
                    cast(FundDailySheet.float_amount_taken_from_investments, String),
                    case_investment_taken,
                )
                .filter(
                    (FundDailySheet.date_current_date >= start_date)
                    & (FundDailySheet.date_current_date <= end_date)
                    & (FundDailySheet.float_amount_taken_from_investments > 0)
                )
            )
            all_queries.append(investment_given_query)
            all_queries.append(investment_taken_query)
        if major_receipts:
            case_major_receipts = case(
                (
                    FundDailySheet.text_major_collections.is_not(None),
                    "Major collections",
                ),
                else_="",
            )
            major_receipts_query = (
                db.session.query(FundDailySheet)
                .with_entities(
                    FundDailySheet.date_current_date,
                    case_major_receipts,
                    case_major_receipts,
                    FundDailySheet.text_major_collections,
                    case_major_receipts,
                )
                .filter(
                    (FundDailySheet.date_current_date >= start_date)
                    & (FundDailySheet.date_current_date <= end_date)
                    & (FundDailySheet.text_major_collections.is_not(None))
                    & (FundDailySheet.text_major_collections != "")
                )
            )
            # pass
            all_queries.append(major_receipts_query)
        if major_payments:

            case_major_payments = case(
                (
                    FundDailySheet.text_major_payments.is_not(None),
                    "Major payments",
                ),
                else_="",
            )
            major_payments_query = (
                db.session.query(FundDailySheet)
                .with_entities(
                    FundDailySheet.date_current_date,
                    case_major_payments,
                    case_major_payments,
                    FundDailySheet.text_major_payments,
                    case_major_payments,
                )
                .filter(
                    (FundDailySheet.date_current_date >= start_date)
                    & (FundDailySheet.date_current_date <= end_date)
                    & (FundDailySheet.text_major_payments.is_not(None))
                    & (FundDailySheet.text_major_payments != "")
                )
            )
            # pass
            all_queries.append(major_payments_query)
        # all_queries = [inflow_query, outflow_query, investment_given_query, investment_taken_query]
        query_set = union(*all_queries)
        query = db.session.execute(query_set)
        return render_template("reports_output.html", query=query)
    form.check_inflow.data = True
    form.check_outflow.data = True
    form.check_investments.data = True
    return render_template("reports_form.html", form=form)


@funds_bp.route("/view_jv_flags", methods=["GET", "POST"])
@login_required
def view_jv_flags():

    list = FundJournalVoucherFlagSheet.query.order_by(FundJournalVoucherFlagSheet.id)
    column_names = FundJournalVoucherFlagSheet.query.statement.columns.keys()

    return render_template("jv_view_flags.html", list=list, column_names=column_names)


@funds_bp.route("/upload_jv_flags", methods=["GET", "POST"])
@login_required
def upload_jv_flags():

    form = UploadFileForm()

    if form.validate_on_submit():
        jv_flag_sheet = form.data["file_upload"]
        df_jv_flag_sheet = pd.read_csv(
            jv_flag_sheet,
            dtype={
                "txt_description": str,
                "txt_flag": str,
                "txt_gl_code": str,
                "txt_sl_code": str,
            },
        )
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))

        df_jv_flag_sheet["date_created_date"] = datetime.datetime.now()
        df_jv_flag_sheet["created_by"] = current_user.username

        df_jv_flag_sheet.to_sql(
            "fund_journal_voucher_flag_sheet",
            engine,
            if_exists="append",
            index=False,
        )
        flash("Flags for Journal voucher have been uploaded successfully.")
    return render_template(
        "upload_file_template.html",
        form=form,
        title="Upload flags for journal voucher",
    )


@funds_bp.route("/download_jv", methods=["POST", "GET"])
@login_required
def download_jv():
    """Function to generate generate Fund Journal voucher from available data
    Input required: Start date and end date
    Inflow query is run to collect all data from bank statement
    Inflow and amount drawn from investment is collected from inflow query
    Outflow query is used to collect all outflow data
    Investment query is used to collect money given to investment
    Note: Amount drawn from investment is already colleted from inflow query and not required to run again separately
    Output: Pandas dataframe written to excel file with start date and end date added to file name for quick reference.
    """

    form = FundsJVForm()
    from extensions import db

    if form.validate_on_submit():
        # if no start date is provided, default to today
        start_date = form.data["start_date"] or datetime.date.today()
        # if no end date is provided, default to today
        end_date = form.data["end_date"] or datetime.date.today()

        all_queries = []

        # inflow case and query
        # all inflows from bank statement is collected
        # this includes amount drawn from investment
        case_inflow = case((FundBankStatement.credit != 0, "Inflow"), else_="").label(
            "Type"
        )
        inflow_query = (
            db.session.query(FundBankStatement)
            .with_entities(
                FundBankStatement.value_date.label("Date"),
                func.concat(
                    FundBankStatement.description, FundBankStatement.reference_no
                ).label("Bank Description"),
                FundBankStatement.credit.label("Amount"),
                case_inflow,
            )
            .filter(
                (
                    (FundBankStatement.value_date >= start_date)
                    & (FundBankStatement.value_date <= end_date)
                )
                & (FundBankStatement.credit != 0)
            )
        )
        all_queries.append(inflow_query)

        # outflow case and query
        # fund JV flag sheet contains flag in upper case and without underscore

        case_outflow = case(
            (FundDailyOutflow.outflow_amount > 0, "Outflow"), else_=""
        ).label("Type")

        # func.upper and func.replace is used to uppercase the results and remove "amount" and underscore from results
        # this is because our JV flag sheet has flags in upper case and without "AMOUNT" and underscore
        outflow_query = (
            db.session.query(FundDailyOutflow)
            .with_entities(
                FundDailyOutflow.outflow_date.label("Date"),
                func.upper(
                    func.replace(
                        func.replace(
                            FundDailyOutflow.outflow_description, "amount_", ""
                        ),
                        "_",
                        " ",
                    )
                ).label("Bank Description"),
                FundDailyOutflow.outflow_amount.label("Amount"),
                case_outflow,
            )
            .filter(
                (FundDailyOutflow.outflow_date >= start_date)
                & (FundDailyOutflow.outflow_date <= end_date)
                & (FundDailyOutflow.outflow_amount > 0)
            )
        )
        all_queries.append(outflow_query)

        # investment case and query
        # amount given to investment is sourced here
        # amount drawn from investment is already collected in inflow query (straight from bank statement)
        case_investment_given = case(
            (
                FundDailySheet.float_amount_given_to_investments > 0,
                "Given to investment",
            ),
            else_="",
        ).label("Type")

        investment_given_query = (
            db.session.query(FundDailySheet)
            .with_entities(
                FundDailySheet.date_current_date.label("Date"),
                case_investment_given.label("Bank Description"),
                FundDailySheet.float_amount_given_to_investments.label("Amount"),
                case_investment_given,
            )
            .filter(
                (FundDailySheet.date_current_date >= start_date)
                & (FundDailySheet.date_current_date <= end_date)
                & (FundDailySheet.float_amount_given_to_investments > 0)
            )
        )

        all_queries.append(investment_given_query)

        query_set = union(*all_queries)

        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
        conn = engine.connect()
        df_funds = pd.read_sql_query(query_set, conn)

        df_funds["Office Location"] = "000100"

        df_funds["Date"] = pd.to_datetime(df_funds["Date"], format="%d/%m/%Y")

        df_flags, flag_description = prepare_jv_flag(engine)
        # df_flags = pd.read_sql("fund_journal_voucher_flag_sheet", engine)

        # df_flags = df_flags[
        #     ["txt_description", "txt_flag", "txt_gl_code", "txt_sl_code"]
        # ]
        # df_flags = df_flags.drop_duplicates()

        # df_flags = df_flags.rename(
        #     columns={
        #         "txt_description": "DESCRIPTION",
        #         "txt_flag": "FLAG",
        #         "txt_gl_code": "GL Code",
        #         "txt_sl_code": "SL Code",
        #     }
        # )

        # flag_description: list[str] = (
        #     df_flags["DESCRIPTION"].astype(str).unique().tolist()
        # )

        df_merged = pd.concat(
            [
                prepare_inflow_jv(df_funds, df_flags, flag_description),
                prepare_outflow_jv(df_funds, df_flags, flag_description),
                prepare_investment_jv(df_funds),
            ]
        )
        if not df_merged.empty:
            df_merged = df_merged[
                ["Office Location", "GL Code", "SL Code", "DR/CR", "Amount", "Remarks"]
            ]
            df_merged["GL Code"] = pd.to_numeric(df_merged["GL Code"])
            df_merged["SL Code"] = pd.to_numeric(df_merged["SL Code"])
            datetime_string = datetime.datetime.now()
            df_merged.to_excel(
                f"funds_jv/HDFC JV_{datetime_string:%d%m%Y%H%M%S}.xlsx", index=False
            )
            return send_from_directory(
                directory="funds_jv/",
                path=f"HDFC JV_{datetime_string:%d%m%Y%H%M%S}.xlsx",
                download_name=f"HDFC_JV_{start_date}_{end_date}.xlsx",
                as_attachment=True,
            )

        else:
            return "no data"

    return render_template("jv_download_jv.html", form=form)


def prepare_jv_flag(engine) -> tuple[pd.DataFrame, list[str]]:
    df_flags = pd.read_sql("fund_journal_voucher_flag_sheet", engine)

    df_flags = df_flags[["txt_description", "txt_flag", "txt_gl_code", "txt_sl_code"]]
    df_flags = df_flags.drop_duplicates()

    df_flags = df_flags.rename(
        columns={
            "txt_description": "DESCRIPTION",
            "txt_flag": "FLAG",
            "txt_gl_code": "GL Code",
            "txt_sl_code": "SL Code",
        }
    )

    flag_description: list[str] = df_flags["DESCRIPTION"].astype(str).unique().tolist()

    return df_flags, flag_description


def filter_unidentified_credits(df_inflow: pd.DataFrame, engine) -> pd.DataFrame:
    # engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))

    flag_description: list[str] = prepare_jv_flag(engine)[1]

    df_inflow["DESCRIPTION"] = df_inflow["description"].apply(
        lambda x: "".join([part for part in flag_description if part in str(x)])
    )

    df_unidentified_credits = df_inflow[df_inflow["DESCRIPTION"] == ""]

    df_unidentified_credits = df_unidentified_credits.drop(columns=["DESCRIPTION"])
    df_unidentified_credits["date_created_date"] = datetime.datetime.now()
    df_unidentified_credits["created_by"] = current_user.username

    return df_unidentified_credits


def prepare_investment_jv(df_funds_excel: pd.DataFrame) -> pd.DataFrame:
    df_investment = df_funds_excel[
        df_funds_excel["Type"] == "Given to investment"
    ].copy()
    if df_investment.empty:
        return pd.DataFrame()

    df_investment["GL Code"] = 5121900700
    df_investment["SL Code"] = 0
    df_investment["Remarks"] = "Given to investment " + df_investment[
        "Date"
    ].dt.strftime("%d/%m/%Y").astype(str)

    df_investment["DR/CR"] = "DR"
    df_investment_actual = df_investment.copy()

    df_investment_actual["GL Code"] = 9111310000
    df_investment_actual["SL Code"] = 12404226
    df_investment_actual["DR/CR"] = "CR"

    df_investment_merged = pd.concat([df_investment_actual, df_investment])

    return df_investment_merged


def prepare_outflow_jv(
    df_funds_excel: pd.DataFrame, df_flags: pd.DataFrame, flag_description: list[str]
) -> pd.DataFrame:
    df_outflow = df_funds_excel[df_funds_excel["Type"] == "Outflow"].copy()

    if df_outflow.empty:
        return pd.DataFrame()

    df_outflow["DESCRIPTION"] = df_outflow["Bank Description"].apply(
        lambda x: "".join([part for part in flag_description if part in str(x)])
    )

    df_outflow["DESCRIPTION"] = df_outflow["DESCRIPTION"].replace(
        r"^\s*$", "OTHERS", regex=True
    )

    df_outflow = df_outflow.merge(df_flags, on="DESCRIPTION", how="left")

    df_outflow["Remarks"] = (
        df_outflow["DESCRIPTION"]
        + " "
        + df_outflow["FLAG"]
        + " "
        + df_outflow["Date"].dt.strftime("%d/%m/%Y").astype(str)
    )
    df_outflow["DR/CR"] = "DR"

    df_outflow_actual = df_outflow.copy()

    df_outflow_actual["GL Code"] = 9111310000
    df_outflow_actual["SL Code"] = 12404226
    df_outflow_actual["DR/CR"] = "CR"

    df_merged_outflow = pd.concat([df_outflow_actual, df_outflow])

    return df_merged_outflow


def prepare_inflow_jv(
    df_funds_excel: pd.DataFrame, df_flags: pd.DataFrame, flag_description: list[str]
) -> pd.DataFrame:
    df_inflow = df_funds_excel[df_funds_excel["Type"] == "Inflow"].copy()
    if df_inflow.empty:
        return pd.DataFrame()

    df_inflow["DESCRIPTION"] = df_inflow["Bank Description"].apply(
        lambda x: "".join([part for part in flag_description if part in str(x)])
    )

    df_inflow["DESCRIPTION"] = df_inflow["DESCRIPTION"].replace(
        r"^\s*$", "OTHERS", regex=True
    )

    df_inflow = df_inflow.merge(df_flags, on="DESCRIPTION", how="left")

    df_inflow["Remarks"] = (
        df_inflow["FLAG"] + " " + df_inflow["Date"].dt.strftime("%d/%m/%Y").astype(str)
    )

    df_inflow.loc[df_inflow["Amount"] > 0, "DR/CR"] = "CR"
    df_inflow.loc[df_inflow["Amount"] < 0, "DR/CR"] = "DR"
    df_inflow.loc[df_inflow["Amount"] < 0, "Amount"] = df_inflow["Amount"] * -1

    df_inflow_actual = df_inflow.copy()

    df_inflow_actual["GL Code"] = 9111310000
    df_inflow_actual["SL Code"] = 12404226
    df_inflow_actual.loc[df_inflow["DR/CR"] == "DR", "DR/CR"] = "CR"
    df_inflow_actual.loc[df_inflow["DR/CR"] == "CR", "DR/CR"] = "DR"

    df_merged = pd.concat([df_inflow_actual, df_inflow])
    return df_merged


@funds_bp.route("/modify_dates", methods=["POST", "GET"])
@login_required
def modify_dates():
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
