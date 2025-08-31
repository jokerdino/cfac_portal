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
