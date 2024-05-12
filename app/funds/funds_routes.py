# from datetime import datetime
import datetime
import pandas as pd

from flask import current_app, render_template, flash, redirect, url_for, request
from flask_login import current_user, login_required
from sqlalchemy import create_engine, func, distinct

from app.funds import funds_bp

from app.funds.funds_model import (
    DailySheet,
    MajorOutgo,
    AmountGivenToInvestment,
    FlagSheet,
    BankStatement,
    DailyOutflow,
)
from app.funds.funds_form import (
    DailySummaryForm,
    MajorOutgoForm,
    AmountGivenToInvestmentForm,
    UploadFileForm,
    OutflowForm,
    FlagForm,
)

# from app.tickets.tickets_routes import humanize_datetime


outflow_labels = [
    "CITI HEALTH",
    "MRO1 HEALTH",
    "AXIS NEFT",
    "CITI NEFT",
    "TNCMCHIS",
    "AXIS CENTRALISED CHEQUE",
    "AXIS CENTRALISED CHEQUE 521",
    "AXIS TDS GST",
    "PENSION",
    "GRATUITY",
    "RO BHOPAL CROP",
    "RO NAGPUR CROP",
    "CITI OMP",
    "Lien by HDFC",
    "Other payments",
    "BOA TPA",
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
    "amount_boa_tpa",
]


@funds_bp.route("/", methods=["GET", "POST"])
@login_required
def funds_home():
    from extensions import db

    query = db.session.query(distinct(BankStatement.date_uploaded_date))

    return render_template(
        "funds_home.html",
        query=query,
        display_inflow=display_inflow,
        display_outflow=fill_outflow,
        get_inflow_total=get_inflow_total,
        get_daily_summary=get_daily_summary,
    )


def get_inflow_total(date):
    daily_sheet = DailySheet.query.filter(DailySheet.date_current_date == date).first()

    inflow_total = (
        (display_inflow(date) or 0)
        + (return_prev_day_closing_balance(date, "HDFC") or 0)
        - ((daily_sheet.float_amount_taken_from_investments or 0) if daily_sheet else 0)
    )

    return inflow_total


def get_daily_summary(date, requirement):
    daily_sheet = DailySheet.query.filter(DailySheet.date_current_date == date).first()
    if requirement == "net_investment":
        net_investment_amount = (daily_sheet.float_amount_given_to_investments or 0) - (
            daily_sheet.float_amount_taken_from_investments or 0
        )
        return net_investment_amount or 0
    elif requirement == "closing_balance":
        return daily_sheet.float_amount_hdfc_closing_balance or 0


@funds_bp.route("/upload_statement", methods=["GET", "POST"])
@login_required
def upload_bank_statement():
    form = UploadFileForm()

    if form.validate_on_submit():

        # collect bank statement from user upload
        bank_statement = form.data["file_upload"]

        # predetermined columns to be parsed as date types
        date_columns = ["Book Date", "Value Date"]
        df_bank_statement = pd.read_csv(
            bank_statement,
            parse_dates=date_columns,
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

        # adding flag from flag_sheet table
        df_bank_statement = add_flag(df_bank_statement)
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))

        # try:
        df_bank_statement.to_sql(
            "bank_statement",
            engine,
            if_exists="append",
            index=False,
        )

        from extensions import db

        # if there is no daily sheet created for the day, initiate blank daily sheet
        if not DailySheet.query.filter(
            DailySheet.date_current_date == datetime.date.today()
        ).first():
            dailysheet = DailySheet(date_current_date=datetime.date.today())
            db.session.add(dailysheet)
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


@funds_bp.route("/view_bank_statement/<string:date_string>", methods=["GET", "POST"])
@login_required
def view_bank_statement(date_string):
    param_date = datetime.datetime.strptime(date_string, "%d%m%Y")
    query = BankStatement.query.filter(BankStatement.date_uploaded_date == param_date)

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


