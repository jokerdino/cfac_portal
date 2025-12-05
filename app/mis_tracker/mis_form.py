from flask_wtf import FlaskForm

from wtforms import BooleanField, FileField, SubmitField, SelectField
from wtforms.validators import Optional


class FileUploadForm(FlaskForm):
    file_upload = FileField("Bulk upload MIS Tracker file")
    upload_document = SubmitField("Upload")


class MISTrackerForm(FlaskForm):
    bool_mis_shared = BooleanField(
        "Whether MIS has been shared", validators=[Optional()]
    )
    bool_brs_completed = BooleanField(
        "Whether BRS is completed", validators=[Optional()]
    )
    bool_jv_passed = BooleanField(
        "Whether necessary JV has been passed", validators=[Optional()]
    )


class FilterMonthForm(FlaskForm):
    month = SelectField()
    submit = SubmitField(render_kw={"class": "button is-success is-outlined"})
