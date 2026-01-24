from datetime import datetime
from io import BytesIO

import numpy as np
import pandas as pd
from flask import flash, render_template, send_file
from flask_login import current_user, login_required

from extensions import db
from set_view_permissions import admin_required

from . import coinsurance_bp
from .coinsurance_form import (
    CoinsuranceBalanceForm,
    CoinsuranceBalanceQueryForm,
    FilterMonthForm,
)
from .coinsurance_model import CoinsuranceBalances


def populate_period_choices(form):
    # Querying distinct list of periods from the table
    period_list_query = db.session.scalars(
        db.select(CoinsuranceBalances.period).distinct()
    )

    # converting the period from string to datetime object
    list_period = [datetime.strptime(item, "%b-%y") for item in period_list_query]

    # sorting the items of list_period in reverse order
    # newer months will be above
    list_period.sort(reverse=True)

    # list_period is now dynamically added as dropdown choice list to the SelectField
    form.period.choices = [
        (item.strftime("%b-%y"), item.strftime("%B-%Y")) for item in list_period
    ]

    # default choice is set from the top most option in form.period.choices
    period = form.period.choices[0][0]
    return period


@coinsurance_bp.route("/coinsurance_balance/", methods=["POST", "GET"])
@login_required
def query_view_coinsurance_balance():
    form = CoinsuranceBalanceQueryForm()
    period = populate_period_choices(form)

    if form.validate_on_submit():
        period = form.data["period"]
    coinsurance_balance = db.select(CoinsuranceBalances).where(
        CoinsuranceBalances.period == period
    )

    summary = (
        db.select(
            CoinsuranceBalances.company_name,
            db.func.sum(CoinsuranceBalances.hub_due_to_claims),
            db.func.sum(CoinsuranceBalances.hub_due_to_premium),
            db.func.sum(CoinsuranceBalances.oo_due_to),
            db.func.sum(CoinsuranceBalances.hub_due_from_claims),
            db.func.sum(CoinsuranceBalances.hub_due_from_premium),
            db.func.sum(CoinsuranceBalances.oo_due_from),
            db.func.sum(CoinsuranceBalances.net_amount),
        )
        .where(CoinsuranceBalances.period == period)
        .group_by(CoinsuranceBalances.company_name)
        .order_by(CoinsuranceBalances.company_name)
    )

    if not form.data["head_office_balance"]:
        summary = summary.where(
            CoinsuranceBalances.office_code.not_in(("000100", "660000", "001900"))
        )
        coinsurance_balance = coinsurance_balance.where(
            CoinsuranceBalances.office_code.not_in(("000100", "660000", "001900"))
        )

    if current_user.user_type == "ro_user":
        summary = summary.where(
            CoinsuranceBalances.str_regional_office_code == current_user.ro_code
        )
        coinsurance_balance = coinsurance_balance.where(
            CoinsuranceBalances.str_regional_office_code == current_user.ro_code
        )
    summary_query = db.session.execute(summary)
    coinsurance_balance_query = db.session.scalars(coinsurance_balance)
    return render_template(
        "view_coinsurance_balance.html",
        coinsurance_balance=coinsurance_balance_query,
        summary=summary_query,
        form=form,
        period=period,
    )


@coinsurance_bp.route("/coinsurance_balance/delete/", methods=["GET", "POST"])
@login_required
@admin_required
def delete_coinsurance_balance():
    form = FilterMonthForm()
    populate_period_choices(form)

    if form.validate_on_submit():
        period = form.period.data

        stmt = db.delete(CoinsuranceBalances).where(
            CoinsuranceBalances.period == period
        )
        db.session.execute(stmt)
        db.session.commit()
        flash(f"{period} has been deleted.")

    return render_template("coinsurance_balance_delete.html", form=form)


