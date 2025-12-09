from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SelectField, DateField, TextAreaField
from wtforms.validators import DataRequired, Optional


class ChangeInstructionForm(FlaskForm):
    title = StringField(validators=[DataRequired()])
    description = TextAreaField(validators=[Optional()], render_kw={"rows": 5})

    ticket_date = DateField(validators=[DataRequired()])
    ticket_number = StringField(validators=[DataRequired()])
    current_status = SelectField(
        choices=[
            "CI raised",
            "CI number alloted",
            "Approach note received",
            "In development",
            "In UAT",
            "Pilot testing",
            "Deployed in production",
        ]
    )
    ci_document_file = FileField(
        "Upload CI document", validators=[FileAllowed(["pdf"])]
    )
    ci_number = StringField("CI number", validators=[Optional()])

    approach_note_date = DateField(validators=[Optional()])
    approach_note_document_file = FileField(
        "Upload approach note document",
        validators=[FileAllowed(["pdf", "odt", "doc", "docx"])],
    )

    approach_note_approval_date = DateField(validators=[Optional()])

    uat_testing_date = DateField("UAT testing date", validators=[Optional()])
    uat_remarks = TextAreaField("UAT remarks", render_kw={"rows": 4})
    pilot_deployment_date = DateField(
        "Date of pilot deployment (if any)", validators=[Optional()]
    )
    production_deployment_date = DateField(
        "Date of production deployment", validators=[Optional()]
    )
