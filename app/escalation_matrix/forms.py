from flask_wtf import FlaskForm
from wtforms import StringField

from wtforms.validators import DataRequired


class EscalationMatrixForm(FlaskForm):
    service_type = StringField(validators=[DataRequired()])
    nature_of_entity = StringField()
    name_of_entity = StringField()
    level = StringField()
    name = StringField()
    roll = StringField()
    email_address = StringField()
    contact_number = StringField()
