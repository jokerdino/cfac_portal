from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    StringField,
    TextAreaField,
    IntegerField,
    SelectField,
    RadioField,
    SubmitField,
)
from wtforms.validators import Optional, ValidationError, DataRequired, InputRequired
from flask_wtf.file import FileField, FileAllowed, FileRequired, FileSize


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
MAX_UPLOAD_SIZE = 10 * 1024 * 1024


class BaseLienForm(FlaskForm):
    bank_name = StringField(filters=[lambda x: x.strip().upper() if x else None])
    account_number = StringField(filters=[lambda x: x.strip() if x else None])

    ro_name = StringField("RO Name", validators=[InputRequired()])
    ro_code = SelectField("RO Code", choices=ro_choices)
    lien_date = DateField(validators=[Optional()])
    lien_amount = IntegerField(validators=[DataRequired()])
    court_order_lien_file = FileField(
        "Upload court order - lien",
        validators=[
            FileSize(
                MAX_UPLOAD_SIZE,
                message=f"File size must be less than {MAX_UPLOAD_SIZE // (1024 * 1024)}MB.",
            )
        ],
    )

    dd_amount = IntegerField("DD Amount", validators=[Optional()])
    dd_date = DateField("DD Date", validators=[Optional()])
    court_order_dd_file = FileField("Upload court order for DD")
    bank_remarks = TextAreaField(render_kw={"rows": 2})
    action_taken_by_banker = TextAreaField(render_kw={"rows": 2})

    department = SelectField(choices=["Motor", "Others"])
    court_name = StringField()

    case_number = StringField()
    case_title = StringField()
    mact_number = StringField("MACT Number")
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
        choices=["Lien exists", "Lien reversed", "DD issued", "DD reversed"],
        render_kw={"disabled": True},
    )
    appeal_given = RadioField(
        "Whether appeal is given", choices=["Yes", "No"], validators=[Optional()]
    )
    appeal_copy_file = FileField("Upload appeal copy", render_kw={"disabled": True})
    appeal_given_2 = RadioField(
        "Whether further appeal is given",
        choices=["Yes", "No"],
        validators=[Optional()],
    )
    appeal_copy_2_file = FileField(
        "Upload further appeal copy", render_kw={"disabled": True}
    )
    stay_obtained = RadioField(
        "Whether stay was obtained",
        choices=["Yes", "No"],
        validators=[Optional()],
    )
    stay_order_file = FileField("Upload stay order", render_kw={"disabled": True})
    claim_accounting_voucher_number = StringField()
    claim_accounting_voucher_date = DateField(validators=[Optional()])

    ro_remarks = TextAreaField("RO Motor TP Remarks", render_kw={"rows": 2})
    ho_tp_remarks = TextAreaField("HO Motor TP remarks", render_kw={"rows": 2})
    court_order_lien_reversal_file = FileField("Upload court order - lien reversal")
    court_order_dd_reversal_file = FileField("Upload court order - DD reversal")
    _order = [
        "bank_name",
        "account_number",
        "ro_code",
        "ro_name",
        "lien_date",
        "lien_amount",
        "court_order_lien_file",
        "dd_amount",
        "dd_date",
        "court_order_dd_file",
        "bank_remarks",
        "action_taken_by_banker",
        "department",
        "court_name",
        "case_number",
        "case_title",
        "mact_number",
        "petitioner_name",
        "date_of_lien_order",
        "claim_already_paid_by_hub_office",
        "claim_number",
        "date_of_claim_registration",
        "claim_accounting_voucher_number",
        "claim_accounting_voucher_date",
        "claim_disbursement_voucher_file",
        "lien_dd_reversal_order_file",
        "lien_status",
        "appeal_given",
        "appeal_copy_file",
        "appeal_given_2",
        "appeal_copy_2_file",
        "stay_obtained",
        "stay_order_file",
        "ro_remarks",
        "ho_tp_remarks",
        "court_order_lien_reversal_file",
        "court_order_dd_reversal_file",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fields = {
            name: self._fields[name] for name in self._order if name in self._fields
        }

    def validate_claim_already_paid_by_hub_office(form, field):
        if field.data == "Yes":
            if not (
                form.claim_disbursement_voucher_file.data
                or (form.model_obj and form.model_obj.claim_disbursement_voucher)
            ):
                raise ValidationError("Please upload claim disbursement voucher.")

    # def validate_claim_disbursement_voucher_file(form, field):
    #     if field.data:
    #         if not (
    #             form.lien_dd_reversal_order_file.data
    #             or (form.model_obj and form.model_obj.lien_dd_reversal_order)
    #         ):
    #             raise ValidationError("Please upload lien / DD reversal order.")

    def validate_appeal_given(form, field):
        if field.data == "Yes":
            if not (
                form.appeal_copy_file.data
                or (form.model_obj and form.model_obj.appeal_copy)
            ):
                raise ValidationError("Please upload appeal copy.")

    def validate_appeal_given_2(form, field):
        if field.data == "Yes":
            if not (
                form.appeal_copy_2_file.data
                or (form.model_obj and form.model_obj.appeal_copy_2)
            ):
                raise ValidationError("Please upload further appeal copy.")

    def validate_stay_obtained(form, field):
        if field.data == "Yes":
            if not (
                form.stay_order_file.data
                or (form.model_obj and form.model_obj.stay_order)
            ):
                raise ValidationError("Please upload stay order copy.")


class LienFormCFAC(BaseLienForm):
    lien_status = SelectField(
        choices=["Lien exists", "Lien reversed", "DD issued", "DD reversed"],
        render_kw={"disabled": False},
    )


class LienFormHOTP(BaseLienForm):
    bank_name = StringField(render_kw={"disabled": True})
    account_number = StringField(render_kw={"disabled": True})

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


class LienFormRO(LienFormHOTP):
    ro_name = StringField("RO Name", render_kw={"disabled": True})
    ro_code = StringField("RO Code", render_kw={"disabled": True})


class LienUploadForm(FlaskForm):
    lien_file = FileField(
        "Upload lien file", validators=[FileRequired(), FileAllowed(["xlsx"])]
    )


class LienStatusFilterForm(FlaskForm):
    lien_status = SelectField()
    filter = SubmitField("Filter")
