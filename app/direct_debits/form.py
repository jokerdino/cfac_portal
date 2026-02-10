from flask_wtf import FlaskForm
from wtforms import DateField, TextAreaField, StringField
from flask_wtf.file import FileField, FileAllowed, FileRequired


class RegionalOfficeForm(FlaskForm):
    ro_jv_number = StringField("Enter JV number")
    ro_jv_date = DateField("Enter JV date")
    remarks = TextAreaField("Enter remarks")


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
