from flask_wtf import FlaskForm, Form
from flask_wtf.file import FileField, FileAllowed, FileRequired

from wtforms import (
    TextAreaField,
    StringField,
    DateField,
    FieldList,
    FormField,
    HiddenField,
    SelectField,
    SubmitField,
)
from wtforms.validators import DataRequired, Optional


class BulkUploadForm(FlaskForm):
    upload_file = FileField()


class RegionalOfficeAuditReportUploadForm(FlaskForm):
    regional_office_code = StringField(
        validators=[DataRequired()], render_kw={"readonly": True}
    )
    period = StringField(validators=[DataRequired()], render_kw={"readonly": True})
    audit_report_file = FileField(
        "Upload RO Audit report",
        validators=[Optional(), FileAllowed(["pdf"])],
        render_kw={"class": "file", "accept": ".pdf"},
    )
    annexures_file = FileField(
        "Upload annexures (A, B, C, D)",
        validators=[Optional(), FileAllowed(["pdf"])],
        render_kw={"class": "file", "accept": ".pdf"},
    )
    notes_forming_part_of_accounts_file = FileField(
        "Upload notes forming part of Audit report",
        validators=[Optional(), FileAllowed(["pdf"])],
        render_kw={"class": "file", "accept": ".pdf"},
    )

    mode_of_dispatch = StringField(validators=[Optional()])
    date_of_dispatch = DateField(validators=[Optional()])
    tracking_number = StringField(validators=[Optional()])

    remarks = TextAreaField(validators=[Optional()])

    # Non-submitted fields to carry existing file URLs to the template
    existing_audit_report = None
    existing_annexures = None
    existing_notes_forming_part_of_accounts = None


class RegionalOfficeAuditObservationForm(FlaskForm):
    regional_office_code = StringField(
        validators=[DataRequired()], render_kw={"readonly": True}
    )
    period = StringField(
        validators=[DataRequired()], default="March-2026", render_kw={"readonly": True}
    )
    department = StringField(validators=[DataRequired()])
    audit_observation = TextAreaField(validators=[DataRequired()])
    regional_office_remarks = TextAreaField(validators=[DataRequired()])


class AuditorMappingRowForm(Form):
    mapping_id = HiddenField()
    regional_office_code = HiddenField("RO Code")
    regional_office_name = HiddenField("RO Name")
    period = HiddenField("Period")
    user_id = SelectField("Auditor", coerce=int, validators=[Optional()])


class AuditorMappingBulkForm(FlaskForm):
    mappings = FieldList(FormField(AuditorMappingRowForm))
    submit = SubmitField("Save")
