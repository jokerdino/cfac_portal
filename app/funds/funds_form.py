from flask_wtf import FlaskForm

from wtforms import (
    BooleanField,
    FileField,
    StringField,
    SelectField,
    TextAreaField,
    DateField,
    DecimalField,
    SubmitField,
)
from wtforms.validators import DataRequired, Optional


class ReportsForm(FlaskForm):
    start_date = DateField("Enter start date", validators=[Optional()])
    end_date = DateField("Enter end date", validators=[Optional()])
    check_inflow = BooleanField("Include inflow", validators=[Optional()])
    check_outflow = BooleanField("Include outflow", validators=[Optional()])
    check_investments = BooleanField("Include investments", validators=[Optional()])
    check_major_payments = BooleanField(
        "Include major payments", validators=[Optional()]
    )
    check_major_receipts = BooleanField(
        "Include major receipts", validators=[Optional()]
    )


class UploadFileForm(FlaskForm):
    file_upload = FileField("Upload document", validators=[DataRequired()])
    upload_document = SubmitField("Upload")


# class GivenToInvestment(Form):
#     given_to_investment = DecimalField("Given to Investment", validators=[Optional()])
#     expected_date_of_return = DateField(
#         "Enter expected date of return", validators=[Optional()]
#     )
class OutflowForm(FlaskForm):
    # drawn_from_investment = DecimalField(
    #     "Drawn from investment", validators=[Optional()]
    # )
    # investment = FieldList(FormField(GivenToInvestment), min_entries=1)
    given_to_investment = DecimalField("Given to Investment", validators=[Optional()])
    expected_date_of_return = DateField(
        "Enter expected date of return", validators=[Optional()]
    )
    amount_citi_health = DecimalField("CITI Health", validators=[Optional()])
    amount_mro1_health = DecimalField("MRO1 Health", validators=[Optional()])

    amount_axis_neft = DecimalField("AXIS NEFT", validators=[Optional()])
    amount_citi_neft = DecimalField("CITI NEFT", validators=[Optional()])
    amount_tncmchis = DecimalField("TNCMCHIS", validators=[Optional()])
    amount_axis_centralised_cheque = DecimalField(
        "AXIS Centralised Cheque", validators=[Optional()]
    )
    amount_axis_centralised_cheque_521 = DecimalField(
        "AXIS Centralised Cheque 521", validators=[Optional()]
    )
    amount_axis_tds_gst = DecimalField("AXIS TDS GST", validators=[Optional()])
    amount_pension = DecimalField("Pension", validators=[Optional()])
    amount_gratuity = DecimalField("Gratuity", validators=[Optional()])
    amount_ro_bhopal_crop = DecimalField("RO Bhopal Crop", validators=[Optional()])
    amount_ro_nagpur_crop = DecimalField("RO Nagpur Crop", validators=[Optional()])
    amount_citi_omp = DecimalField("CITI OMP", validators=[Optional()])
    amount_hdfc_lien = DecimalField(
        "Amount held by HDFC under Lien", validators=[Optional()]
    )
    amount_other_payments = DecimalField("Other payments", validators=[Optional()])


#    amount_boa_tpa = DecimalField("BOA TPA", validators=[Optional()])


class FlagForm(FlaskForm):
    flag_description = StringField("Add flag description", validators=[DataRequired()])
    flag_regular_expression = StringField(
        "Add flag pattern", validators=[DataRequired()]
    )


class DailySummaryForm(FlaskForm):
    major_receipts = TextAreaField(
        "Enter details of major receipts", validators=[Optional()]
    )
    major_payments = TextAreaField(
        "Enter details of major payments", validators=[Optional()]
    )

    person1_name = SelectField(
        "Enter name of person 1",
        choices=["P Sudha Venkateswari", "S Vineeth", "G Suganya Priya"],
    )
    person1_designation = SelectField(
        "Enter designation of person 1", choices=["Assistant Manager", "Admin. Officer"]
    )
    person2_name = SelectField("Enter name of person 2", choices=["Gaddam Janakiram"])
    person2_designation = SelectField(
        "Enter designation of person 2", choices=["Chief Manager"]
    )
    person3_name = SelectField("Enter name of person 3", choices=["S Hemamalini"])
    person3_designation = SelectField(
        "Enter designation of person 3", choices=["DGM & CFO"]
    )
    person4_name = SelectField("Enter name of person 4", choices=["Usha Girish"])
    person4_designation = SelectField(
        "Enter designation of person 4", choices=["General Manager"]
    )


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
    current_status = SelectField(
        "Status", choices=["Pending", "Paid"], validators=[DataRequired()]
    )


class AmountGivenToInvestmentForm(FlaskForm):
    date_given_to_investment = DateField(
        "Enter date when amount was given to investment", validators=[DataRequired()]
    )
    amount_given_to_investment = DecimalField(
        "Enter amount given to investment", validators=[DataRequired()]
    )
    expected_date_of_return = DateField(
        "Enter expected date of return", validators=[DataRequired()]
    )
    remarks = TextAreaField("Enter additional remarks", validators=[Optional()])

    current_status = SelectField(
        "Status", choices=["Pending", "Received"], validators=[DataRequired()]
    )
