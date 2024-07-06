from flask_wtf import FlaskForm

from wtforms import (
    BooleanField,
    FileField,
    StringField,
    SelectField,
    TextAreaField,
    DateField,
    DecimalField,
    SubmitField,
)
from wtforms.validators import DataRequired, Optional, ValidationError

class WorkAddForm(FlaskForm):
    str_work = StringField("Enter description of work", validators=[DataRequired()])
    str_month = SelectField("Month", choices=["Dec", "Mar","Jun", "Sep"], validators=[DataRequired()])
    str_year = SelectField("Year", choices=["24", "25"], validators=[DataRequired()])
    str_assigned_to = SelectField("Assign to", validators=[DataRequired()])
    submit_button = SubmitField("Submit")

class BRSAddForm(FlaskForm):
    str_name_of_bank = StringField("Name of the bank", validators=[DataRequired()])
    str_month = SelectField("Month", choices=["Dec", "Mar","Jun", "Sep"], validators=[DataRequired()])
    str_year = SelectField("Year", choices=["24", "25"], validators=[DataRequired()])

    str_bank_address = StringField("Enter bank address", validators=[DataRequired()])
    str_gl_code = StringField("Enter GL Code", validators=[DataRequired()])
    str_sl_code = StringField("Enter SL Code", validators=[DataRequired()])
    str_bank_account_number = StringField("Enter Bank account number", validators=[DataRequired()])
    str_customer_id = StringField("Enter Customer ID", validators=[Optional()])

    str_purpose = StringField("Enter purpose of bank account", validators=[DataRequired()])
    str_assigned_to = SelectField("Assign to", validators=[DataRequired()])
    submit_button = SubmitField("Submit")

class BRSTrackerForm(FlaskForm):

    str_name_of_bank = StringField("Name of the bank", validators=[Optional()])
    str_assigned_to = SelectField("Assign to", validators=[Optional()])
    str_purpose = StringField("Update purpose", validators=[Optional()])

    boolean_mis_shared = BooleanField(
        "Whether MIS has been shared", validators=[Optional()]
    )
    str_brs_file_upload = FileField("Upload BRS file", validators=[Optional()])
    boolean_jv_passed = BooleanField(
        "Whether JV has been passed?", validators=[Optional()]
    )
    str_bank_confirmation_file_upload = FileField(
        "Upload Bank confirmation", validators=[Optional()]
    )
    text_remarks = TextAreaField("Enter remarks", validators=[Optional()])
    submit_button = SubmitField("Submit")


class AccountsTrackerForm(FlaskForm):
    str_work = StringField("Work item", validators=[Optional()])
    str_assigned_to = SelectField("Assign to", validators=[Optional()])

    bool_current_status = BooleanField("Completed", validators=[Optional()])
    text_remarks = TextAreaField("Enter remarks", validators=[Optional()])
    submit_button = SubmitField("Submit")


class BulkUploadFileForm(FlaskForm):
    mis_tracker_file_upload = FileField(
        "Upload MIS tracker", validators=[Optional()]
    )
    accounts_tracker_file_upload = FileField(
        "Upload Accounts tracker", validators=[Optional()]
    )
    upload_document = SubmitField("Upload")


class FilterPeriodForm(FlaskForm):
    period = SelectField("Select period", validators=[DataRequired()])