@funds_bp.route("/view_flag_sheet", methods=["GET", "POST"])
@login_required
def view_flag_sheet():
    # param_date = datetime.datetime.strptime(date_string, "%d%m%Y")
    query = FlagSheet.query.order_by(
        FlagSheet.flag_description
    )  # filter(BankStatement.date_uploaded_date == param_date)

    column_names = [
        "flag_description",
        "flag_reg_exp",
    ]  # ,'description', 'ledger_balance', 'credit', 'debit', 'value_date', 'reference_no', 'flag_description']
    return render_template(
        "flag_view_sheet.html", query=query, column_names=column_names
    )


@funds_bp.route("/add_flag", methods=["POST", "GET"])
@login_required
def add_flag_entry():
    from extensions import db

    form = FlagForm()
    if form.validate_on_submit():
        flag = FlagSheet(
            flag_description=form.data["flag_description"],  # db.Column(db.Text)
            flag_reg_exp=form.data["flag_regular_expression"],
        )
        db.session.add(flag)
        db.session.commit()
        return redirect(url_for("funds.view_flag_sheet"))
        # db.Column(db.Text))
    return render_template("flag_edit_entry.html", form=form, title="Add flag entry")


@funds_bp.route("/edit_flag/<int:flag_id>", methods=["POST", "GET"])
@login_required
def edit_flag_entry(flag_id):
    from extensions import db

    flag = FlagSheet.query.get_or_404(flag_id)
    form = FlagForm()
    if form.validate_on_submit():
        flag.flag_description = form.data["flag_description"]
        # db.Column(db.Text)
        flag.flag_reg_exp = form.data["flag_regular_expression"]
        # db.session.add(flag)
        db.session.commit()
        return redirect(url_for("funds.view_flag_sheet"))
        # db.Column(db.Text))
    form.flag_description.data = flag.flag_description
    form.flag_regular_expression.data = flag.flag_reg_exp
    return render_template("flag_edit_entry.html", form=form, title="Edit flag entry")


@funds_bp.route("/enter_outflow/<string:date_string>", methods=["GET", "POST"])
@login_required
def enter_outflow(date_string):
    from extensions import db

    param_date = datetime.datetime.strptime(date_string, "%d%m%Y")

    daily_sheet = DailySheet.query.filter(
        DailySheet.date_current_date == param_date
    ).first()

    investment_list = AmountGivenToInvestment.query.filter(AmountGivenToInvestment.date_expected_date_of_return == param_date)
    list_outgo = MajorOutgo.query.filter(MajorOutgo.date_of_outgo == param_date) #go.asc())
    form = OutflowForm()
    if form.validate_on_submit():
        from extensions import db

        for key, value in form.data.items():
            if ("amount" in key) and (value is not None):
                write_to_database_outflow(param_date, key, value)

        amount_given_to_investment = form.data["given_to_investment"] or 0
        amount_drawn_from_investment = form.data["drawn_from_investment"] or 0
        daily_sheet.float_amount_given_to_investments = amount_given_to_investment

        daily_sheet.float_amount_taken_from_investments = amount_drawn_from_investment

        daily_sheet.float_amount_investment_closing_balance = (
            return_prev_day_closing_balance(param_date, "Investment")
            + amount_given_to_investment
            - amount_drawn_from_investment
        )

        # yesterday closing balance + inflow - outflow + investment_inflow - investment_outflow
        daily_sheet.float_amount_hdfc_closing_balance = (
            return_prev_day_closing_balance(param_date, "HDFC")
            + display_inflow(param_date)
            - fill_outflow(param_date)
            - amount_given_to_investment
        )
        db.session.commit()

        return redirect(
            url_for(
                "funds.add_remarks",
                date_string=date_string,
            )
        )

    for item in outflow_amounts:
        form[item].data = fill_outflow(param_date, item) or 0

    form.drawn_from_investment.data = (
        (daily_sheet.float_amount_taken_from_investments or 0) if daily_sheet else 0
    )
    form.given_to_investment.data = (
        (daily_sheet.float_amount_given_to_investments or 0) if daily_sheet else 0
    )

    return render_template(
        "enter_outflow.html",
        form=form,
        display_date=param_date,
        enable_update=enable_update,
        display_inflow=display_inflow,
        investment_list=investment_list,
        list_outgo=list_outgo,
    )


