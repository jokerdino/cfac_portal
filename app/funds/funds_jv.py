from datetime import datetime, date
from io import BytesIO
from typing import Any

import pandas as pd

from flask import (
    render_template,
    send_file,
    request,
    redirect,
    url_for,
)

from flask_login import login_required, current_user


from . import funds_bp
from .funds_form import FundsJVForm, JVFlagAddForm
from .funds_model import (
    FundBankStatement,
    FundDailyOutflow,
    FundDailySheet,
    FundJournalVoucherFlagSheet,
)

from set_view_permissions import fund_managers, admin_required
from extensions import db


# @funds_bp.route("/download_jv/", methods=["POST", "GET"])
# @login_required
# @fund_managers
# def download_jv():
#     """Function to generate generate Fund Journal voucher from available data
#     Input required: Start date and end date
#     Inflow query is run to collect all data from bank statement
#     Inflow and amount drawn from investment is collected from inflow query
#     Outflow query is used to collect all outflow data
#     Investment query is used to collect money given to investment
#     Note: Amount drawn from investment is already collected from inflow query and not required to run again separately
#     Output: Pandas dataframe written to excel file with start date and end date added to file name for quick reference.
#     """

#     form = FundsJVForm()

#     if form.validate_on_submit():
#         # if no start date is provided, default to today
#         start_date = form.data["start_date"] or date.today()
#         # if no end date is provided, default to today
#         end_date = form.data["end_date"] or date.today()

#         all_queries = []

#         # inflow case and query
#         # all inflows from bank statement is collected
#         # this includes amount drawn from investment
#         case_inflow = case((FundBankStatement.credit != 0, "Inflow"), else_="").label(
#             "Type"
#         )
#         inflow_query = (
#             db.session.query(FundBankStatement)
#             .with_entities(
#                 FundBankStatement.value_date.label("Date"),
#                 func.concat(
#                     FundBankStatement.description, FundBankStatement.reference_no
#                 ).label("Bank Description"),
#                 FundBankStatement.credit.label("Amount"),
#                 case_inflow,
#             )
#             .filter(
#                 (
#                     (FundBankStatement.value_date >= start_date)
#                     & (FundBankStatement.value_date <= end_date)
#                 )
#                 & (FundBankStatement.credit != 0)
#             )
#         )
#         all_queries.append(inflow_query)

#         # outflow case and query
#         # fund JV flag sheet contains flag in upper case and without underscore

#         case_outflow = case(
#             (FundDailyOutflow.outflow_amount > 0, "Outflow"), else_=""
#         ).label("Type")

#         # func.upper and func.replace is used to uppercase the results and remove "amount" and underscore from results
#         # this is because our JV flag sheet has flags in upper case and without "AMOUNT" and underscore
#         outflow_query = (
#             db.session.query(FundDailyOutflow)
#             .with_entities(
#                 FundDailyOutflow.outflow_date.label("Date"),
#                 func.upper(
#                     func.replace(
#                         func.replace(
#                             FundDailyOutflow.outflow_description, "amount_", ""
#                         ),
#                         "_",
#                         " ",
#                     )
#                 ).label("Bank Description"),
#                 FundDailyOutflow.outflow_amount.label("Amount"),
#                 case_outflow,
#             )
#             .filter(
#                 (FundDailyOutflow.outflow_date >= start_date)
#                 & (FundDailyOutflow.outflow_date <= end_date)
#                 & (FundDailyOutflow.outflow_amount > 0)
#             )
#         )
#         all_queries.append(outflow_query)

#         # investment case and query
#         # amount given to investment is sourced here
#         # amount drawn from investment is already collected in inflow query (straight from bank statement)
#         case_investment_given = case(
#             (
#                 FundDailySheet.float_amount_given_to_investments > 0,
#                 "Given to investment",
#             ),
#             else_="",
#         ).label("Type")

#         investment_given_query = (
#             db.session.query(FundDailySheet)
#             .with_entities(
#                 FundDailySheet.date_current_date.label("Date"),
#                 case_investment_given.label("Bank Description"),
#                 FundDailySheet.float_amount_given_to_investments.label("Amount"),
#                 case_investment_given,
#             )
#             .filter(
#                 (FundDailySheet.date_current_date >= start_date)
#                 & (FundDailySheet.date_current_date <= end_date)
#                 & (FundDailySheet.float_amount_given_to_investments > 0)
#             )
#         )

