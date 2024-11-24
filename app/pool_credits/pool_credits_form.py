from flask_wtf import FlaskForm
from wtforms import SelectField, TextAreaField
from wtforms.validators import DataRequired, Optional

regional_office_list = [
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
    "Reinsurance",
    "Housing Loan",
    "Establishment",
]


class UpdatePoolCreditsForm(FlaskForm):
    str_regional_office_code = SelectField(
        "Enter RO Code", choices=regional_office_list, validators=[DataRequired()]
    )
    text_remarks = TextAreaField("Enter remarks", validators=[Optional()])


class FilterMonthForm(FlaskForm):
    month = SelectField(validators=[DataRequired()])
