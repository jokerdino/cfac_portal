from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import (
    DateField,
    IntegerField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Optional, ValidationError


class ContractsAddForm(FlaskForm):
    vendor = StringField(
        "Name of vendor",
        validators=[DataRequired()],
        filters=[lambda x: x.strip() if x else None],
    )
    purpose = StringField(
        "Nature of contract",
        validators=[DataRequired()],
    )
    start_date = DateField()
    end_date = DateField()
    emd = IntegerField("EMD", validators=[Optional()])
    notice_period = StringField()
    renewal = StringField("Renewal terms")
    remarks = TextAreaField()
    upload_contract_file = FileField("Upload copy of contract")

    def validate_end_date(self, field):
        if field.data < self.start_date.data:
            raise ValidationError("End date cannot be earlier than start date.")