#         all_queries.append(investment_given_query)

#         query_set = union_all(*all_queries)

#         with db.engine.connect() as conn:
#             df_funds = pd.read_sql(query_set, conn)

#         df_funds["Office Location"] = "000100"

#         df_funds["Date"] = pd.to_datetime(df_funds["Date"], format="%d/%m/%Y")

#         df_flags, flag_description = prepare_jv_flag()
#         df_inflow = prepare_inflow_jv(df_funds, df_flags, flag_description)
#         df_merged = pd.concat(
#             [
#                 df_inflow,
#                 prepare_outflow_jv(df_funds, df_flags, flag_description),
#                 prepare_investment_jv(df_funds),
#             ]
#         )

#         if not df_merged.empty:
#             df_merged = df_merged[
#                 ["Office Location", "GL Code", "SL Code", "DR/CR", "Amount", "Remarks"]
#             ]
#             df_merged["GL Code"] = pd.to_numeric(df_merged["GL Code"])
#             df_merged["SL Code"] = pd.to_numeric(df_merged["SL Code"])
#             # datetime_string = datetime.now()
#             output = BytesIO()
#             with pd.ExcelWriter(output) as writer:
#                 df_merged.to_excel(writer, sheet_name="JV", index=False)
#                 df_inflow.to_excel(writer, sheet_name="inflow", index=False)
#             output.seek(0)
#             return send_file(
#                 output,
#                 download_name=f"HDFC_JV_{start_date}_{end_date}.xlsx",
#                 as_attachment=True,
#             )

#         else:
#             return "no data"

#     return render_template(
#         "funds_form.html",
#         form=form,
#         title="Enter dates for downloading funds JV",
#     )


@funds_bp.route("/download_jv2/", methods=["POST", "GET"])
@login_required
@fund_managers
def download_jv2():
    """Function to generate generate Fund Journal voucher from available data
    Input required: Start date and end date
    Inflow query is run to collect all data from bank statement
    Inflow and amount drawn from investment is collected from inflow query
    Outflow query is used to collect all outflow data
    Investment query is used to collect money given to investment
    Note: Amount drawn from investment is already collected from inflow query and not required to run again separately
    Output: Pandas dataframe written to excel file with start date and end date added to file name for quick reference.
    """

    form = FundsJVForm()

    if form.validate_on_submit():
        start_date = form.start_date.data or date.today()
        end_date = form.end_date.data or date.today()

        inflow_query_list = prepare_inflow_jv_new(start_date, end_date)
        outflow_query_list = prepare_outflow_jv_new(start_date, end_date)
        investment_query_list = prepare_investment_jv_new(start_date, end_date)

        query_set = db.union_all(
            *inflow_query_list, *outflow_query_list, *investment_query_list
        )

        inflow_details_list = prepare_inflow_details(start_date, end_date)

        with db.engine.connect() as conn:
            df_merged = pd.read_sql(query_set, conn)
            df_inflow = pd.read_sql(inflow_details_list, conn)

        if not df_merged.empty:
            df_merged["GL Code"] = pd.to_numeric(df_merged["GL Code"])
            df_merged["SL Code"] = pd.to_numeric(df_merged["SL Code"])

            output = BytesIO()
            with pd.ExcelWriter(output) as writer:
                df_merged.to_excel(writer, sheet_name="JV", index=False)
                df_inflow.to_excel(writer, sheet_name="Inflow", index=False)

            output.seek(0)
            return send_file(
                output,
                download_name=f"HDFC_JV_{start_date}_{end_date}.xlsx",
                as_attachment=True,
            )

        else:
            return "no data"

    return render_template(
        "funds_form.html",
        form=form,
        title="Enter dates for downloading funds JV",
    )


def filter_unidentified_credits(df_inflow: pd.DataFrame) -> pd.DataFrame:
    flag_description: list[str] = prepare_jv_flag()[1]

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


def prepare_jv_flag() -> tuple[pd.DataFrame, list[str]]:
    df_flags = pd.read_sql("fund_journal_voucher_flag_sheet", db.engine)

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


# def prepare_investment_jv(df_funds_excel: pd.DataFrame) -> pd.DataFrame:
#     """Obsolete function: Use prepare_investment_jv_new function instead."""
#     df_investment = df_funds_excel[
#         df_funds_excel["Type"] == "Given to investment"
#     ].copy()
#     if df_investment.empty:
#         return pd.DataFrame()

