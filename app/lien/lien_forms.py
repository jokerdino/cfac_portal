from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    StringField,
    TextAreaField,
    IntegerField,
    SelectField,
    RadioField,
)
from wtforms.validators import Optional, ValidationError
from flask_wtf.file import FileField, FileAllowed, FileRequired


ALLOWED_RO_CODES = {
    "010000",
    "020000",
    "030000",
    "040000",
    "050000",
    "060000",
    "070000",
    "080000",
    "090000",
    "100000",
    "110000",
    "120000",
    "130000",
    "140000",
    "150000",
    "160000",
    "170000",
    "180000",
    "190000",
    "200000",
    "210000",
    "220000",
    "230000",
    "240000",
    "250000",
    "260000",
    "270000",
    "280000",
    "290000",
    "300000",
    "500100",
    "500200",
    "500300",
    "500400",
    "500500",
    "500700",
}

ro_choices = sorted(ALLOWED_RO_CODES)


class LienFormCFAC(FlaskForm):
    bank_name = StringField()
    account_number = StringField()

    ro_name = StringField("RO Name")
    ro_code = SelectField("RO Code", choices=ro_choices)
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
    claim_disbursement_voucher_file = FileField(
        "Upload claim disbursement voucher", render_kw={"disabled": True}
    )

    lien_dd_reversal_order_file = FileField(
        "Upload lien / DD reversal order", render_kw={"disabled": True}
    )
    lien_status = SelectField(
        choices=["Lien exists", "Lien reversed", "DD issued", "DD reversed"]
    )
    appeal_given = RadioField(
        "Whether appeal is given", choices=["Yes", "No"], validators=[Optional()]
    )
    appeal_copy_file = FileField("Upload appeal copy", render_kw={"disabled": True})
    stay_obtained = RadioField(
        "Whether stay was obtained",
        choices=["Yes", "No"],
        validators=[Optional()],
    )
    stay_order_file = FileField("Upload stay order", render_kw={"disabled": True})
    claim_accounting_voucher_number = StringField()
    claim_accounting_voucher_date = DateField(validators=[Optional()])

    ro_remarks = TextAreaField("RO Remarks", render_kw={"rows": 3})
    ho_tp_remarks = TextAreaField("HO TP remarks", render_kw={"rows": 3})
    court_order_lien_reversal_file = FileField("Upload court order - lien reversal")
    court_order_dd_reversal_file = FileField("Upload DD reversal order")

    def validate_claim_already_paid_by_hub_office(form, field):
        if field.data == "Yes":
            if not form.claim_disbursement_voucher_file.data:
                raise ValidationError("Please upload claim disbursement voucher.")

    def validate_claim_disbursement_voucher_file(form, field):
        if field.data:
            if not form.lien_dd_reversal_order_file.data:
                raise ValidationError("Please upload lien / DD reversal order.")

    def validate_appeal_given(form, field):
        if field.data == "Yes":
            if not form.appeal_copy_file.data:
                raise ValidationError("Please upload appeal copy.")

    def validate_stay_obtained(form, field):
        if field.data == "Yes":
            if not form.stay_order_file.data:
                raise ValidationError("Please upload stay order copy.")


