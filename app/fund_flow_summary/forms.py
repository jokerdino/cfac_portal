from flask_wtf import FlaskForm, Form
from flask_wtf.file import FileRequired, FileAllowed, FileField
from wtforms import (
    IntegerField,
    DecimalField,
    FormField,
    FieldList,
    HiddenField,
    StringField,
    SelectField,
    SubmitField,
)

from wtforms.validators import Optional, DataRequired, ValidationError, InputRequired
from .models import FundInflowSummary


class InflowSummaryForm(Form):
    month = StringField(render_kw={"readonly": True, "class": "input"})
    type_of_collection = StringField(render_kw={"readonly": True, "class": "input"})
    bank_vendor_name = StringField(render_kw={"readonly": True, "class": "input"})
    mode_of_collection = StringField(render_kw={"readonly": True, "class": "input"})

    number_of_transactions = IntegerField(
        validators=[Optional()],
        render_kw={"class": "input is-small"},
    )
    amount = DecimalField(
        validators=[Optional()],
        render_kw={"class": "input is-small"},
    )
    id = HiddenField()


class InflowSummaryInputForm(FlaskForm):
    summary = FieldList(
        FormField(InflowSummaryForm, default=FundInflowSummary), min_entries=1
    )


class BankChargesInputForm(FlaskForm):
    fixed_charges = DecimalField(validators=[InputRequired()])
    variable_charges = DecimalField(validators=[InputRequired()])
    total_charges = DecimalField(validators=[InputRequired()])

    def validate_total_charges(self, field):
        fixed = self.fixed_charges.data
        variable = self.variable_charges.data
        if not field.data == fixed + variable:
            raise ValidationError(
                "Total charges should tally with sum of fixed and variable charges"
            )


class FundOutflowInputForm(FlaskForm):
    number_of_transactions = IntegerField(validators=[DataRequired()])
    amount = DecimalField(validators=[DataRequired()])


class MonthFilterForm(FlaskForm):
    month = SelectField()
    submit = SubmitField()


class BulkUploadFileForm(FlaskForm):
    file_upload = FileField(validators=[FileRequired(), FileAllowed(["xlsx"])])
