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


class BRSTrackerForm(FlaskForm):

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
    bool_current_status = BooleanField("Completed", validators=[Optional()])
    text_remarks = TextAreaField("Enter remarks", validators=[Optional()])
    submit_button = SubmitField("Submit")


class BulkUploadFileForm(FlaskForm):
    mis_tracker_file_upload = FileField(
        "Upload MIS tracker", validators=[DataRequired()]
    )
    accounts_tracker_file_upload = FileField(
        "Upload Accounts tracker", validators=[DataRequired()]
    )
    upload_document = SubmitField("Upload")


class FilterPeriodForm(FlaskForm):
    period = SelectField("Select period", validators=[DataRequired()])
