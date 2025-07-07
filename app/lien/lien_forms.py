from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    StringField,
    TextAreaField,
    IntegerField,
    SelectField,
    BooleanField,
    RadioField,
)
from wtforms.validators import Optional
from flask_wtf.file import FileField, FileAllowed, FileRequired


class LienFormCFAC(FlaskForm):
    bank_name = StringField()
    account_number = StringField()

    ro_name = StringField("RO Name")
    ro_code = StringField("RO Code")
    lien_date = DateField(validators=[Optional()])
    lien_amount = IntegerField(validators=[Optional()])
    court_order_lien_file = FileField("Upload court order - lien")

    dd_amount = IntegerField("DD Amount", validators=[Optional()])
    dd_date = DateField("DD Date", validators=[Optional()])
    court_order_dd_file = FileField("Upload DD copy")
    bank_remarks = TextAreaField(render_kw={"rows": 3})
    action_taken_by_banker = TextAreaField(render_kw={"rows": 3})

    department = SelectField(choices=["Motor", "Others"])
    court_name = StringField()

    case_number = StringField()
    case_title = StringField()
    petitioner_name = StringField()
    date_of_lien_order = DateField(validators=[Optional()])
    claim_already_paid_by_hub_office = RadioField(
        "Whether claim already paid by claims hub / office",
        choices=["Yes", "No"],
        validators=[Optional()],
    )
    claim_number = StringField()
    date_of_claim_registration = DateField(validators=[Optional()])
    claim_disbursement_voucher = StringField()

    lien_dd_reversal_order_file = FileField("Upload lien / DD reversal order")
    lien_status = SelectField(
        choices=["Lien exists", "Lien reversed", "DD issued", "DD reversed"]
    )
    appeal_given = RadioField(
        "Whether appeal is given", choices=["Yes", "No"], validators=[Optional()]
    )
    appeal_copy_file = FileField("Upload appeal copy")
    stay_obtained = RadioField(
        "Whether stay was obtained", choices=["Yes", "No"], validators=[Optional()]
    )
    stay_order_file = FileField("Upload stay order")
    claim_accounting_voucher_number = StringField()
    claim_accounting_voucher_date = DateField(validators=[Optional()])

    ro_remarks = TextAreaField("RO Remarks", render_kw={"rows": 3})
    ho_tp_remarks = TextAreaField("HO TP remarks", render_kw={"rows": 3})
    court_order_lien_reversal_file = FileField("Upload court order - lien reversal")
    court_order_dd_reversal_file = FileField("Upload DD reversal order")


class LienFormRO(FlaskForm):
    bank_name = StringField(render_kw={"disabled": True})
    account_number = StringField(render_kw={"disabled": True})

    ro_name = StringField("RO Name", render_kw={"disabled": True})
    ro_code = StringField("RO Code", render_kw={"disabled": True})
    lien_date = DateField(validators=[Optional()], render_kw={"disabled": True})
    lien_amount = IntegerField(validators=[Optional()], render_kw={"disabled": True})
    court_order_lien_file = FileField(
        "Upload court order - lien", render_kw={"disabled": True}
    )

    dd_amount = IntegerField(
        "DD Amount", validators=[Optional()], render_kw={"disabled": True}
    )
    dd_date = DateField(
        "DD Date", validators=[Optional()], render_kw={"disabled": True}
    )
    court_order_dd_file = FileField("Upload DD copy", render_kw={"disabled": True})
    bank_remarks = TextAreaField(render_kw={"rows": 3, "disabled": True})
    action_taken_by_banker = TextAreaField(render_kw={"rows": 3, "disabled": True})

    department = SelectField(choices=["Motor", "Others"])
    court_name = StringField()

    case_number = StringField()
    case_title = StringField()
    petitioner_name = StringField()
    date_of_lien_order = DateField(validators=[Optional()])
    claim_already_paid_by_hub_office = RadioField(
        "Whether claim already paid by claims hub / office", choices=["Yes", "No"]
    )
    claim_number = StringField()
    date_of_claim_registration = DateField(validators=[Optional()])
    claim_disbursement_voucher = StringField()

    lien_dd_reversal_order_file = FileField("Upload lien / DD reversal order")
    lien_status = SelectField(
        choices=["Lien exists", "Lien reversed", "DD issued", "DD reversed"]
    )
    appeal_given = RadioField("Whether appeal is given", choices=["Yes", "No"])
    appeal_copy_file = FileField("Upload appeal copy")
    stay_obtained = RadioField("Whether stay was obtained", choices=["Yes", "No"])
    stay_order_file = FileField("Upload stay order")
    claim_accounting_voucher_number = StringField()
    claim_accounting_voucher_date = DateField(validators=[Optional()])

    ro_remarks = TextAreaField("RO Remarks", render_kw={"rows": 3})
    ho_tp_remarks = TextAreaField("HO TP remarks", render_kw={"rows": 3})
    court_order_lien_reversal_file = FileField("Upload court order - lien reversal")
    court_order_dd_reversal_file = FileField("Upload DD reversal order")


class LienFormROold(FlaskForm):
    ro_code = StringField("RO Code")
    ro_name = StringField("RO Name")

    court_name = StringField()
    case_number = StringField()
    case_title = StringField()
    petitioner_name = StringField()
    date_of_order = DateField(validators=[Optional()])

    bank_remarks = TextAreaField(render_kw={"rows": 3})
    action_taken_by_banker = TextAreaField(render_kw={"rows": 3, "disabled": True})
    department = StringField()

    lien_date = DateField(render_kw={"disabled": True})
    lien_amount = IntegerField(render_kw={"disabled": True})
    dd_date = DateField("DD Date", render_kw={"disabled": True})
    dd_amount = IntegerField("DD Amount", render_kw={"disabled": True})

    lien_status = SelectField(
        choices=["Lien exists", "Lien reversed", "DD issued", "DD reversed"]
    )

    claim_number = StringField()
    date_of_claim = DateField(validators=[Optional()])
    claim_accounting_voucher_number = StringField()

    bank_name = StringField(render_kw={"disabled": True})
    account_number = StringField(render_kw={"disabled": True})

    ro_remarks = TextAreaField("RO Remarks", render_kw={"rows": 3})

    court_order_lien_file = FileField(
        "Upload court order - lien", render_kw={"disabled": True}
    )
    court_order_dd_file = FileField("Upload DD copy", render_kw={"disabled": True})
    court_order_lien_reversal_file = FileField("Upload court order - lien reversal")
    court_order_dd_reversal_file = FileField("Upload DD reversal order")


class LienUploadForm(FlaskForm):
    lien_file = FileField(
        "Upload lien file", validators=[FileRequired(), FileAllowed(["xlsx"])]
    )


class LienAddRemarks(FlaskForm):
    ro_remarks = TextAreaField("RO Remarks")
