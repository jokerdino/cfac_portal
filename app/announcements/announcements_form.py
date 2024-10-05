from flask_wtf import FlaskForm
from wtforms import TextAreaField, StringField

from wtforms.validators import DataRequired


class AnnouncementsForm(FlaskForm):
    txt_title = StringField("Enter title of announcement", validators=[DataRequired()])
    txt_message = TextAreaField(
        "Enter announcement message", validators=[DataRequired()]
    )
