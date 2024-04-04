from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    FileField,
    DateField,
    DecimalField,
    IntegerField,
    TextAreaField,
    SelectField,
    StringField,
)
from wtforms.validators import DataRequired, Optional, NumberRange


class BGForm(FlaskForm):
    regional_code = StringField("Enter Regional Office Code", validators=[Optional()])
    office_code = StringField("Enter Operating Office Code", validators=[Optional()])

    customer_name = StringField("Enter customer name", validators=[DataRequired()])
    customer_id = StringField("Enter Customer ID", validators=[DataRequired()])
    debit_amount = DecimalField("Enter debit amount", validators=[Optional()])
    credit_amount = DecimalField("Enter credit amount", validators=[Optional()])
    payment_id = StringField("Enter Payment ID", validators=[DataRequired()])

    date_of_payment = DateField("Enter date of payment", validators=[DataRequired()])
    reason = TextAreaField("Enter reasons for the same", validators=[Optional()])
    course_of_action = TextAreaField("Enter course of action", validators=[Optional()])
