from datetime import datetime

from flask_login import current_user
from extensions import db


class IncomingReinsuranceConfirmations(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name_of_insured = db.Column(db.String)
    business_type = db.Column(db.String)
    lob = db.Column(db.String)
    risk_type = db.Column(db.String)
    proposal_type = db.Column(db.String)

    endorsement_number = db.Column(db.String)
    proposal_number = db.Column(db.String)
    policy_number = db.Column(db.String)
    uw_year = db.Column(db.String)
    policy_start_date = db.Column(db.Date)

    policy_end_date = db.Column(db.Date)
    uiic_share_percentage = db.Column(db.Numeric(10, 2))
    policy_premium = db.Column(db.Numeric(20, 2))
    ri_premium = db.Column(db.Numeric(20, 2))
    broker_code = db.Column(db.String)

    broker_name = db.Column(db.String)
    reinsurer_code = db.Column(db.String)
    reinsurer_name = db.Column(db.String)
    fac_share_percentage = db.Column(db.Numeric(10, 2))
    gross_fac_premium = db.Column(db.Numeric(20, 2))

    commission_percentage = db.Column(db.Numeric(10, 2))
    commission_amount = db.Column(db.Numeric(20, 2))
    net_fac_premium = db.Column(db.Numeric(20, 2))
    core_cp_generated_date = db.Column(db.Date)
    handed_to_accounts_dept_date = db.Column(db.Date)

    ppw_date = db.Column(db.Date)
    payment_period = db.Column(db.String)
    quarter = db.Column(db.String)
    cp_generated_by = db.Column(db.String)
    cp_number = db.Column(db.String)

    remarks = db.Column(db.Text)
    irda_data = db.Column(db.Text)

    file_leader_cp_documents = db.Column(db.String)
    file_uiic_cp_documents = db.Column(db.String)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)


class OutgoingReinsuranceConfirmations(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    cp_number = db.Column(db.String)
    name_of_insured = db.Column(db.String)
    business_type = db.Column(db.String)
    lob = db.Column(db.String)
    risk_type = db.Column(db.String)

    proposal_type = db.Column(db.String)
    endorsement_number = db.Column(db.String)
    proposal_number = db.Column(db.String)
    policy_number = db.Column(db.String)
    uw_year = db.Column(db.String)

    policy_start_date = db.Column(db.Date)
    policy_end_date = db.Column(db.Date)
    uiic_share_percentage = db.Column(db.Numeric(10, 2))
    policy_premium = db.Column(db.Numeric(20, 2))
    ri_premium = db.Column(db.Numeric(20, 2))

    broker_code = db.Column(db.String)
    broker_name = db.Column(db.String)
    reinsurer_code = db.Column(db.String)
    reinsurer_name = db.Column(db.String)
    fac_share_percentage = db.Column(db.Numeric(10, 2))

    gross_fac_premium = db.Column(db.Numeric(20, 2))
    commission_percentage = db.Column(db.Numeric(10, 2))
    commission_amount = db.Column(db.Numeric(20, 2))
    net_fac_premium = db.Column(db.Numeric(20, 2))
    core_cp_generated_date = db.Column(db.Date)

    handed_to_accounts_dept_date = db.Column(db.Date)
    ppw_date = db.Column(db.Date)
    payment_period = db.Column(db.String)
    quarter = db.Column(db.String)
    cp_generated_by = db.Column(db.String)

    remarks = db.Column(db.Text)
    irda_data = db.Column(db.Text)

    file_leader_cp_documents = db.Column(db.String)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)