@coinsurance_bp.route("/coinsurance_balance/generate", methods=["POST", "GET"])
@login_required
@admin_required
def generate_coinsurance_balance():
    form = CoinsuranceBalanceForm()

    if form.validate_on_submit():
        period = form.period.data
        #        flag_sheet = form.flag_sheet_file.data

        list_df = [
            pd.read_csv(file, dtype={"GLCode": str})
            for file in form.csv_files_upload.data
        ]

        # Concatenate all DataFrames into a single DataFrame
        df_concat = pd.concat(list_df, ignore_index=True)

        # Adjust credit and debit by dividing by 2 where the office code is 100
        # df_concat.loc[df_concat["Office Code"] == 100, "Credit"] = (
        #     df_concat["Credit"] / 2
        # )
        # df_concat.loc[df_concat["Office Code"] == 100, "Debit"] = df_concat["Debit"] / 2

        # Calculate the net amount by subtracting debits from credits
        df_concat["Net amount"] = df_concat["Credit"] - df_concat["Debit"]

        # Remove rows where the net amount is zero
        df_concat = df_concat[df_concat["Net amount"] != 0]

        # Load additional data for GL codes and zones from an Excel file
        # df_flag_sheet = pd.read_excel(flag_sheet, sheet_name="GLCodes")
        #   df_zones = pd.read_excel(
        #      flag_sheet, sheet_name="Zones", dtype={"Regional Code": str}
        # )
        df_flag_sheet = pd.read_sql(
            "coinsurance_balance_general_ledger_code_flag_sheet",
            db.engine,
            columns=["gl_code", "description", "company_name"],
        )
        df_zones = pd.read_sql(
            "coinsurance_balance_zone_flag_sheet",
            db.engine,
            columns=["regional_code", "zone"],
        )
        # Merge the concatenated data with the flag sheet on GLCode
        df_merged = df_concat.merge(
            df_flag_sheet, left_on="GLCode", right_on="gl_code", how="left"
        )

        # Generate office-wise and company-wise pivot tables
        pivot_df_merged_office = prepare_pivot(
            df_merged, df_zones, ["Office Code", "company_name"], period
        )
        pivot_df_merged = prepare_pivot(
            df_merged, df_zones, ["company_name", "Office Code"], period
        )

        net_off_jv = prepare_net_off(df_merged, ["company_name"], period, df_flag_sheet)

        # Generate a company-wise summary
        pivot_companywise = pivot_df_merged.pivot_table(
            index="company_name", values="Net", aggfunc="sum"
        )
        pivot_companywise.reset_index(inplace=True)
        output = BytesIO()
        upload_coinsurance_balance_refactored(pivot_df_merged_office)
        # Write the pivot tables and summary to an Excel file
        with pd.ExcelWriter(output) as writer:
            pivot_df_merged_office.to_excel(
                writer, sheet_name="office_wise", index=False
            )
            pivot_df_merged.to_excel(writer, sheet_name="company_wise", index=False)
            pivot_companywise.to_excel(writer, sheet_name="summary", index=False)
            net_off_jv.to_excel(writer, sheet_name="Net off JV", index=False)

            # Apply formatting to the Excel sheets
            format_workbook = writer.book
            format_currency = format_workbook.add_format({"num_format": "##,##,#0.00"})

            format_worksheet_oo = writer.sheets["office_wise"]
            format_worksheet_oo.set_column("C:I", 11, format_currency)
            format_worksheet_oo.autofit()

            format_worksheet_company = writer.sheets["company_wise"]
            format_worksheet_company.set_column("C:I", 11, format_currency)
            format_worksheet_company.autofit()

            format_worksheet_summary = writer.sheets["summary"]
            format_worksheet_summary.set_column("B:B", 11, format_currency)
            format_worksheet_summary.autofit()

        output.seek(0)
        return send_file(
            output,
            download_name=f"coinsurance_balance_{period}.xlsx",
            as_attachment=True,
        )

    return render_template("generate_coinsurance_balance.html", form=form)


