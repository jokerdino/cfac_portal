from datetime import datetime, date
import pandas as pd

from flask import (
    current_app,
    render_template,
    send_from_directory,
    flash,
    request,
    redirect,
    url_for,
)

from flask_login import login_required, current_user
from sqlalchemy import func, case, union, create_engine

from . import funds_bp
from .funds_form import FundsJVForm, UploadFileForm, JVFlagAddForm
from .funds_model import (
    FundBankStatement,
    FundDailyOutflow,
    FundDailySheet,
    FundJournalVoucherFlagSheet,
)

from set_view_permissions import fund_managers, admin_required
from extensions import db


@funds_bp.route("/download_jv/", methods=["POST", "GET"])
@login_required
@fund_managers
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
        start_date = form.data["start_date"] or date.today()
        # if no end date is provided, default to today
        end_date = form.data["end_date"] or date.today()

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
        df_inflow = prepare_inflow_jv(df_funds, df_flags, flag_description)
        df_merged = pd.concat(
            [
                # prepare_inflow_jv(df_funds, df_flags, flag_description),
                df_inflow,
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
            datetime_string = datetime.now()
            with pd.ExcelWriter(
                f"download_data/funds_jv/HDFC JV_{datetime_string:%d%m%Y%H%M%S}.xlsx"
            ) as writer:
                df_merged.to_excel(writer, sheet_name="JV", index=False)
                df_inflow.to_excel(writer, sheet_name="inflow", index=False)
            return send_from_directory(
                directory="download_data/funds_jv/",
                path=f"HDFC JV_{datetime_string:%d%m%Y%H%M%S}.xlsx",
                download_name=f"HDFC_JV_{start_date}_{end_date}.xlsx",
                as_attachment=True,
            )

        else:
            return "no data"

    return render_template("jv_download_jv_macro.html", form=form)


def filter_unidentified_credits(df_inflow: pd.DataFrame, engine) -> pd.DataFrame:
    # engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))

    flag_description: list[str] = prepare_jv_flag(engine)[1]

    df_inflow_copy = df_inflow.copy()

    df_inflow_copy["DESCRIPTION"] = df_inflow_copy["description"].apply(
        lambda x: "".join([part for part in flag_description if part in str(x)])
    )

    df_unidentified_credits = df_inflow_copy[df_inflow_copy["DESCRIPTION"] == ""].copy()

    df_unidentified_credits = df_unidentified_credits.drop(columns=["DESCRIPTION"])
    df_unidentified_credits["date_created_date"] = datetime.now()
    df_unidentified_credits["created_by"] = current_user.username
    df_unidentified_credits["bool_jv_passed"] = False

    return df_unidentified_credits


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


@funds_bp.route("/jv_flags/", methods=["GET", "POST"])
@login_required
@fund_managers
def view_jv_flags():

    list = FundJournalVoucherFlagSheet.query.order_by(FundJournalVoucherFlagSheet.id)
    column_names = FundJournalVoucherFlagSheet.query.statement.columns.keys()

    return render_template("jv_view_flags.html", list=list, column_names=column_names)


@funds_bp.route("/jv_flags/upload", methods=["GET", "POST"])
@login_required
@fund_managers
def upload_jv_flags():

    form = UploadFileForm()

    if form.validate_on_submit():
        jv_flag_sheet = form.data["file_upload"]
        df_jv_flag_sheet = pd.read_excel(
            jv_flag_sheet,
            dtype={
                "txt_description": str,
                "txt_flag": str,
                "txt_gl_code": str,
                "txt_sl_code": str,
            },
        )
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))

        df_jv_flag_sheet["date_created_date"] = datetime.now()
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


@funds_bp.route("/jv_flags/add", methods=["POST", "GET"])
@login_required
@admin_required
def add_jv_flag():
    """Add new JV flag patterns through model form"""

    jv = FundJournalVoucherFlagSheet()

    if request.method == "POST":
        form = JVFlagAddForm(request.form, obj=jv)
        if form.validate():
            form.populate_obj(jv)
            db.session.add(jv)
            db.session.commit()
            return redirect(url_for(".view_jv_flags"))
    else:
        form = JVFlagAddForm()

    return render_template(
        "jv_pattern_add.html",
        form=form,
        title="Add new JV pattern",
    )


@funds_bp.route("/jv_flags/<int:jv_id>/edit/", methods=["POST", "GET"])
@login_required
@admin_required
def edit_jv_flag(jv_id):
    """Edit JV flag patterns through model form"""

    jv = db.get_or_404(FundJournalVoucherFlagSheet, jv_id)

    if request.method == "POST":
        form = JVFlagAddForm(request.form, obj=jv)
        if form.validate():
            form.populate_obj(jv)
            db.session.add(jv)
            db.session.commit()
            return redirect(url_for(".view_jv_flags"))
    else:
        form = JVFlagAddForm(obj=jv)

    return render_template(
        "jv_pattern_add.html",
        form=form,
        title="Edit JV pattern",
    )
