from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import StringField
from wtforms.validators import DataRequired


class WorkAllocationEditForm(FlaskForm):
    bank_name = StringField(validators=[DataRequired()])
    mode = StringField(validators=[DataRequired()])
    officer_name = StringField(validators=[DataRequired()])


class BulkUploadForm(FlaskForm):
    file = FileField(validators=[DataRequired()])
