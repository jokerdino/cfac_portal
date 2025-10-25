from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    DecimalField,
    TextAreaField,
    StringField,
)
from wtforms.validators import DataRequired, Optional


class BGForm(FlaskForm):
    ro_code = StringField("Regional Office Code", validators=[Optional()])
    oo_code = StringField("Operating Office Code", validators=[Optional()])

    customer_name = StringField(validators=[DataRequired()])
    customer_id = StringField("Customer ID / SL Code", validators=[DataRequired()])
    debit_amount = DecimalField(validators=[Optional()])
    credit_amount = DecimalField(validators=[Optional()])
    payment_id = StringField(validators=[DataRequired()])

    date_of_payment = DateField(validators=[DataRequired()])
    reason = TextAreaField("Reasons for BG balance", validators=[DataRequired()])
    course_of_action = TextAreaField(
        "Course of action for rectification of credit balance",
        validators=[Optional()],
    )
