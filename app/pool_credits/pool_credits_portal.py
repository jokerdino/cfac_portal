from datetime import datetime
import re

import pandas as pd
from flask_login import current_user


def extract_number(input_string):
    matches = re.findall(r"\d+", input_string)
    return matches[0] if matches else "0"


def prepare_dataframe_neft(df_credits_neft):
    df_credits_neft[
        ["Cr", "IFSC Code", "Name of remitter", "Recipient", "UTR number"]
    ] = df_credits_neft["description"].str.split("-", expand=True, n=4)
    return df_credits_neft


def prepare_dataframe_rtgs(df_credits_rtgs):
    df_credits_rtgs[
        ["Cr", "IFSC Code", "Name of remitter", "Recipient", "UTR number"]
    ] = df_credits_rtgs["description"].str.split("-", expand=True, n=4)
    return df_credits_rtgs


def prepare_dataframe_hdfc(df_credits_p):
    df_credits_p["Name of remitter"] = "HDFC Bank"

    df_credits_p["reference_no"] = (
        df_credits_p["description"].apply(extract_number)
        + "_"
        + df_credits_p["credit"].astype(int).astype(str)
        + "_"
        + df_credits_p["value_date"].str.replace("/", "")
    )
    return df_credits_p


def prepare_dataframe_others(df_credits_others):
    df_credits_others["Name of remitter"] = "HDFC Collections"

    df_credits_others.loc[
        df_credits_others["reference_no"].isnull(), "reference_no"
    ] = (
        df_credits_others["description"].apply(extract_number)
        + "_"
        + df_credits_others["credit"].astype(int).astype(str)
        + "_"
        + df_credits_others["value_date"].str.replace("/", "")
    )

    return df_credits_others


def prepare_dataframe(df_credits_copy):
    #    date_columns = ["book_date", "value_date"]

    df_credits = df_credits_copy.copy()

    # df_credits = df_credits[~df_credits["description"].str.contains("UII688")]
    df_credits = df_credits[df_credits["credit"].gt(0)]

    list_words = [
        #    "Opening Balance",
        #    "Trf Frm",
        #    "CMS-UII290802",
        #    "SWEEPMOD",
        #    "EOD SWEEP",
        #    "BOD SWEEP",
        "NEFT Cr-KKBK0000958-UNITED INDIA INSURANCE CO LTD-",
        "00041110000353-",
        #    "00040350000860-",
        "00041110000206-",
        #    "AUTO SWEEPOUT TO UNITED IND INSUR CO 57500001066304",
        "CHQ DEP",
        "DD Issue",
        "Closing Balance",
        "EDC R",
        #    "FD",
        #    "NEFT Cr-HSBC0110002-UNITED INDIA INSURANCE CO LTD-",
        #    "NEFT Cr-ICIC0000007-UNITED INDIA INSURANCE COMPANY LIMI-",
        #    "UNITED INDIA I-",
    ]
    df_credits = df_credits[
        ~df_credits["description"].str.startswith(tuple(list_words))
    ]
    df_credits_neft = df_credits[
        df_credits["description"].str.startswith("NEFT Cr")
    ].copy()
    df_credits_p = df_credits[df_credits["description"].str.startswith("P:")].copy()
    df_credits_rtgs = df_credits[
        df_credits["description"].str.startswith("RTGS Cr")
    ].copy()
    df_credits_others = df_credits[
        ~df_credits["description"].str.startswith(("NEFT Cr", "P:", "RTGS Cr"))
    ].copy()

    # len_df_credits = len(df_credits)
    # len_df_credits_neft = len(df_credits_neft)
    # len_df_credits_p = len(df_credits_p)
    # len_df_credits_rtgs = len(df_credits_rtgs)
    # len_df_credits_others = len(df_credits_others)

    # len_df_total = (
    #     len_df_credits_neft + len_df_credits_rtgs + len_df_credits_p + len_df_credits_others
    # )

    # print(len_df_credits)
    # print(len_df_total)

    df_credits_neft = (
        prepare_dataframe_neft(df_credits_neft)
        if not df_credits_neft.empty
        else pd.DataFrame()
    )
    df_credits_rtgs = (
        prepare_dataframe_rtgs(df_credits_rtgs)
        if not df_credits_rtgs.empty
        else pd.DataFrame()
    )
    df_credits_p = (
        prepare_dataframe_hdfc(df_credits_p)
        if not df_credits_p.empty
        else pd.DataFrame()
    )

    df_credits_others = (
        prepare_dataframe_others(df_credits_others)
        if not df_credits_others.empty
        else pd.DataFrame()
    )

    df_merged = pd.concat(
        [df_credits_neft, df_credits_rtgs, df_credits_p, df_credits_others],
        ignore_index=True,
    )
    if not df_merged.empty:
        df_merged = df_merged[
            ["reference_no", "value_date", "credit", "Name of remitter"]
        ]
        df_merged.rename(
            columns={
                "reference_no": "txt_reference_number",
                "value_date": "date_value_date",
                "credit": "amount_credit",
                "Name of remitter": "txt_name_of_remitter",
            },
            inplace=True,
        )

        df_merged["date_created_date"] = datetime.now()
        df_merged["created_by"] = current_user.username
        return df_merged
    else:
        return pd.DataFrame()
