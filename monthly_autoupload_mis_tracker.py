from datetime import date
from dateutil.relativedelta import relativedelta

import pandas as pd
from sqlalchemy import create_engine

from config import Config
from app.mis_tracker.mis_helper_functions import upload_mis_file


prev_month = date.today() - relativedelta(months=1)
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)


df_mis = pd.read_csv("/home/barneedhar/Projects/mis_monthly_template.csv")
df_mis["txt_period"] = prev_month.strftime("%B-%Y")

upload_mis_file(df_mis, engine, "AUTOUPLOAD")
