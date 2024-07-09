from flask_wtf import FlaskForm, Form

from wtforms import (
    BooleanField,
    FileField,
    FieldList,
    FormField,
    RadioField,
    StringField,
    SelectField,
    TextAreaField,
    DateField,
    DecimalField,
    SubmitField,
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
    "Coinsurance",
    "Housing Loan",
    "Establishment",
    "GST",
    "Asset",
    "TDS",
    "FCS",
    "Payment gateway",
    "Foreign remittance",
    "POS",
    "BBPS",
    "Others",
]


class ReconEntriesForm(FlaskForm):
    str_period = SelectField("Period", choices=["Jun-24"], validators=[DataRequired()])

    str_department_inter_region = RadioField(
        "HO department / Inter region",
        choices=[("RO", "Other region"), ("HO", "Head office department")],
        validators=[DataRequired()],
    )
    str_department = SelectField(
        "Department", choices=department_list, validators=[Optional()]
    )
    str_ro_code = SelectField("Region", choices=ro_list, validators=[Optional()])
    str_debit_credit = RadioField(
        "Debit / Credit", choices=["DR", "CR"], validators=[DataRequired()]
    )
    amount_recon = DecimalField("Amount", validators=[DataRequired()])
    text_remarks = TextAreaField("Remarks", validators=[Optional()])
    submit_button = SubmitField("Submit")
    delete_button = SubmitField("Delete")


class HeadOfficeAcceptForm(FlaskForm):

    str_assigned_to = SelectField("Assign to", validators=[Optional()])
    str_head_office_status = RadioField(
        "Head office status",
        choices=["Pending","Accepted", "Not accepted"],
        validators=[Optional()],
    )
    text_head_office_remarks = TextAreaField(
        "Head office remarks", validators=[Optional()]
    )

    str_head_office_voucher_number = StringField(
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


# class ReconEntriesForm(FlaskForm):
#     add_entries = FieldList(FormField(IndividualEntriesForm), min_entries=5) # type: ignore
#     submit_button = SubmitField("Submit")