def enable_update(date):
    # print(date, datetime.date.today())
    if datetime.date.today() == date.date():
        return True
    else:
        return False


def write_to_database_outflow(date, key, amount):
    from extensions import db

    outflow_query = db.session.query(DailyOutflow).filter(
        DailyOutflow.outflow_date == date
    )
    if key:
        outflow_query = outflow_query.filter(
            DailyOutflow.outflow_description == key
        ).first()
        if outflow_query:
            outflow_query.outflow_amount = amount
            db.session.commit()
        else:
            outflow = DailyOutflow(
                outflow_date=date,
                outflow_description=key,
                outflow_amount=amount,
            )
            db.session.add(outflow)
            db.session.commit()


def fill_outflow(date, description=None):
    from extensions import db

    outflow = db.session.query(func.sum(DailyOutflow.outflow_amount)).filter(
        DailyOutflow.outflow_date == date
    )
    if description:
        outflow = outflow.filter(
            DailyOutflow.outflow_description == description
        ).first()
        return outflow[0] or 0

    return outflow[0][0] or 0


@funds_bp.route("/add_remarks/<string:date_string>", methods=["GET", "POST"])
@login_required
def add_remarks(date_string):
    from extensions import db

    form = DailySummaryForm()
    param_date = datetime.datetime.strptime(date_string, "%d%m%Y")
    daily_sheet = DailySheet.query.filter(
        DailySheet.date_current_date == param_date
    ).first()
    if form.validate_on_submit():
        daily_sheet.text_major_collections = form.data["major_receipts"]
        daily_sheet.text_major_payments = form.data["major_payments"]

        db.session.commit()
        return redirect(
            url_for(
                "funds.daily_summary",
                date_string=date_string,
            )
        )
    form.major_receipts.data = (
        (daily_sheet.text_major_collections or None) if daily_sheet else None
    )
    form.major_payments.data = (
        (daily_sheet.text_major_payments or None) if daily_sheet else None
    )
    # print(datetime.date.today())
    # print(param_date)
    return render_template(
        "add_remarks.html",
        form=form,
        display_date=param_date,
        enable_update=enable_update,
        display_inflow=display_inflow,
        display_outflow=fill_outflow,
    )


def return_prev_day_closing_balance(date: datetime, type: str):
    from extensions import db

    daily_summary = (
        db.session.query(DailySheet)
        .filter(DailySheet.date_current_date < date)
        .order_by(DailySheet.date_current_date.desc())
        .limit(1)
    ).first()
    # print(daily_summary)
    if daily_summary:
        if type == "Investment":
            return daily_summary.float_amount_investment_closing_balance or 0
        elif type == "HDFC":
            return daily_summary.float_amount_hdfc_closing_balance or 0
    else:
        return 0


@funds_bp.route("/daily_summary/<string:date_string>", methods=["GET", "POST"])
@login_required
def daily_summary(date_string):
    from extensions import db

    param_date = datetime.datetime.strptime(date_string, "%d%m%Y")
    #    outflow = DailyOutflow.query.filter(DailyOutflow.outflow_date == param_date).first()
    daily_sheet = DailySheet.query.filter(
        DailySheet.date_current_date == param_date
    ).first()
    flag_description = db.session.query(FlagSheet.flag_description)
    #    print(flag_description)
    # inflow = BankStatement.query.filter(BankStatement.date_uploaded_date == param_date)
    return render_template(
        "daily_summary.html",
        display_date=param_date,
        # outflow=outflow,
        daily_sheet=daily_sheet,
        display_inflow=display_inflow,
        outflow_items=zip(outflow_labels, outflow_amounts),
        right_length=len(outflow_labels),
        # outflow_amounts=outflow_amounts,
        display_outflow=fill_outflow,
        flag_description=flag_description,
        return_prev_day_closing_balance=return_prev_day_closing_balance,
        get_inflow_total=get_inflow_total,
        pdf=False,
    )


