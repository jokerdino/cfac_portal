from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import IntegerField, RadioField, SubmitField
from wtforms.validators import DataRequired


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
    upload_document = SubmitField("Upload")