class LienFormHOTP(FlaskForm):
    bank_name = StringField(render_kw={"disabled": True})
    account_number = StringField(render_kw={"disabled": True})

    ro_name = StringField("RO Name")
    ro_code = SelectField("RO Code", choices=ro_choices)
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
        "Whether claim already paid by claims hub / office",
        choices=["Yes", "No"],
    )
    claim_number = StringField()
    date_of_claim_registration = DateField(validators=[Optional()])
    claim_disbursement_voucher_file = FileField(
        "Upload claim disbursement voucher", render_kw={"disabled": True}
    )

    lien_dd_reversal_order_file = FileField(
        "Upload lien / DD reversal order", render_kw={"disabled": True}
    )
    lien_status = SelectField(
        choices=["Lien exists", "Lien reversed", "DD issued", "DD reversed"]
    )
    appeal_given = RadioField(
        "Whether appeal is given",
        choices=["Yes", "No"],
    )
    appeal_copy_file = FileField("Upload appeal copy", render_kw={"disabled": True})
    stay_obtained = RadioField(
        "Whether stay was obtained",
        choices=["Yes", "No"],
    )
    stay_order_file = FileField("Upload stay order", render_kw={"disabled": True})
    claim_accounting_voucher_number = StringField()
    claim_accounting_voucher_date = DateField(validators=[Optional()])

    ro_remarks = TextAreaField("RO Remarks", render_kw={"rows": 3})
    ho_tp_remarks = TextAreaField("HO TP remarks", render_kw={"rows": 3})
    court_order_lien_reversal_file = FileField("Upload court order - lien reversal")
    court_order_dd_reversal_file = FileField("Upload DD reversal order")

    def validate_claim_already_paid_by_hub_office(form, field):
        if field.data == "Yes":
            if not form.claim_disbursement_voucher_file.data:
                raise ValidationError("Please upload claim disbursement voucher.")

    def validate_claim_disbursement_voucher_file(form, field):
        if field.data:
            if not form.lien_dd_reversal_order_file.data:
                raise ValidationError("Please upload lien / DD reversal order.")

    def validate_appeal_given(form, field):
        if field.data == "Yes":
            if not form.appeal_copy_file.data:
                raise ValidationError("Please upload appeal copy.")

    def validate_stay_obtained(form, field):
        if field.data == "Yes":
            if not form.stay_order_file.data:
                raise ValidationError("Please upload stay order copy.")


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
        "Whether claim already paid by claims hub / office",
        choices=["Yes", "No"],
    )
    claim_number = StringField()
    date_of_claim_registration = DateField(validators=[Optional()])
    claim_disbursement_voucher_file = FileField(
        "Upload claim disbursement voucher", render_kw={"disabled": True}
    )

    lien_dd_reversal_order_file = FileField(
        "Upload lien / DD reversal order", render_kw={"disabled": True}
    )
    lien_status = SelectField(
        choices=["Lien exists", "Lien reversed", "DD issued", "DD reversed"]
    )
    appeal_given = RadioField(
        "Whether appeal is given",
        choices=["Yes", "No"],
    )
    appeal_copy_file = FileField("Upload appeal copy", render_kw={"disabled": True})
    stay_obtained = RadioField(
        "Whether stay was obtained",
        choices=["Yes", "No"],
    )
    stay_order_file = FileField("Upload stay order", render_kw={"disabled": True})
    claim_accounting_voucher_number = StringField()
    claim_accounting_voucher_date = DateField(validators=[Optional()])

    ro_remarks = TextAreaField("RO Remarks", render_kw={"rows": 3})
    ho_tp_remarks = TextAreaField("HO TP remarks", render_kw={"rows": 3})
    court_order_lien_reversal_file = FileField("Upload court order - lien reversal")
    court_order_dd_reversal_file = FileField("Upload DD reversal order")

    def validate_claim_already_paid_by_hub_office(form, field):
        if field.data == "Yes":
            if not form.claim_disbursement_voucher_file.data:
                raise ValidationError("Please upload claim disbursement voucher.")

    def validate_claim_disbursement_voucher_file(form, field):
        if field.data:
            if not form.lien_dd_reversal_order_file.data:
                raise ValidationError("Please upload lien / DD reversal order.")

    def validate_appeal_given(form, field):
        if field.data == "Yes":
            if not form.appeal_copy_file.data:
                raise ValidationError("Please upload appeal copy.")

    def validate_stay_obtained(form, field):
        if field.data == "Yes":
            if not form.stay_order_file.data:
                raise ValidationError("Please upload stay order copy.")


class LienUploadForm(FlaskForm):
    lien_file = FileField(
        "Upload lien file", validators=[FileRequired(), FileAllowed(["xlsx"])]
    )


# class LienAddRemarks(FlaskForm):
#     ro_remarks = TextAreaField("RO Remarks")
