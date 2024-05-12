from flask_wtf import FlaskForm

from wtforms import (
    FileField,
    StringField,
    SelectField,
    IntegerField,
    TextAreaField,
    DateField,
    DecimalField,
    SubmitField,
)
from wtforms.validators import DataRequired, Optional, NumberRange

class UploadFileForm(FlaskForm):
    file_upload = FileField("Upload document", validators=[DataRequired()])
    upload_document = SubmitField("Upload")

class OutflowForm(FlaskForm):
    drawn_from_investment = DecimalField("Drawn from investment", validators=[Optional()])
    given_to_investment = DecimalField("Given to Investment", validators=[Optional()])

    amount_citi_health = DecimalField("CITI Health", validators=[Optional()])
    amount_mro1_health = DecimalField("MRO1 Health", validators=[Optional()])

    amount_axis_neft = DecimalField("AXIS NEFT", validators=[Optional()])
    amount_citi_neft = DecimalField("CITI NEFT", validators=[Optional()])
    amount_tncmchis = DecimalField("TNCMCHIS", validators=[Optional()])
    amount_axis_centralised_cheque = DecimalField("AXIS Centralised Cheque", validators=[Optional()])
    amount_axis_centralised_cheque_521 = DecimalField("AXIS Centralised Cheque 521", validators=[Optional()])
    amount_axis_tds_gst = DecimalField("AXIS TDS GST", validators=[Optional()])
    amount_pension = DecimalField("Pension", validators=[Optional()])
    amount_gratuity = DecimalField("Gratuity", validators=[Optional()])
    amount_ro_bhopal_crop = DecimalField("RO Bhopal Crop", validators=[Optional()])
    amount_ro_nagpur_crop = DecimalField("RO Nagpur Crop", validators=[Optional()])
    amount_citi_omp = DecimalField("CITI OMP", validators=[Optional()])
    amount_hdfc_lien = DecimalField("Amount held by HDFC under Lien", validators=[Optional()])
    amount_other_payments = DecimalField("Other payments", validators=[Optional()])
    amount_boa_tpa = DecimalField("BOA TPA", validators=[Optional()])


class FlagForm(FlaskForm):
    flag_description = StringField("Add flag description", validators=[DataRequired()])
    flag_regular_expression = StringField("Add flag pattern", validators=[DataRequired()])


class DailySummaryForm(FlaskForm):
    major_receipts = TextAreaField(
        "Enter details of major receipts", validators=[Optional()]
    )
    major_payments = TextAreaField(
        "Enter details of major payments", validators=[Optional()]
    )


class DailySummaryForm2(FlaskForm):

    current_date = DateField("Enter date", validators=[DataRequired()])
    total_receipts = DecimalField(
        "Enter total amount receipted", validators=[DataRequired()]
    )
    total_payments = DecimalField(
        "Enter total amount paid", validators=[DataRequired()]
    )

    major_receipts = TextAreaField(
        "Enter details of major receipts", validators=[Optional()]
    )
    major_payments = TextAreaField(
        "Enter details of major payments", validators=[Optional()]
    )

    amount_given_to_investments = DecimalField(
        "Amount given to investments", validators=[Optional()]
    )
    amount_received_from_investments = DecimalField(
        "Amount received from investments", validators=[Optional()]
    )

    remarks = TextAreaField("Enter additional remarks", validators=[Optional()])
    submit_daily_summary = SubmitField("Submit")

class MajorOutgoForm(FlaskForm):
    date_of_outgo = DateField(
        "Enter expected date of outgo", validators=[DataRequired()]
    )
    amount_expected_outgo = DecimalField(
        "Enter estimated amount of outgo", validators=[DataRequired()]
    )
    department = TextAreaField(
        "Enter details of department/ Region", validators=[DataRequired()]
    )
    remarks = TextAreaField("Enter remarks", validators=[Optional()])
    current_status = SelectField("Status", choices=["Pending", "Paid"], validators=[DataRequired()])



class AmountGivenToInvestmentForm(FlaskForm):
    date_given_to_investment = DateField(
        "Enter date when amount was given to investment", validators=[DataRequired()]
    )
    amount_given_to_investment = DecimalField(
        "Enter amount given to investment", validators=[DataRequired()]
    )
    expected_date_amount_return = DateField(
        "Enter expected date of return", validators=[DataRequired()]
    )
    remarks = TextAreaField("Enter additional remarks", validators=[Optional()])

    current_status = SelectField("Status", choices=["Pending", "Received"], validators=[DataRequired()])