@funds_bp.route("/daily_summary/pdf/<string:date_string>", methods=["GET", "POST"])
@login_required
def daily_summary_pdf(date_string):
    from extensions import db

    param_date = datetime.datetime.strptime(date_string, "%d%m%Y")
    #    outflow = DailyOutflow.query.filter(DailyOutflow.outflow_date == param_date).first()
    daily_sheet = DailySheet.query.filter(
        DailySheet.date_current_date == param_date
    ).first()
    flag_description = db.session.query(FlagSheet.flag_description)
    #    print(flag_description)
    # inflow = BankStatement.query.filter(BankStatement.date_uploaded_date == param_date)
    return render_template(
        "daily_summary.html",
        display_date=param_date,
        # outflow=outflow,
        daily_sheet=daily_sheet,
        display_inflow=display_inflow,
        outflow_items=zip(outflow_labels, outflow_amounts),
        right_length=len(outflow_labels),
        # outflow_amounts=outflow_amounts,
        display_outflow=fill_outflow,
        flag_description=flag_description,
        return_prev_day_closing_balance=return_prev_day_closing_balance,
        get_inflow_total=get_inflow_total,
        pdf=True,
    )


def display_inflow(input_date, inflow_description=None):
    from extensions import db

    inflow = db.session.query(
        func.sum(BankStatement.credit), func.sum(BankStatement.ledger_balance)
    ).filter(BankStatement.date_uploaded_date == input_date)
    if inflow_description:
        inflow = inflow.filter(BankStatement.flag_description == inflow_description)
        # if inflow_description in ["HDFC OPENING BAL", "HDFC CLOSING BAL"]:
        #     # Opening balance and closing balances values are stored in ledger_balance column
        #     print(type(inflow[0][1]))
        #     return inflow[0][1]

    return inflow[0][0] or 0


def add_flag(df_bank_statement):
    # obtain flag from database and store it as pandas dataframe
    engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
    df_flag_sheet = pd.read_sql("flag_sheet", engine)
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
            "flag_sheet",
            engine,
            if_exists="append",
            index=False,
        )
    return render_template(
        "upload_file_template.html", form=form, title="Upload flag sheet"
    )


# @funds_bp.route("/add_summary", methods=["POST", "GET"])
# @login_required
# def add_daily_summary():
#     form = DailySummaryForm()
#     from extensions import db

#     if form.validate_on_submit():
#         current_date = form.data["current_date"]
#         total_receipts = form.data["total_receipts"]
#         total_payments = form.data["total_payments"]

#         major_receipts = form.data["major_receipts"]
#         major_payments = form.data["major_payments"]

#         amount_given_to_investments = form.data["amount_given_to_investments"]
#         amount_received_from_investments = form.data["amount_received_from_investments"]

#         remarks = form.data["remarks"]

#         summary = DailySheet(
#             date_current_date=current_date,
#             float_receipts=total_receipts,
#             float_payments=total_payments,
#             text_major_collections=major_receipts,
#             text_major_payments=major_payments,
#             float_amount_given_to_investments=amount_given_to_investments,
#             float_amount_taken_from_investments=amount_received_from_investments,
#             text_remarks=remarks,
#             created_by=current_user.username,
#             date_created_date=datetime.now(),
#         )
#         db.session.add(summary)
#         db.session.commit()
#         return redirect(url_for("funds.view_daily_summary", summary_key=summary.id))
#     return render_template(
#         "add_daily_summary.html", form=form, title="Enter daily summary"
#     )


# @funds_bp.route("/view_summary/<int:summary_key>")
# def view_daily_summary(summary_key):
#     daily_summary = DailySheet.query.get_or_404(summary_key)
#     return render_template("view_daily_summary.html", daily_summary=daily_summary)

@funds_bp.route("/add_outgo/", methods=["POST", "GET"])
@login_required
def add_major_outgo():
    from extensions import db
    form = MajorOutgoForm()
    if form.validate_on_submit():
        outgo = MajorOutgo(date_of_outgo=form.data["date_of_outgo"], float_expected_outgo=form.data["amount_expected_outgo"],
                           text_dept=form.data["department"],
                           text_remarks=form.data["remarks"],
                           current_status=form.data["current_status"])
        db.session.add(outgo)
        db.session.commit()
        return redirect(url_for("funds.list_outgo"))



    return render_template("outgo_edit.html", form=form)