def prepare_net_off(df_merged, index_list, period, df_gl_codes):
    # Create a pivot table based on the specified index columns and descriptions
    df_net_off = df_merged.pivot_table(
        index=index_list,
        columns="description",
        values="Net amount",
        aggfunc="sum",
    )

    # Replace NaN values with 0 and calculate the net amount
    df_net_off.fillna(0, inplace=True)
    df_net_off["Due to"] = (
        df_net_off["OO Due to"]
        + df_net_off["Hub Due to Premium"]
        + df_net_off["Hub Due to Claims"]
    )

    df_net_off["Due from"] = (
        df_net_off["OO Due from"]
        + df_net_off["Hub Due from Premium"]
        + df_net_off["Hub Due from Claims"]
    ) * -1

    df_net_off.reset_index(inplace=True)
    df_net_off = df_net_off[["company_name", "Due to", "Due from"]]
    df_net_off["Amount"] = df_net_off[["Due to", "Due from"]].min(axis=1)

    df_gl_codes = df_gl_codes[df_gl_codes["description"].str.contains("OO Due")].copy()

    df_net_off_gl_merged = df_net_off.merge(df_gl_codes, on="company_name")
    df_net_off_gl_merged["Office Location"] = "000100"
    df_net_off_gl_merged["SL Code"] = 0
    df_net_off_gl_merged["Remarks"] = (
        f"Net off JV {period} " + df_net_off_gl_merged["company_name"]
    )
    df_net_off_gl_merged.loc[
        df_net_off_gl_merged["description"] == "OO Due from", "DR/CR"
    ] = "CR"
    df_net_off_gl_merged.loc[
        df_net_off_gl_merged["description"] == "OO Due to", "DR/CR"
    ] = "DR"
    df_net_off_gl_merged.rename(columns={"gl_code": "GL Code"}, inplace=True)

    df_net_off_gl_merged = df_net_off_gl_merged[
        ["Office Location", "GL Code", "SL Code", "DR/CR", "Amount", "Remarks"]
    ]
    return df_net_off_gl_merged


