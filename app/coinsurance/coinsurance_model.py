from extensions import db


class Coinsurance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uiic_regional_code = db.Column(db.String)
    uiic_office_code = db.Column(db.String)
    follower_company_name = db.Column(db.String)
    follower_office_code = db.Column(db.String)

    str_period = db.Column(db.String)
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

    utr_number = db.Column(db.String)

    def get_zone(self):
        self.ro_code = self.uiic_regional_code

        if self.ro_code in [
            "020000",
            "060000",
            "120000",
            "160000",
            "180000",
            "190000",
            "230000",
            "270000",
            "500100",
            "020051",
        ]:
            return "West"
        elif self.ro_code in [
            "010000",
            "050000",
            "070000",
            "090000",
            "100000",
            "150000",
            "170000",
            "240000",
            "280000",
            "300000",
            "500200",
            "500400",
            "500500",
            "050051",
        ]:
            return "South"
        elif self.ro_code in [
            "040000",
            "080000",
            "110000",
            "140000",
            "200000",
            "220000",
            "250000",
            "290000",
            "500300",
            "040051",
        ]:
            return "North"
        elif self.ro_code in [
            "030000",
            "130000",
            "210000",
            "260000",
            "500700",
            "030051",
        ]:
            return "East"
        else:
            return "NA"


class Settlement(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name_of_company = db.Column(db.String)
    date_of_settlement = db.Column(db.Date)
    settled_amount = db.Column(db.Integer)
    utr_number = db.Column(db.String)
    file_settlement_file = db.Column(db.String)
    type_of_transaction = db.Column(db.String)
    notes = db.Column(db.Text)

    created_by = db.Column(db.String)
    created_on = db.Column(db.DateTime)

    updated_by = db.Column(db.String)
    updated_on = db.Column(db.DateTime)

    deleted_by = db.Column(db.String)
    deleted_on = db.Column(db.DateTime)


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

    str_period = db.Column(db.String)
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


class CoinsuranceBalances(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    str_zone = db.Column(db.String)
    str_regional_office_code = db.Column(db.String)

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

    created_by = db.Column(db.String)
    created_on = db.Column(db.DateTime)

    updated_by = db.Column(db.String)
    updated_on = db.Column(db.DateTime)

    deleted_by = db.Column(db.String)
    deleted_on = db.Column(db.DateTime)


class CoinsuranceCashCall(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    txt_hub = db.Column(db.String)
    txt_ro_code = db.Column(db.String)
    txt_oo_code = db.Column(db.String)

    str_leader_follower = db.Column(db.String)
    txt_insured_name = db.Column(db.String)
    date_policy_start_date = db.Column(db.Date)
    date_policy_end_date = db.Column(db.Date)

    amount_total_paid = db.Column(db.Numeric(15, 2))
    txt_remarks = db.Column(db.Text)
    date_claim_payment = db.Column(db.Date)

    txt_coinsurer_name = db.Column(db.String)
    percent_share = db.Column(db.Numeric(5, 2))
    amount_of_share = db.Column(db.Numeric(15, 2))
    txt_request_id = db.Column(db.String)

    date_of_cash_call_raised = db.Column(db.Date)
    txt_current_status = db.Column(db.String)

    txt_utr_number = db.Column(db.String)
    date_of_cash_call_settlement = db.Column(db.Date)
    amount_settlement = db.Column(db.Numeric(15, 2))

    created_by = db.Column(db.String)
    created_on = db.Column(db.DateTime)

    updated_by = db.Column(db.String)
    updated_on = db.Column(db.DateTime)

    deleted_by = db.Column(db.String)
    deleted_on = db.Column(db.DateTime)
