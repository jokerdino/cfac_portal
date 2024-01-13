from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import (
    BooleanField,
    DateField,
    IntegerField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Optional, ValidationError


class ContractsAddForm(FlaskForm):
    vendor_name = StringField("Name of vendor", validators=[DataRequired()])
    purpose = StringField("Nature of contract", validators=[DataRequired()])
    start_date = DateField("Start date")
    end_date = DateField("End date")
    emd = IntegerField("EMD", validators=[Optional()])
    notice_period = StringField("Notice period")
    renewal = StringField("Renewal terms")
    remarks = TextAreaField("Enter remarks")
    upload_contract_file = FileField("Upload copy of contract")

    def validate_end_date(self, field):
        if field.data < self.start_date.data:
            raise ValidationError("End date cannot be earlier than start date.")


#  status = SelectField(
#     "Current status", choices=["Live", "Expired"]
# )

# vendor = db.Column(db.String)
# purpose = db.Column(db.String)
# start_date = db.Column(db.Date)
# end_date = db.Column(db.Date)
# status = db.Column(db.String)
# emd = db.Column(db.Integer)
# renewal = db.Column(db.String)
#
# remarks = db.Column(db.String)
# contract_file = db.Column(db.String)
