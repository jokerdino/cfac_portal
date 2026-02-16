from flask_wtf import FlaskForm
from wtforms import TextAreaField, StringField, DateField, SelectField

from wtforms.validators import DataRequired, Optional


class AuditorCertificateForm(FlaskForm):
    ro_code = StringField(validators=[DataRequired()])
    ro_name = StringField(validators=[DataRequired()])

    purpose = TextAreaField(validators=[DataRequired()])
    date_of_request = DateField(validators=[DataRequired()])

    bid_closing_date = DateField(validators=[Optional()])
    certificate_issued_date = DateField(validators=[Optional()])

    invoice_received_date = DateField(validators=[Optional()])
    invoice_date = DateField(validators=[Optional()])

    remarks = TextAreaField(validators=[Optional()])

    disbursement_date = DateField(validators=[Optional()])
    request_id = StringField(validators=[Optional()])
    date_of_payment = DateField(validators=[Optional()])
    utr_number = StringField(validators=[Optional()])
