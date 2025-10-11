from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField,
    DateField,
    IntegerField,
    SelectField,
    TextAreaField,
    TimeField,
    SubmitField,
)

from wtforms.validators import DataRequired, Optional, ValidationError


class CircularForm(FlaskForm):
    date_of_issue = DateField("Date of issue", validators=[DataRequired()])
    circular_title = StringField("Circular title", validators=[DataRequired()])
    issued_by_name = StringField("Issued by", validators=[DataRequired()])
    issued_by_designation = StringField("Designation", validators=[DataRequired()])
    recipients = TextAreaField()
    remarks = TextAreaField()
    upload_document_file = FileField(validators=[FileAllowed(["pdf"])])


class InwardForm(FlaskForm):
    date_of_receipt = DateField("Date of receipt", validators=[DataRequired()])
    time_of_receipt = TimeField("Time of receipt", validators=[DataRequired()])
    sender_name = StringField("Sender name", validators=[DataRequired()])
    sender_address = StringField("Sender address", validators=[DataRequired()])
    mode_of_receipt = StringField("Mode of receipt", validators=[DataRequired()])
    letter_reference_number = StringField(
        "Letter reference number", validators=[DataRequired()]
    )
    description_of_item = TextAreaField(
        "Description of item", validators=[DataRequired()]
    )
    recipient_name = StringField("Recipient name", validators=[DataRequired()])
    received_by = StringField("Received by", validators=[DataRequired()])

    remarks = TextAreaField()
    upload_document_file = FileField(validators=[FileAllowed(["pdf"])])


class OutwardForm(FlaskForm):
    date_of_dispatch = DateField("Date of dispatch", validators=[DataRequired()])
    time_of_dispatch = TimeField("Time of dispatch", validators=[DataRequired()])
    recipient_name = StringField("Recipient name", validators=[DataRequired()])
    recipient_address = StringField("Recipient address", validators=[DataRequired()])
    mode_of_dispatch = StringField("Mode of dispatch", validators=[DataRequired()])

    description_of_item = TextAreaField(
        "Description of item", validators=[DataRequired()]
    )
    sender_name = StringField("Sender name", validators=[DataRequired()])
    dispatched_by = StringField("Dispatched by", validators=[DataRequired()])

    remarks = TextAreaField()
    upload_document_file = FileField(validators=[FileAllowed(["pdf"])])
