from extensions import db


class ReconEntries(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    str_period = db.Column(db.String)

    str_regional_office_code = db.Column(db.String)
    str_department = db.Column(db.String)
    str_target_ro_code = db.Column(db.String)
    txt_remarks = db.Column(db.Text)
    str_debit_credit = db.Column(db.String)
    amount_recon = db.Column(db.Numeric(20, 2))

    str_assigned_to = db.Column(db.String)
    str_head_office_status = db.Column(db.String)

    txt_head_office_remarks = db.Column(db.Text)
    str_head_office_voucher = db.Column(db.String)
    date_head_office_voucher = db.Column(db.Date)

    created_by = db.Column(db.String)
    date_created_date = db.Column(db.DateTime)

    updated_by = db.Column(db.String)
    date_updated_date = db.Column(db.DateTime)

    deleted_by = db.Column(db.String)
    date_deleted_date = db.Column(db.DateTime)


class ReconSummary(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    str_period = db.Column(db.String)
    str_regional_office_code = db.Column(db.String)

    input_ro_balance_dr_cr = db.Column(db.String)
    input_float_ro_balance = db.Column(db.Numeric(20, 2))
    input_ho_balance_dr_cr = db.Column(db.String)
    input_float_ho_balance = db.Column(db.Numeric(20, 2))

    float_ho_balance = db.Column(db.Numeric(20, 2))  # calculated value

    # meta data
    created_by = db.Column(db.String)
    date_created_date = db.Column(db.DateTime)

    updated_by = db.Column(db.String)
    date_updated_date = db.Column(db.DateTime)

    deleted_by = db.Column(db.String)
    date_deleted_date = db.Column(db.DateTime)


class ReconUpdateBalance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    str_period = db.Column(db.String)
    str_regional_office_code = db.Column(db.String)

    ro_balance = db.Column(db.Numeric(20, 2))
    ro_dr_cr = db.Column(db.String)
    ho_balance = db.Column(db.Numeric(20, 2))
    ho_dr_cr = db.Column(db.String)
