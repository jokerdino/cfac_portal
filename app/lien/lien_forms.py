from flask_wtf import FlaskForm
from wtforms import DateField, StringField, TextAreaField, IntegerField, SelectField
from wtforms.validators import Optional
from flask_wtf.file import FileField, FileAllowed, FileRequired


class LienFormCFAC(FlaskForm):
    ro_code = StringField("RO Code")
    ro_name = StringField("RO Name")

    court_name = StringField()
    case_number = StringField()
    case_title = StringField()
    petitioner_name = StringField()
    date_of_order = DateField(validators=[Optional()])

    bank_remarks = TextAreaField(render_kw={"rows": 3})
    action_taken_by_banker = TextAreaField(render_kw={"rows": 3})
    department = StringField()

    lien_date = DateField(validators=[Optional()])
    lien_amount = IntegerField(validators=[Optional()])
    dd_date = DateField("DD Date", validators=[Optional()])
    dd_amount = IntegerField("DD Amount", validators=[Optional()])

    lien_status = SelectField(
        choices=["Lien exists", "Lien reversed", "DD issued", "DD reversed"]
    )
    claim_number = StringField()
    date_of_claim = DateField(validators=[Optional()])
    claim_accounting_voucher_number = StringField()

    bank_name = StringField()
    account_number = StringField()

    ro_remarks = TextAreaField("RO Remarks", render_kw={"rows": 3})

    court_order_lien_file = FileField("Upload court order - lien")
    court_order_dd_file = FileField("Upload DD copy")
    court_order_lien_reversal_file = FileField("Upload court order - lien reversal")
    court_order_dd_reversal_file = FileField("Upload DD reversal order")


class LienFormRO(FlaskForm):
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
