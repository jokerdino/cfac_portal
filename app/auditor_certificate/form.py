from flask_wtf import FlaskForm
from wtforms import TextAreaField, StringField, DateField

from wtforms.validators import DataRequired, Optional, ValidationError

from .model import AuditorCertificate

from extensions import db


class AuditorCertificateForm(FlaskForm):
    ro_code = StringField("RO code", validators=[DataRequired()])
    ro_name = StringField("RO name", validators=[DataRequired()])

    purpose = TextAreaField(validators=[DataRequired()])
    tender_number = StringField(validators=[Optional()])
    date_of_request = DateField("Date of request", validators=[DataRequired()])

    bid_closing_date = DateField("Bid closing date", validators=[Optional()])
    certificate_issued_date = DateField(
        "Certificate issued date", validators=[Optional()]
    )

    invoice_received_date = DateField("Invoice received date", validators=[Optional()])
    invoice_number = StringField(validators=[Optional()])
    invoice_date = DateField("Invoice date", validators=[Optional()])

    remarks = TextAreaField(validators=[Optional()])

    disbursement_date = DateField("Disbursement date", validators=[Optional()])
    request_id = StringField("Request ID", validators=[Optional()])
    date_of_payment = DateField("Date of payment", validators=[Optional()])
    utr_number = StringField("UTR number", validators=[Optional()])

    def __init__(self, *args, obj_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.obj_id = obj_id

    def validate_tender_number(self, field):
        if not field.data:
            return

        query = db.select(AuditorCertificate).where(
            AuditorCertificate.tender_number == field.data
        )
        if self.obj_id:
            query = query.where(AuditorCertificate.id != self.obj_id)

        if db.session.scalar(query):
            raise ValidationError("Tender number already exists.")

    def validate_invoice_number(self, field):
        if not field.data:
            return

        query = db.select(AuditorCertificate).where(
            AuditorCertificate.invoice_number == field.data
        )
        if self.obj_id:
            query = query.where(AuditorCertificate.id != self.obj_id)

        if db.session.scalar(query):
            raise ValidationError("Invoice number already exists.")
