from datetime import date
from dateutil.relativedelta import relativedelta

import pandas as pd
from sqlalchemy import create_engine

from config import Config
from app.brs.brs_helper_functions import upload_brs_file


prev_month = date.today() - relativedelta(months=1)
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)


def get_financial_year(date):
    if date.strftime("%m") in ["01", "02", "03"]:
        prev_year = date - relativedelta(years=1)
        return f"{prev_year.strftime('%y')}-{date.strftime('%y')}"
    else:
        next_year = date - relativedelta(years=-1)
        return f"{date.strftime('%y')}-{next_year.strftime('%y')}"


df_mis = pd.read_csv(
    "/home/barneedhar/Projects/brs_monthly_template.csv",
    dtype={"uiic_regional_code": str, "uiic_office_code": str},
)
df_mis["month"] = prev_month.strftime("%B-%Y")
df_mis["financial_year"] = get_financial_year(prev_month)
upload_brs_file(df_mis, engine, "AUTOUPLOAD")
