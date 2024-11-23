from datetime import datetime

import numpy as np
import pandas as pd
from flask import current_app, flash, render_template, request, send_from_directory
from flask_login import current_user, login_required
from sqlalchemy import create_engine, func

from extensions import db
from set_view_permissions import admin_required

from . import coinsurance_bp
from .coinsurance_form import (
    CoinsuranceBalanceForm,
    CoinsuranceBalanceQueryForm,
    DeleteCoinsuranceBalanceEntries,
)
from .coinsurance_model import CoinsuranceBalances


def populate_period_choices(form):
    # Querying distinct list of periods from the table
    period_list_query = db.session.query(CoinsuranceBalances.period).distinct()

    # converting the period from string to datetime object
    list_period = [datetime.strptime(item[0], "%b-%y") for item in period_list_query]

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
    coinsurance_balance = CoinsuranceBalances.query.filter(
        CoinsuranceBalances.period == period
    )

    summary = (
        CoinsuranceBalances.query.with_entities(
            CoinsuranceBalances.company_name,
            func.sum(CoinsuranceBalances.hub_due_to_claims),
            func.sum(CoinsuranceBalances.hub_due_to_premium),
            func.sum(CoinsuranceBalances.oo_due_to),
            func.sum(CoinsuranceBalances.hub_due_from_claims),
            func.sum(CoinsuranceBalances.hub_due_from_premium),
            func.sum(CoinsuranceBalances.oo_due_from),
            func.sum(CoinsuranceBalances.net_amount),
        )
        .filter(CoinsuranceBalances.period == period)
        .group_by(CoinsuranceBalances.company_name)
        .order_by(CoinsuranceBalances.company_name)
    )

    if form.data["head_office_balance"] == False:
        summary = summary.filter(
            CoinsuranceBalances.office_code.not_in(("000100", "660000", "001900"))
        )
        coinsurance_balance = coinsurance_balance.filter(
            CoinsuranceBalances.office_code.not_in(("000100", "660000", "001900"))
        )

    if current_user.user_type == "ro_user":
        summary = summary.filter(
            CoinsuranceBalances.str_regional_office_code == current_user.ro_code
        )
        coinsurance_balance = coinsurance_balance.filter(
            CoinsuranceBalances.str_regional_office_code == current_user.ro_code
        )
    return render_template(
        "view_coinsurance_balance.html",
        coinsurance_balance=coinsurance_balance,
        summary=summary,
        form=form,
        period=period,
    )


@coinsurance_bp.route("/coinsurance_balance/delete/", methods=["GET", "POST"])
@login_required
@admin_required
def delete_coinsurance_balance():

    form = DeleteCoinsuranceBalanceEntries()
    _period = populate_period_choices(form)

    if form.validate_on_submit():
        period = form.period.data
        result = db.session.scalars(
            db.select(CoinsuranceBalances).filter(CoinsuranceBalances.period == period)
        )
        for item in result:
            db.session.delete(item)
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
        flag_sheet = form.flag_sheet_file.data

        list_df = [pd.read_csv(file) for file in form.csv_files_upload.data]

        # Concatenate all DataFrames into a single DataFrame
        df_concat = pd.concat(list_df, ignore_index=True)

        # Adjust credit and debit by dividing by 2 where the office code is 100
        df_concat.loc[df_concat["Office Code"] == 100, "Credit"] = (
            df_concat["Credit"] / 2
        )
        df_concat.loc[df_concat["Office Code"] == 100, "Debit"] = df_concat["Debit"] / 2

        # Calculate the net amount by subtracting debits from credits
        df_concat["Net amount"] = df_concat["Credit"] - df_concat["Debit"]

        # Remove rows where the net amount is zero
        df_concat = df_concat[df_concat["Net amount"] != 0]

        # Load additional data for GL codes and zones from an Excel file
        df_flag_sheet = pd.read_excel(flag_sheet, sheet_name="GLCodes")
        df_zones = pd.read_excel(
            flag_sheet, sheet_name="Zones", dtype={"Regional Code": str}
        )

        # Merge the concatenated data with the flag sheet on GLCode
        df_merged = df_concat.merge(df_flag_sheet, on="GLCode", how="left")

        # Generate office-wise and company-wise pivot tables
        pivot_df_merged_office = prepare_pivot(
            df_merged, df_zones, ["Office Code", "Company name"], period
        )
        pivot_df_merged = prepare_pivot(
            df_merged, df_zones, ["Company name", "Office Code"], period
        )

        net_off_jv = prepare_net_off(df_merged, ["Company name"], period, df_flag_sheet)

        # Generate a company-wise summary
        pivot_companywise = pivot_df_merged.pivot_table(
            index="Company name", values="Net", aggfunc="sum"
        )
        pivot_companywise.reset_index(inplace=True)

        # Write the pivot tables and summary to an Excel file
        with pd.ExcelWriter(
            f"coinsurance_balances/coinsurance_balance_{period}.xlsx"
        ) as writer:
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

        return send_from_directory(
            directory="coinsurance_balances/",
            path=f"coinsurance_balance_{period}.xlsx",
            download_name=f"coinsurance_balance_{period}.xlsx",
            as_attachment=True,
        )

    return render_template("generate_coinsurance_balance.html", form=form)


