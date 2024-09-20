from datetime import datetime


def upload_brs_file(df_brs_upload, engine, username):
    df_brs_upload["timestamp"] = datetime.now()

    df_month = df_brs_upload["month"].drop_duplicates().to_frame()
    df_month = df_month.rename(columns={"month": "txt_month"})
    df_month["bool_enable_delete"] = True
    df_month["created_by"] = username
    df_month["created_on"] = datetime.now()

    df_brs_upload.to_sql("brs", engine, if_exists="append", index=False)
    df_month.to_sql("delete_entries", engine, if_exists="append", index=False)