#     df_investment["GL Code"] = 5121900700
#     df_investment["SL Code"] = 0
#     df_investment["Remarks"] = "Given to investment " + df_investment[
#         "Date"
#     ].dt.strftime("%d/%m/%Y").astype(str)

#     df_investment["DR/CR"] = "DR"
#     df_investment_actual = df_investment.copy()

#     df_investment_actual["GL Code"] = 9111310000
#     df_investment_actual["SL Code"] = 12404226
#     df_investment_actual["DR/CR"] = "CR"

#     df_investment_merged = pd.concat([df_investment_actual, df_investment])

#     return df_investment_merged


# def prepare_outflow_jv(
#     df_funds_excel: pd.DataFrame, df_flags: pd.DataFrame, flag_description: list[str]
# ) -> pd.DataFrame:
#     """Obsolete function: Use prepare_outflow_jv_new function instead."""
#     df_outflow = df_funds_excel[df_funds_excel["Type"] == "Outflow"].copy()

#     if df_outflow.empty:
#         return pd.DataFrame()

#     df_outflow["DESCRIPTION"] = df_outflow["Bank Description"].apply(
#         lambda x: "".join([part for part in flag_description if part in str(x)])
#     )

#     df_outflow["DESCRIPTION"] = df_outflow["DESCRIPTION"].replace(
#         r"^\s*$", "OTHERS", regex=True
#     )

#     df_outflow = df_outflow.merge(df_flags, on="DESCRIPTION", how="left")

#     df_outflow["Remarks"] = (
#         df_outflow["DESCRIPTION"]
#         + " "
#         + df_outflow["FLAG"]
#         + " "
#         + df_outflow["Date"].dt.strftime("%d/%m/%Y").astype(str)
#     )
#     df_outflow["DR/CR"] = "DR"

#     df_outflow_actual = df_outflow.copy()

#     df_outflow_actual["GL Code"] = 9111310000
#     df_outflow_actual["SL Code"] = 12404226
#     df_outflow_actual["DR/CR"] = "CR"

#     df_merged_outflow = pd.concat([df_outflow_actual, df_outflow])

#     return df_merged_outflow


# def prepare_inflow_jv(
#     df_funds_excel: pd.DataFrame, df_flags: pd.DataFrame, flag_description: list[str]
# ) -> pd.DataFrame:
#     """Obsolete function: Use prepare_inflow_jv_new function"""
#     df_inflow = df_funds_excel[df_funds_excel["Type"] == "Inflow"].copy()
#     if df_inflow.empty:
#         return pd.DataFrame()

#     df_inflow["DESCRIPTION"] = df_inflow["Bank Description"].apply(
#         lambda x: "".join([part for part in flag_description if part in str(x)])
#     )

#     df_inflow["DESCRIPTION"] = df_inflow["DESCRIPTION"].replace(
#         r"^\s*$", "OTHERS", regex=True
#     )

#     df_inflow = df_inflow.merge(df_flags, on="DESCRIPTION", how="left")

#     df_inflow["Remarks"] = (
#         df_inflow["FLAG"] + " " + df_inflow["Date"].dt.strftime("%d/%m/%Y").astype(str)
#     )

#     df_inflow.loc[df_inflow["Amount"] > 0, "DR/CR"] = "CR"
#     df_inflow.loc[df_inflow["Amount"] < 0, "DR/CR"] = "DR"
#     df_inflow.loc[df_inflow["Amount"] < 0, "Amount"] = df_inflow["Amount"] * -1

#     df_inflow_actual = df_inflow.copy()

#     df_inflow_actual["GL Code"] = 9111310000
#     df_inflow_actual["SL Code"] = 12404226
#     df_inflow_actual.loc[df_inflow["DR/CR"] == "DR", "DR/CR"] = "CR"
#     df_inflow_actual.loc[df_inflow["DR/CR"] == "CR", "DR/CR"] = "DR"

#     df_merged = pd.concat([df_inflow_actual, df_inflow])
#     return df_merged


