from flask_wtf import FlaskForm
from wtforms import TextAreaField, StringField


from wtforms.validators import DataRequired, Optional

class AnnouncementsForm(FlaskForm):
    title = StringField("Enter title of announcement", validators=[DataRequired()])
    message = TextAreaField("Enter announcement message", validators=[DataRequired()])
