from flask_wtf import FlaskForm
#from flask_wtf.file import FileField
from wtforms import BooleanField, FileField, SubmitField
from wtforms.validators import DataRequired, Optional


class FileUploadForm(FlaskForm):
    file_upload = FileField("Bulk upload MIS Tracker file")
       # file_upload = FileField("Upload document", validators=[DataRequired()])
    upload_document = SubmitField("Upload")

class MISTrackerForm(FlaskForm):
    bool_mis_shared = BooleanField("Whether MIS has been shared", validators=[Optional()])
    bool_brs_completed = BooleanField("Whether BRS is completed", validators=[Optional()])
    bool_jv_passed = BooleanField("Whether necessary JV has been passed", validators=[Optional()])