def prepare_inflow_jv_new(start_date, end_date) -> list[Any]:
    inflow_credit_query = (
        db.select(
            db.literal("000100").label("Office Location"),
            db.func.coalesce(
                FundJournalVoucherFlagSheet.txt_gl_code, "5131405950"
            ).label("GL Code"),
            db.func.coalesce(FundJournalVoucherFlagSheet.txt_sl_code, "0").label(
                "SL Code"
            ),
            db.case((FundBankStatement.credit > 0, "CR"), else_="DR").label("DR/CR"),
            db.case(
                (FundBankStatement.credit < 0, -FundBankStatement.credit),
                else_=FundBankStatement.credit,
            ).label("Amount"),
            db.func.concat(
                db.func.coalesce(FundJournalVoucherFlagSheet.txt_flag, "OTHERS"),
                " ",
                db.func.to_char(FundBankStatement.value_date, "DD/MM/YYYY"),
            ).label("Remarks"),
        )
        .outerjoin(
            FundBankStatement.flag,
        )
        .where(
            db.and_(
                (FundBankStatement.value_date.between(start_date, end_date)),
                FundBankStatement.credit != 0,
            )
        )
    )
    inflow_debit_query = (
        db.select(
            db.literal("000100").label("Office Location"),
            db.literal("9111310000").label("GL Code"),
            db.literal("12404226").label("SL Code"),
            db.case((FundBankStatement.credit < 0, "CR"), else_="DR").label("DR/CR"),
            db.case(
                (FundBankStatement.credit < 0, -FundBankStatement.credit),
                else_=FundBankStatement.credit,
            ).label("Amount"),
            db.func.concat(
                db.func.coalesce(FundJournalVoucherFlagSheet.txt_flag, "OTHERS"),
                " ",
                db.func.to_char(FundBankStatement.value_date, "DD/MM/YYYY"),
            ).label("Remarks"),
        )
        .outerjoin(
            FundBankStatement.flag,
        )
        .where(
            db.and_(
                (FundBankStatement.value_date.between(start_date, end_date)),
                FundBankStatement.credit != 0,
            )
        )
    )
    return [inflow_credit_query, inflow_debit_query]


def prepare_inflow_details(start_date, end_date):
    inflow_credit_query = (
        db.select(
            db.func.to_char(FundBankStatement.value_date, "DD/MM/YYYY").label(
                "Value date"
            ),
            FundBankStatement.description.label("Bank Description"),
            FundBankStatement.reference_no.label("Reference No"),
            db.func.coalesce(FundJournalVoucherFlagSheet.txt_flag, "OTHERS").label(
                "Flag name"
            ),
            db.func.coalesce(
                FundJournalVoucherFlagSheet.txt_description, "OTHERS"
            ).label("Flag pattern"),
            db.func.coalesce(
                FundJournalVoucherFlagSheet.txt_gl_code, "5131405950"
            ).label("GL Code"),
            db.func.coalesce(FundJournalVoucherFlagSheet.txt_sl_code, "0").label(
                "SL Code"
            ),
            db.case((FundBankStatement.credit > 0, "CR"), else_="DR").label("DR/CR"),
            db.case(
                (FundBankStatement.credit < 0, -FundBankStatement.credit),
                else_=FundBankStatement.credit,
            ).label("Amount"),
            db.func.concat(
                db.func.coalesce(FundJournalVoucherFlagSheet.txt_flag, "OTHERS"),
                " ",
                db.func.to_char(FundBankStatement.value_date, "DD/MM/YYYY"),
            ).label("Remarks"),
        )
        .outerjoin(
            FundBankStatement.flag,
        )
        .where(
            db.and_(
                (FundBankStatement.value_date.between(start_date, end_date)),
                FundBankStatement.credit != 0,
            )
        )
    ).order_by(FundBankStatement.id)

    return inflow_credit_query


def prepare_investment_jv_new(start_date, end_date) -> list[Any]:
    investment_debit_query = db.select(
        db.literal("000100").label("Office Location"),
        db.literal("9111310000").label("GL Code"),
        db.literal("12404226").label("SL Code"),
        db.literal("CR").label("DR/CR"),
        FundDailySheet.float_amount_given_to_investments.label("Amount"),
        db.func.concat(
            "Given to investment ",
            db.func.to_char(FundDailySheet.date_current_date, "DD/MM/YYYY"),
        ).label("Remarks"),
    ).where(
        db.and_(
            (FundDailySheet.date_current_date.between(start_date, end_date)),
            FundDailySheet.float_amount_given_to_investments > 0,
        )
    )
    investment_credit_query = db.select(
        db.literal("000100").label("Office Location"),
        db.literal("5121900700").label("GL Code"),
        db.literal("0").label("SL Code"),
        db.literal("DR").label("DR/CR"),
        FundDailySheet.float_amount_given_to_investments.label("Amount"),
        db.func.concat(
            "Given to investment ",
            db.func.to_char(FundDailySheet.date_current_date, "DD/MM/YYYY"),
        ).label("Remarks"),
    ).where(
        db.and_(
            (FundDailySheet.date_current_date.between(start_date, end_date)),
            FundDailySheet.float_amount_given_to_investments > 0,
        )
    )
    return [investment_debit_query, investment_credit_query]


