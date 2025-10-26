from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Optional


class UpdatePoolCreditsForm(FlaskForm):
    str_regional_office_code = SelectField("Enter RO Code", validators=[DataRequired()])
    text_remarks = TextAreaField("Enter remarks", validators=[Optional()])


class FilterMonthForm(FlaskForm):
    month = SelectField(validators=[DataRequired()])


class PoolCreditsJVForm(FlaskForm):
    str_regional_office_code = StringField(
        "Confirmed by",
        validators=[DataRequired()],
        filters=[lambda x: x.strip() if x else None],
    )
    gl_code = StringField(
        "GL code",
        validators=[DataRequired()],
        filters=[lambda x: x.strip() if x else None],
    )
    sl_code = StringField(
        "SL code",
        validators=[DataRequired()],
        filters=[lambda x: x.strip() if x else None],
    )


class JVUploadForm(FlaskForm):
    jv_file = FileField(
        "Upload JV mapping file",
        render_kw={"accept": ".xlsx", "class": "file"},
        validators=[FileRequired(), FileAllowed(["xlsx"])],
    )
