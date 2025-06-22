from flask_wtf import FlaskForm, Form
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import (
    RadioField,
    SubmitField,
    DateField,
    StringField,
    TextAreaField,
    IntegerField,
    DecimalField,
    SelectField,
)


from wtforms.validators import Optional, DataRequired


class UploadFileForm(FlaskForm):
    file_upload = FileField(
        "Upload document",
        validators=[FileRequired(), FileAllowed(["pdf"])],
        render_kw={"accept": ".pdf"},
    )
    file_process_option = RadioField(
        "Select option",
        choices=[("export_excel", "Excel extract"), ("split", "Split PDF file")],
    )
    line_number = IntegerField(validators=[DataRequired()])
    upload_document = SubmitField("Upload")


class IncomingReinsuranceConfirmationForm(FlaskForm):
    name_of_insured = StringField(validators=[DataRequired()])
    business_type = SelectField(
        choices=["Outgoing", "Incoming"], validators=[DataRequired()]
    )
    lob = SelectField(
        "LOB",
        choices=[
            "Fire",
            "Engineering",
            "Marine Cargo",
            "Marine Hull",
            "Liability",
            "Aviation",
            "Health",
            "Others",
        ],
        validators=[DataRequired()],
    )
    risk_type = SelectField(choices=["IAR", "MEGA"], validators=[DataRequired()])
    proposal_type = SelectField(
        choices=["Policy", "Endorsement"], validators=[DataRequired()]
    )
    endorsement_number = StringField(validators=[Optional()])
    proposal_number = StringField(validators=[DataRequired()])
    policy_number = StringField(validators=[DataRequired()])
    uw_year = StringField(validators=[DataRequired()])
    policy_start_date = DateField(validators=[DataRequired()])
    policy_end_date = DateField(validators=[DataRequired()])

    uiic_share_percentage = DecimalField(validators=[DataRequired()])
    policy_premium = DecimalField(validators=[DataRequired()])
    ri_premium = DecimalField(validators=[DataRequired()])
    broker_code = StringField(validators=[Optional()])
    broker_name = StringField(validators=[Optional()])
    reinsurer_code = StringField(validators=[DataRequired()])
    reinsurer_name = StringField(validators=[DataRequired()])
    fac_share_percentage = DecimalField(validators=[DataRequired()])
    gross_fac_premium = DecimalField(validators=[DataRequired()])
    commission_percentage = DecimalField(validators=[DataRequired()])
    commission_amount = DecimalField(validators=[DataRequired()])
    net_fac_premium = DecimalField(validators=[DataRequired()])
    core_cp_generated_date = DateField(validators=[Optional()])
    handed_to_accounts_dept_date = DateField(validators=[Optional()])
    ppw_date = DateField(validators=[Optional()])
    payment_period = StringField(validators=[Optional()])
    quarter = StringField(validators=[Optional()])
    cp_generated_by = StringField(validators=[Optional()])
    cp_number = StringField(validators=[Optional()])

    remarks = TextAreaField(validators=[Optional()])
    irda_data = TextAreaField(validators=[Optional()])

    leader_cp_documents = FileField(
        "Upload leader CP documents",
    )
    uiic_cp_documents = FileField("Upload UIIC CP documents")


class OutgoingReinsuranceConfirmationForm(FlaskForm): ...


class FetchProposalNumberForm(Form):
    proposal_number = StringField()
