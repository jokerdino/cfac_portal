from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import (
    StringField,
    DateField,
    SubmitField,
    DecimalField,
    TextAreaField,
    SelectField,
)
from wtforms.validators import DataRequired, Optional
from wtforms_sqlalchemy.orm import model_form

from .models import DqrMachines


class UploadFileForm(FlaskForm):
    file = FileField("File", validators=[FileRequired()])
    submit = SubmitField("Upload")


class DQRRefundEditForm(FlaskForm):
    organisation = StringField(default="United India Insurance Co.")
    ro_code = SelectField(
        "RO code",
        choices=[],
    )
    office_code = SelectField(
        choices=[],
    )
    device_serial_number = StringField(render_kw={"readonly": True})
    refund_amount = DecimalField(validators=[DataRequired()])
    txn_date = DateField(validators=[DataRequired()])
    txn_currency = StringField(default="INR", render_kw={"readonly": True})
    refund_currency = StringField(default="INR", render_kw={"readonly": True})
    auth_code = StringField(render_kw={"readonly": True})
    mid = StringField("MID", render_kw={"readonly": True})
    tid = StringField("TID", render_kw={"readonly": True})
    txn_amt = DecimalField(render_kw={"readonly": True}, validators=[DataRequired()])
    rrn = StringField("RRN", validators=[DataRequired()])
    account_number = StringField(default="719011004568", render_kw={"readonly": True})
    reason_for_refund = TextAreaField(validators=[DataRequired()])
    date_of_email_sent_to_bank = DateField(
        "Date of email sent to bank for refund", validators=[DataRequired()]
    )
    refund_ref_no = StringField(validators=[Optional()])
    refund_date = DateField(validators=[Optional()])
    ro_remarks = TextAreaField("OO/RO remarks", validators=[Optional()])
    refund_status = SelectField(
        choices=["Refund pending", "Refund completed"], default="Refund pending"
    )
    submit = SubmitField()


DQRMachineEditForm = model_form(
    DqrMachines,
    only=[
        "ro_code",
        "merchant_name",
        "merchant_dba_name",
        "mid",
        "tid",
        "mcc_code",
        "office_code",
        "address",
        "city",
        "pincode",
        "state",
        "name",
        "login",
        "user_id",
        "password",
        "device_name",
        "status",
        "device_serial_number",
        "installation_date",
    ],
)
