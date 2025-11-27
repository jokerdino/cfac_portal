from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import IntegerField, RadioField, StringField, SubmitField
from wtforms.validators import DataRequired, Optional


class UploadFileForm(FlaskForm):
    file_upload = FileField(
        "Upload document",
        validators=[FileRequired(), FileAllowed(["pdf"])],
        render_kw={"accept": ".pdf"},
    )
    file_process_option = RadioField(
        "Select option",
        choices=[("export_excel", "Excel extract"), ("split", "Split PDF file")],
    )
    line_number = IntegerField(validators=[DataRequired()])
    prefix = StringField(validators=[Optional()])
    suffix = StringField(validators=[Optional()])
    upload_document = SubmitField("Upload")
