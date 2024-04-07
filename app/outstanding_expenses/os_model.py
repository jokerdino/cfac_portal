from extensions import db


class OutstandingExpenses(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    str_regional_office_code = db.Column(db.String)
    str_operating_office_code = db.Column(db.String)

    str_party_type = db.Column(db.String)
    str_party_id = db.Column(db.String)
    str_party_name = db.Column(db.String)
    float_gross_amount = db.Column(db.Numeric(15, 2))

    bool_tds_involved = db.Column(db.Boolean)
    float_tds_amount = db.Column(db.Numeric(15, 2))
    float_net_amount = db.Column(db.Numeric(15, 2))

    str_section = db.Column(db.String)
    str_pan_number = db.Column(db.String)

    str_nature_of_payment = db.Column(db.String)
    str_narration = db.Column(db.Text)

    date_date_of_creation = db.Column(db.DateTime)

    # os_jv = db.relationship(
    #     "OutstandingExpensesJournalVoucher", backref="os_exp", lazy="dynamic"
    # )


# class OutstandingExpensesJournalVoucher(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     os_exp_id = db.Column(db.Integer, db.ForeignKey("outstanding_expenses.id"))
#     #  os_entries = db.relationship("Outstanding_entries", backref="os", lazy="dynamic")
#
#     str_office_location = db.Column(db.String)
#     str_gl_code = db.Column(db.String)
#     str_sl_code = db.Column(db.String)
#     str_dr_cr = db.Column(db.String)
#
#     float_amount = db.Column(db.Numeric(15, 2))
#     txt_remarks = db.Column(db.Text)
