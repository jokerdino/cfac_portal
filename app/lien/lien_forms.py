from flask_wtf import FlaskForm
from wtforms import DateField, StringField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Optional
from flask_wtf.file import FileField, FileAllowed, FileRequired


class LienForm(FlaskForm):
    ro_code = StringField("RO Code")
    ro_name = StringField("RO Name")

    court_name = StringField()
    case_number = StringField()
    petitioner_name = StringField()
    date_of_order = DateField(validators=[Optional()])
    action_taken_by_banker = TextAreaField()
    lien_amount = IntegerField(validators=[Optional()])
    dd_amount = IntegerField("DD Amount", validators=[Optional()])

    bank_name = StringField()
    account_number = StringField()

    ro_remarks = TextAreaField("RO Remarks")

    court_order_lien_file = FileField("Upload court order - lien")
    court_order_dd_file = FileField("Upload DD copy")
    court_order_lien_reversal_file = FileField("Upload court order - lien reversal")


class LienUploadForm(FlaskForm):
    lien_file = FileField(
        "Upload lien file", validators=[FileRequired(), FileAllowed(["xlsx"])]
    )
