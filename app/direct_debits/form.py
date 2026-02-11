from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    TextAreaField,
    StringField,
    SelectField,
    SubmitField,
    DecimalField,
)
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms.validators import Optional

from .model import Status


class HeadOfficeForm(FlaskForm):
    ro_name = StringField("RO Name")
    ro_code = StringField("RO Code")
    transaction_date = DateField()
    particulars = StringField()
    debit = DecimalField()
    status = SelectField(coerce=Status)
    dd_reversal_date = DateField("DD reversal date", validators=[Optional()])
    ho_iot_jv_number = StringField("HO IOT JV number", validators=[Optional()])
    ho_iot_jv_date = DateField("HO IOT JV date", validators=[Optional()])


class RegionalOfficeForm(FlaskForm):
    ro_jv_number = StringField("Enter JV number", validators=[Optional()])
    ro_jv_date = DateField("Enter JV date", validators=[Optional()])
    remarks = TextAreaField("Enter remarks", validators=[Optional()])


class BulkDirectDebitForm(FlaskForm):
    file_upload = FileField(
        validators=[FileRequired(), FileAllowed(["xlsx"])],
        render_kw=({"class": "file", "accept": ".xlsx"}),
    )


class JournalVoucherUpdateForm(FlaskForm):
    ho_iot_jv_number = StringField("HO IOT JV number")
    ho_iot_jv_date = DateField("HO IOT JV date")


class JournalVoucerRemarksForm(FlaskForm):
    remarks = StringField("Enter remarks for JV", default="CC DD DEBITS ")


class MonthFilterForm(FlaskForm):
    month = SelectField()
    filter = SubmitField("Filter")
