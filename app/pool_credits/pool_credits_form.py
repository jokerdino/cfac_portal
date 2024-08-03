from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, Optional


class UpdatePoolCreditsForm(FlaskForm):
    str_regional_office_code = StringField("Enter RO Code", validators=[DataRequired()])
    text_remarks = TextAreaField("Enter remarks", validators=[Optional()])
