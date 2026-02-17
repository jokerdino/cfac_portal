from flask_wtf import FlaskForm
from wtforms import TextAreaField, StringField, DateField, SelectField

from wtforms.validators import DataRequired, Optional


class AuditorCertificateForm(FlaskForm):
    ro_code = StringField("RO code", validators=[DataRequired()])
    ro_name = StringField("RO name", validators=[DataRequired()])

    purpose = TextAreaField(validators=[DataRequired()])
    date_of_request = DateField("Date of request", validators=[DataRequired()])

    bid_closing_date = DateField("Bid closing date", validators=[Optional()])
    certificate_issued_date = DateField(
        "Certificate issued date", validators=[Optional()]
    )

    invoice_received_date = DateField("Invoice received date", validators=[Optional()])
    invoice_date = DateField("Invoice date", validators=[Optional()])

    remarks = TextAreaField(validators=[Optional()])

    disbursement_date = DateField("Disbursement date", validators=[Optional()])
    request_id = StringField("Request ID", validators=[Optional()])
    date_of_payment = DateField("Date of payment", validators=[Optional()])
    utr_number = StringField("UTR number", validators=[Optional()])
