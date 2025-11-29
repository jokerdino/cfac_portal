from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import (
    # FileField,
    RadioField,
    StringField,
    SelectField,
    TextAreaField,
    DateField,
    DecimalField,
    SubmitField,
    HiddenField,
)
from wtforms.validators import DataRequired, Optional, ValidationError

ro_list = [
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
]

department_list = [
    "Housing Loan",
    "Establishment",
    "Learning Centre",
    "Reinsurance",
    "TDS",
    "GST",
    "Asset",
    "HDFC - FCS",
    "HDFC Pool account / UII688",
    "Other than HDFC - FCS",
    "AXIS - PMSBY",
    "Centralised cheque",
    "NEFT",
    "Bank of America - RTGS",
    "IndusInd - RTGS",
    "Payment gateway",
    "POS",
    "BBPS",
    "Foreign remittance",
    "Coinsurance",
    "Others",
]


class ReconEntriesForm(FlaskForm):
    str_regional_office_code = HiddenField()
    str_period = SelectField("Period", choices=["Jun-24"], validators=[DataRequired()])

    str_department_inter_region = RadioField(
        "Other region / HO department",
        choices=[("RO", "Other region"), ("HO", "Head office department")],
        validators=[DataRequired()],
    )
    str_department = SelectField(
        "Department", choices=department_list, validators=[Optional()]
    )
    str_target_ro_code = SelectField("Region", choices=ro_list, validators=[Optional()])
    str_debit_credit = RadioField(
        "Debit / Credit",
        choices=[("DR", "DR / Add"), ("CR", "CR / Less")],
        validators=[DataRequired()],
    )
    amount_recon = DecimalField("Amount", validators=[DataRequired()])
    txt_remarks = TextAreaField("Remarks", validators=[Optional()])
    submit_button = SubmitField("Submit")
    delete_button = SubmitField("Delete")

    def validate_str_department_inter_region(self, field):
        if field.data == "RO" and not self.str_target_ro_code.data:
            raise ValidationError("Target RO code is required for RO selection.")

        if field.data == "HO" and not self.str_department.data:
            raise ValidationError("Department is required for HO selection.")

    def validate_str_target_ro_code(self, field):
        if self.str_regional_office_code.data == field.data:
            raise ValidationError(
                "Selected RO code cannot be same as the RO code of the user."
            )


class HeadOfficeAcceptForm(FlaskForm):
    str_assigned_to = SelectField("Assign to", validators=[Optional()])
    str_head_office_status = RadioField(
        "Head office status",
        choices=["Pending", "Accepted", "Not accepted"],
        validators=[Optional()],
    )
    text_head_office_remarks = TextAreaField(
        "Head office remarks", validators=[Optional()]
    )

    str_head_office_voucher = StringField(
        "Head office voucher number", validators=[Optional()]
    )
    date_head_office_voucher = DateField(
        "Date of voucher passed in Head office", validators=[Optional()]
    )
    submit_button = SubmitField("Submit")


class RegionalOfficeAcceptForm(FlaskForm):
    str_accept = RadioField(
        "Accepted?", choices=["Accepted", "Not accepted"], validators=[DataRequired()]
    )
    text_remarks = TextAreaField("Remarks", validators=[Optional()])
    submit_button = SubmitField("Submit")


class ReconSummaryForm(FlaskForm):
    input_ro_balance_dr_cr = SelectField(
        choices=["DR", "CR"], validators=[DataRequired()]
    )
    input_float_ro_balance = DecimalField(
        "Enter balance as per RO", validators=[DataRequired()]
    )
    input_ho_balance_dr_cr = SelectField(
        choices=["DR", "CR"], validators=[DataRequired()]
    )
    input_float_ho_balance = DecimalField(
        "Enter balance as per HO", validators=[DataRequired()]
    )

    text_remarks = TextAreaField("Remarks", validators=[Optional()])
    submit_button = SubmitField("Submit")


class UploadFileForm(FlaskForm):
    file_upload = FileField("Upload summary template", validators=[DataRequired()])
    upload_document = SubmitField("Upload")


class ReconUploadForm(FlaskForm):
    ro_csv_file = FileField(
        "Upload RO CSV file", validators=[FileRequired(), FileAllowed(["csv"])]
    )
    ho_csv_file = FileField(
        "Upload HO CSV file", validators=[FileRequired(), FileAllowed(["csv"])]
    )
    flag_file = FileField(
        "Upload Flag file", validators=[FileRequired(), FileAllowed(["xlsx"])]
    )
    upload_document = SubmitField("Submit")


class ConsolUploadForm(FlaskForm):
    consol_file = FileField(
        "Upload Consolidated file", validators=[FileRequired(), FileAllowed(["xlsx"])]
    )
    upload_document = SubmitField("Submit")
