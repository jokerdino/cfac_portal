from extensions import db


class HeadOfficeAccountsTracker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    str_work = db.Column(db.String)
    str_period = db.Column(db.String)
    str_person = db.Column(db.String)
    # user inputs
    bool_current_status = db.Column(db.Boolean)
    text_remarks = db.Column(db.Text)

    # meta data
    date_created_date = db.Column(db.DateTime)
    date_updated_date = db.Column(db.DateTime)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String)
    updated_by = db.Column(db.String)
    deleted_by = db.Column(db.String)


class HeadOfficeBankReconTracker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    str_period = db.Column(db.String)

    str_name_of_bank = db.Column(db.String)
    str_bank_address = db.Column(db.String)

    str_purpose = db.Column(db.String)
    str_person = db.Column(db.String)

    str_gl_code = db.Column(db.String)
    str_sl_code = db.Column(db.String)

    str_bank_account_number = db.Column(db.String)
    str_customer_id = db.Column(db.String)

    # user inputs
    boolean_mis_shared = db.Column(db.Boolean)
    str_brs_file_upload = db.Column(db.String)
    boolean_jv_passed = db.Column(db.Boolean)
    str_bank_confirmation_file_upload = db.Column(db.String)
    text_remarks = db.Column(db.Text)

    # meta data
    date_created_date = db.Column(db.DateTime)
    date_updated_date = db.Column(db.DateTime)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String)
    updated_by = db.Column(db.String)
    deleted_by = db.Column(db.String)
