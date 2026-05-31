from datetime import date


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


def get_fy_choice_list(start_year=2024) -> list[str]:
    today = date.today()

    current_fy_start = today.year if today.month >= 4 else today.year - 1

    return [
        f"FY{year % 100:02d}-{(year + 1) % 100:02d}"
        for year in range(start_year, current_fy_start + 1)
    ]


fy_choice_list: list[str] = get_fy_choice_list()


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