def prepare_net_off(df_merged, index_list, period, df_gl_codes):
    # Create a pivot table based on the specified index columns and descriptions
    df_net_off = df_merged.pivot_table(
        index=index_list,
        columns="Description",
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
    df_net_off = df_net_off[["Company name", "Due to", "Due from"]]
    df_net_off["Amount"] = df_net_off[["Due to", "Due from"]].min(axis=1)

    df_gl_codes = df_gl_codes[df_gl_codes["Description"].str.contains("OO Due")].copy()

    df_net_off_gl_merged = df_net_off.merge(df_gl_codes, on="Company name")
    df_net_off_gl_merged["Office Location"] = "000100"
    df_net_off_gl_merged["SL Code"] = 0
    df_net_off_gl_merged["Remarks"] = (
        f"Net off JV {period} " + df_net_off_gl_merged["Company name"]
    )
    df_net_off_gl_merged.loc[
        df_net_off_gl_merged["Description"] == "OO Due from", "DR/CR"
    ] = "CR"
    df_net_off_gl_merged.loc[
        df_net_off_gl_merged["Description"] == "OO Due to", "DR/CR"
    ] = "DR"
    df_net_off_gl_merged.rename(columns={"GLCode": "GL Code"}, inplace=True)

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
        columns="Description",
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
    pivot_df_merged_office["Regional Code"] = np.where(
        pivot_df_merged_office["Office Code"].between(10000, 310000),
        (pivot_df_merged_office["Office Code"] // 10000) * 10000,
        pivot_df_merged_office["Office Code"],
    )
    pivot_df_merged_office["Regional Code"] = (
        pivot_df_merged_office["Regional Code"].astype(int).astype(str).str.zfill(6)
    )
    pivot_df_merged_office["Office Code"] = (
        pivot_df_merged_office["Office Code"].astype(str).str.zfill(6)
    )

    # Merge the calculated regional codes with the zones data from the flag sheet
    pivot_df_merged_office = pivot_df_merged_office.merge(
        df_zones, on="Regional Code", how="left"
    )

    # Add the period to the pivot table
    pivot_df_merged_office["Period"] = period

    return pivot_df_merged_office


@coinsurance_bp.route("/coinsurance_balance/upload", methods=["POST", "GET"])
@login_required
@admin_required
def upload_coinsurance_balance():
    if request.method == "POST":
        file_upload_coinsurance_balance = request.files.get("file")
        df_coinsurance_balance = pd.read_excel(
            file_upload_coinsurance_balance,
            sheet_name="office_wise",
            dtype={
                "Office Code": str,
                "Company name": str,
                "Hub Due from Claims": float,
                "Hub Due from Premium": float,
                "Hub Due to Claims": float,
                "Hub Due to Premium": float,
                "OO Due to": float,
                "OO Due from": float,
                "Net": float,
                "Period": str,
                "Regional Code": str,
                "Zone": str,
            },
        )
        df_coinsurance_balance.rename(
            columns={
                "Office Code": "office_code",
                "Company name": "company_name",
                "Hub Due from Claims": "hub_due_from_claims",
                "Hub Due from Premium": "hub_due_from_premium",
                "Hub Due to Claims": "hub_due_to_claims",
                "Hub Due to Premium": "hub_due_to_premium",
                "OO Due to": "oo_due_to",
                "OO Due from": "oo_due_from",
                "Net": "net_amount",
                "Period": "period",
                "Regional Code": "str_regional_office_code",
                "Zone": "str_zone",
            },
            inplace=True,
        )
        df_coinsurance_balance["created_by"] = current_user.username
        df_coinsurance_balance["created_on"] = datetime.now()
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
        df_coinsurance_balance.to_sql(
            "coinsurance_balances", engine, if_exists="append", index=False
        )
        flash("Coinsurance balance has been uploaded to database.")
    return render_template("coinsurance_balance_upload.html")
