from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import (
    SubmitField,
    SelectField,
    RadioField,
    SelectMultipleField,
)

from wtforms.validators import DataRequired
from wtforms.widgets import CheckboxInput, ListWidget

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
        render_kw={
            "class": "file",
            "accept": ".xlsx",
        },
    )
    submit = SubmitField("Submit", render_kw={"class": "button is-success"})


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
        render_kw={
            "class": "file",
            "accept": ".xlsx",
        },
    )

    submit = SubmitField("Submit", render_kw={"class": "button is-success"})


class MultiCheckboxField(SelectMultipleField):
    """
    A multiple-select, except displays a list of checkboxes.

    Iterating the field will produce subfields, allowing custom rendering of
    the enclosed checkbox fields.
    """

    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class BudgetQueryForm(FlaskForm):
    str_financial_year = SelectField(
        "Select financial year", choices=fy_choice_list, validators=[DataRequired()]
    )
    str_ro_code = MultiCheckboxField("Select RO code")
    str_expense_head = MultiCheckboxField("Select Expense head")

    submit = SubmitField("Submit")