def prepare_outflow_jv_new(start_date, end_date) -> list[Any]:
    outflow_credit_query = (
        db.select(
            db.literal("000100").label("Office Location"),
            db.literal("9111310000").label("GL Code"),
            db.literal("12404226").label("SL Code"),
            db.literal("CR").label("DR/CR"),
            FundDailyOutflow.outflow_amount.label("Amount"),
            db.func.concat(
                FundDailyOutflow.normalized_description,
                " ",
                FundJournalVoucherFlagSheet.txt_flag,
                " ",
                db.func.to_char(FundDailyOutflow.outflow_date, "DD/MM/YYYY"),
            ).label("Remarks"),
        )
        .join(
            FundJournalVoucherFlagSheet,
            FundDailyOutflow.normalized_description.contains(
                FundJournalVoucherFlagSheet.txt_description
            ),
        )
        .where(
            db.and_(
                FundDailyOutflow.outflow_date.between(start_date, end_date),
                FundDailyOutflow.outflow_amount > 0,
            )
        )
    )
    outflow_debit_query = (
        db.select(
            db.literal("000100").label("Office Location"),
            FundJournalVoucherFlagSheet.txt_gl_code.label("GL Code"),
            FundJournalVoucherFlagSheet.txt_sl_code.label("SL Code"),
            db.literal("DR").label("DR/CR"),
            FundDailyOutflow.outflow_amount.label("Amount"),
            db.func.concat(
                FundDailyOutflow.normalized_description,
                " ",
                FundJournalVoucherFlagSheet.txt_flag,
                " ",
                db.func.to_char(FundDailyOutflow.outflow_date, "DD/MM/YYYY"),
            ).label("Remarks"),
        )
        .join(
            FundJournalVoucherFlagSheet,
            FundDailyOutflow.normalized_description.contains(
                FundJournalVoucherFlagSheet.txt_description
            ),
        )
        .where(
            db.and_(
                FundDailyOutflow.outflow_date.between(start_date, end_date),
                FundDailyOutflow.outflow_amount > 0,
            )
        )
    )
    return [outflow_credit_query, outflow_debit_query]


@funds_bp.route("/jv_flags/", methods=["GET", "POST"])
@login_required
@fund_managers
def view_jv_flags():
    list = db.session.scalars(
        db.select(FundJournalVoucherFlagSheet).order_by(FundJournalVoucherFlagSheet.id)
    )

    column_names = [col.key for col in FundJournalVoucherFlagSheet.__table__.columns]

    return render_template("jv_view_flags.html", list=list, column_names=column_names)


# @funds_bp.route("/jv_flags/upload", methods=["GET", "POST"])
# @login_required
# @fund_managers
# def upload_jv_flags():
#     form = UploadFileForm()

#     if form.validate_on_submit():
#         jv_flag_sheet = form.data["file_upload"]
#         df_jv_flag_sheet = pd.read_excel(
#             jv_flag_sheet,
#             dtype={
#                 "txt_description": str,
#                 "txt_flag": str,
#                 "txt_gl_code": str,
#                 "txt_sl_code": str,
#             },
#         )

#         df_jv_flag_sheet["date_created_date"] = datetime.now()
#         df_jv_flag_sheet["created_by"] = current_user.username

#         df_jv_flag_sheet.to_sql(
#             "fund_journal_voucher_flag_sheet",
#             db.engine,
#             if_exists="append",
#             index=False,
#         )
#         flash("Flags for Journal voucher have been uploaded successfully.")
#     return render_template(
#         "upload_file_template.html",
#         form=form,
#         title="Upload flags for journal voucher",
#     )


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
        "funds_form.html",
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
        "funds_form.html",
        form=form,
        title="Edit JV pattern",
    )
