from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import RadioField, SubmitField


class UploadFileForm(FlaskForm):
    file_upload = FileField(
        "Upload document",
        validators=[FileRequired(), FileAllowed(["pdf"])],
        render_kw={"accept": ".pdf"},
    )
    file_process_option = RadioField(
        "Process option",
        choices=[("export_excel", "Excel extract"), ("split", "Split PDF file")],
    )
    upload_document = SubmitField("Upload")
