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
    date_of_issue = DateField("Date of Issue", validators=[DataRequired()])
    circular_number = StringField("Circular Number", validators=[DataRequired()])
    circular_title = StringField("Circular Title", validators=[DataRequired()])
    issued_by = StringField("Issued By", validators=[DataRequired()])
    mode_of_dispatch = StringField("Mode of Dispatch", validators=[DataRequired()])
    recipients = TextAreaField()
    number_of_copies = IntegerField("Number of Copies", validators=[DataRequired()])
    date_of_acknowledgement = DateField("Date of Acknowledgement")
    remarks = TextAreaField()
    upload_document_file = FileField(validators=[FileAllowed("pdf")])