@funds_bp.route("/edit/outgo/<int:outgo_id>/", methods=["POST", "GET"])
@login_required
def edit_major_outgo(outgo_id):
    from extensions import db
    outgo = MajorOutgo.query.get_or_404(outgo_id)
    form = MajorOutgoForm()
    if form.validate_on_submit():
        outgo.date_of_outgo = form.data["date_of_outgo"]
        outgo.float_expected_outgo = form.data["amount_expected_outgo"]
        outgo.text_dept = form.data["department"]
        outgo.text_remarks = form.data["remarks"]
        outgo.current_status = form.data["current_status"]
        db.session.commit()
        return redirect(url_for("funds.list_outgo"))
    form.date_of_outgo.data = outgo.date_of_outgo
    form.amount_expected_outgo.data = outgo.float_expected_outgo
    form.department.data = outgo.text_dept
    form.remarks.data = outgo.text_remarks
    form.current_status.data = outgo.current_status
    return render_template("outgo_edit.html", form=form)



@funds_bp.route("/list_outgo/", methods=["POST", "GET"])
@login_required
def list_outgo():
    list_outgo = MajorOutgo.query.order_by(MajorOutgo.date_of_outgo.asc())
    #print(list_outgo.all())
    return render_template("outgo_list.html", list_outgo=list_outgo)

@funds_bp.route("/add_amount_investment", methods=["POST", "GET"])
@login_required
def add_amount_given_to_investment():
    from extensions import db

    form = AmountGivenToInvestmentForm()
    if form.validate_on_submit():
        date_given = form.data["date_given_to_investment"]
        amount_given = form.data["amount_given_to_investment"]
        expected_date_amount_return = form.data["expected_date_amount_return"]
        remarks = form.data["remarks"]
        current_status = form.data["current_status"]
        given_to_investment = AmountGivenToInvestment(
            date_given_to_investment=date_given,
            float_amount_given_to_investment=amount_given,
            text_remarks=remarks,
            date_expected_date_of_return=expected_date_amount_return,
            current_status=current_status,
        )
        db.session.add(given_to_investment)
        db.session.commit()
        return redirect(url_for("funds.list_amount_given_to_investment"))

    return render_template("investment_edit_amount.html", form=form)

@funds_bp.route("/edit_amount_investment/<int:investment_id>", methods=["POST", "GET"])
@login_required
def edit_amount_given_to_investment(investment_id):
    from extensions import db
    investment = AmountGivenToInvestment.query.get_or_404(investment_id)

    form = AmountGivenToInvestmentForm()
    if form.validate_on_submit():
        investment.date_given_to_investment = form.data["date_given_to_investment"]
        investment.float_amount_given_to_investment = form.data["amount_given_to_investment"]
        investment.date_expected_date_amount_return = form.data["expected_date_amount_return"]
        investment.text_remarks = form.data["remarks"] or None
        investment.current_status = form.data["current_status"]
        db.session.commit()
    form.date_given_to_investment.data = investment.date_given_to_investment
    form.amount_given_to_investment.data = investment.float_amount_given_to_investment
    form.expected_date_amount_return.data = investment.date_expected_date_of_return
    form.remarks.data = investment.text_remarks
    form.current_status.data = investment.current_status
    return render_template("investment_edit_amount.html", form=form)

@funds_bp.route("/list_amount_investment/")
@login_required
def list_amount_given_to_investment():
    investment_list = AmountGivenToInvestment.query.order_by(AmountGivenToInvestment.date_expected_date_of_return.asc())

    return render_template("investment_list.html", investment_list=investment_list)


# @funds_bp.route("/horo", methods=["POST", "GET"])
# def hororecon():

#     if request.method == "POST":


#         print(request.form.to_dict())


#     return render_template("hororecon.html")
