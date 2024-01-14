# import uuid
# from sqlalchemy.dialects.postgresql import UUID

from extensions import db


class Coinsurance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uiic_regional_code = db.Column(db.String)
    uiic_office_code = db.Column(db.String)
    follower_company_name = db.Column(db.String)
    follower_office_code = db.Column(db.String)

    type_of_transaction = db.Column(db.String)
    request_id = db.Column(db.String)
    payable_amount = db.Column(db.Integer)
    receivable_amount = db.Column(db.Integer)
    insured_name = db.Column(db.String)

    boolean_reinsurance_involved = db.Column(db.Boolean)
    int_ri_payable_amount = db.Column(db.Integer)
    int_ri_receivable_amount = db.Column(db.Integer)

    net_amount = db.Column(db.Integer)

    statement = db.Column(db.String)
    confirmation = db.Column(db.String)
    ri_confirmation = db.Column(db.String)

    current_status = db.Column(db.String)

    # settlement_uuid = db.Column(UUID(as_uuid=True), default=uuid.uuid4)
    # settlement_id = db.Column(db.Integer, db.ForeignKey("settlement.id"))
    utr_number = db.Column(db.String)


class Settlement(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name_of_company = db.Column(db.String)
    date_of_settlement = db.Column(db.Date)
    settled_amount = db.Column(db.Integer)
    utr_number = db.Column(db.String)
    file_settlement_file = db.Column(db.String)
    type_of_transaction = db.Column(db.String)


#    coinsurance_entries = db.relationship(
#       "coinsurance_entries", backref="settlement", lazy="dynamic"
#  )
# settlement_uuid = db.Column(UUID(as_uuid=True), default=uuid.uuid4)


class Remarks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coinsurance_id = db.Column(db.Integer)

    user = db.Column(db.String)
    remarks = db.Column(db.Text)
    time_of_remark = db.Column(db.DateTime)


class Coinsurance_log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coinsurance_id = db.Column(db.Integer)
    user = db.Column(db.String)
    time_of_update = db.Column(db.DateTime)

    uiic_regional_code = db.Column(db.String)
    uiic_office_code = db.Column(db.String)
    follower_company_name = db.Column(db.String)
    follower_office_code = db.Column(db.String)

    type_of_transaction = db.Column(db.String)
    request_id = db.Column(db.String)
    payable_amount = db.Column(db.Integer)
    receivable_amount = db.Column(db.Integer)

    boolean_reinsurance_involved = db.Column(db.Boolean)
    int_ri_payable_amount = db.Column(db.Integer)
    int_ri_receivable_amount = db.Column(db.Integer)

    net_amount = db.Column(db.Integer)

    statement = db.Column(db.String)
    confirmation = db.Column(db.String)
    ri_confirmation = db.Column(db.String)

    current_status = db.Column(db.String)
    utr_number = db.Column(db.String)


#    settlement_uuid = db.Column(UUID(as_uuid=True), default=uuid.uuid4)


class CoinsuranceBalances(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    office_code = db.Column(db.String)
    company_name = db.Column(db.String)
    period = db.Column(db.String)
    hub_due_to_claims = db.Column(db.Float)
    hub_due_to_premium = db.Column(db.Float)
    hub_due_from_claims = db.Column(db.Float)
    hub_due_from_premium = db.Column(db.Float)
    oo_due_to = db.Column(db.Float)
    oo_due_from = db.Column(db.Float)
    net_amount = db.Column(db.Float)
