from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import SubmitField, SelectField, RadioField, SelectMultipleField

from wtforms.validators import DataRequired, Optional

fy_choice_list = ["FY24-25", "FY25-26"]


class BudgetAllocationForm(FlaskForm):
    str_financial_year = SelectField(
        "Select financial year", choices=fy_choice_list, validators=[DataRequired()]
    )
    str_type = RadioField(
        "Select type", choices=["Original", "Revised"], validators=[DataRequired()]
    )
    str_budget_allocation = FileField(
        "Upload budget allocation file (excel)",
        validators=[FileRequired(), FileAllowed(["xlsx"])],
    )
    submit = SubmitField("Submit")


class BudgetUtilizationForm(FlaskForm):
    str_financial_year = SelectField(
        "Select financial year", choices=fy_choice_list, validators=[DataRequired()]
    )
    str_quarter = SelectField(
        "Select quarter", choices=["I", "II", "III", "IV"], validators=[DataRequired()]
    )
    str_budget_utilization = FileField(
        "Upload budget utilization file (excel)",
        validators=[FileRequired(), FileAllowed(["xlsx"])],
    )
    submit = SubmitField("Submit")


class BudgetQueryForm(FlaskForm):
    str_financial_year = SelectField(
        "Select financial year", choices=fy_choice_list, validators=[DataRequired()]
    )
    str_ro_code = SelectMultipleField("Select RO code")
    str_expense_head = SelectMultipleField("Select Expense head")
    # str_type = RadioField(
    #     "Select original or revised",
    #     choices=["Original", "Revised"],
    #     validators=[DataRequired()],
    # )
    submit = SubmitField("Submit")