def prepare_pivot(df_merged, df_zones, index_list, period):
    """
    Prepares a pivot table summarizing the net amounts.

    Parameters:
        df_merged (DataFrame): The merged DataFrame containing financial data.
        index_list (list): List of columns to group by in the pivot table.
        period (str): The accounting period.

    Returns:
        DataFrame: A pivot table summarizing net amounts by the specified indices.
    """

    # Create a pivot table based on the specified index columns and descriptions
    pivot_df_merged_office = df_merged.pivot_table(
        index=index_list,
        columns="description",
        values="Net amount",
        aggfunc="sum",
    )

    # Replace NaN values with 0 and calculate the net amount
    pivot_df_merged_office.fillna(0, inplace=True)
    pivot_df_merged_office["Net"] = (
        pivot_df_merged_office["OO Due to"]
        + pivot_df_merged_office["Hub Due to Premium"]
        + pivot_df_merged_office["Hub Due to Claims"]
        + pivot_df_merged_office["OO Due from"]
        + pivot_df_merged_office["Hub Due from Premium"]
        + pivot_df_merged_office["Hub Due from Claims"]
    )

    pivot_df_merged_office.reset_index(inplace=True)

    # Derive the regional code by dividing the office code by 10000 and rounding
    pivot_df_merged_office["regional_code"] = np.where(
        pivot_df_merged_office["Office Code"].between(10000, 310000),
        (pivot_df_merged_office["Office Code"] // 10000) * 10000,
        pivot_df_merged_office["Office Code"],
    )
    pivot_df_merged_office["regional_code"] = (
        pivot_df_merged_office["regional_code"].astype(int).astype(str).str.zfill(6)
    )
    pivot_df_merged_office["Office Code"] = (
        pivot_df_merged_office["Office Code"].astype(str).str.zfill(6)
    )

    # Merge the calculated regional codes with the zones data from the flag sheet
    pivot_df_merged_office = pivot_df_merged_office.merge(
        df_zones, on="regional_code", how="left"
    )

    # Add the period to the pivot table
    pivot_df_merged_office["Period"] = period

    return pivot_df_merged_office


def upload_coinsurance_balance_refactored(df):
    df.columns = df.columns.str.lower().str.replace(" ", "_")
    df = df.rename(
        columns={
            "net": "net_amount",
            "regional_code": "str_regional_office_code",
            "zone": "str_zone",
        },
    )

    db.session.execute(db.insert(CoinsuranceBalances), df.to_dict(orient="records"))
    db.session.commit()


# @coinsurance_bp.route("/coinsurance_balance/upload", methods=["POST", "GET"])
# @login_required
# @admin_required
# def upload_coinsurance_balance():
#     """Obsolete function: Replaced by upload_coinsurance_balance_refactored"""
#     if request.method == "POST":
#         file_upload_coinsurance_balance = request.files.get("file")
#         df_coinsurance_balance = pd.read_excel(
#             file_upload_coinsurance_balance,
#             sheet_name="office_wise",
#             dtype={
#                 "Office Code": str,
#                 "Company name": str,
#                 "Hub Due from Claims": float,
#                 "Hub Due from Premium": float,
#                 "Hub Due to Claims": float,
#                 "Hub Due to Premium": float,
#                 "OO Due to": float,
#                 "OO Due from": float,
#                 "Net": float,
#                 "Period": str,
#                 "regional_code": str,
#                 "zone": str,
#             },
#         )

#         df_coinsurance_balance = df_coinsurance_balance.rename(
#             columns={
#                 "Office Code": "office_code",
#                 "Company name": "company_name",
#                 "Hub Due from Claims": "hub_due_from_claims",
#                 "Hub Due from Premium": "hub_due_from_premium",
#                 "Hub Due to Claims": "hub_due_to_claims",
#                 "Hub Due to Premium": "hub_due_to_premium",
#                 "OO Due to": "oo_due_to",
#                 "OO Due from": "oo_due_from",
#                 "Net": "net_amount",
#                 "Period": "period",
#                 "regional_code": "str_regional_office_code",
#                 "zone": "str_zone",
#             },
#         )
#         df_coinsurance_balance["created_by"] = current_user.username
#         df_coinsurance_balance["created_on"] = datetime.now()
#         # engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
#         df_coinsurance_balance.to_sql(
#             "coinsurance_balances", db.engine, if_exists="append", index=False
#         )
#         flash("Coinsurance balance has been uploaded to database.")
#     return render_template("coinsurance_balance_upload.html")


# @coinsurance_bp.route("/coinsurance_balance/gl_code/upload/", methods=["POST", "GET"])
# @login_required
# @admin_required
# def gl_code_flag_sheet_upload():
#     form = UploadFileForm()
#     if form.validate_on_submit():
#         df = pd.read_excel(form.data["file_upload"])
#         df.to_sql(
#             "coinsurance_balance_general_ledger_code_flag_sheet",
#             db.engine,
#             if_exists="append",
#             index=False,
#         )
#         flash("Successfully uploaded.")
#     return render_template(
#         "coinsurance_upload_file_template.html",
#         form=form,
#         title="Upload GL code flag sheet",
#     )


# @coinsurance_bp.route("/coinsurance_balance/zones/upload/", methods=["POST", "GET"])
# @login_required
# @admin_required
# def zone_flag_sheet_upload():
#     form = UploadFileForm()
#     if form.validate_on_submit():
#         df = pd.read_excel(form.data["file_upload"], dtype={"regional_code": str})
#         df.to_sql(
#             "coinsurance_balance_zone_flag_sheet",
#             db.engine,
#             if_exists="append",
#             index=False,
#         )
#         flash("Successfully uploaded.")

#     return render_template(
#         "coinsurance_upload_file_template.html",
#         form=form,
#         title="Upload Zone flag sheet",
#     )
