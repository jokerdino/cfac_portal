from datetime import datetime

# from flask import current_app
# from flask_login import current_user
# from sqlalchemy import create_engine


def upload_mis_file(df_mis_tracker, engine, username):
    #   engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
    df_mis_tracker["created_by"] = username
    df_mis_tracker["created_on"] = datetime.now()
    df_mis_tracker.to_sql("mis_tracker", engine, if_exists="append", index=False)
