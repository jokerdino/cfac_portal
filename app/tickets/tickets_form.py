from flask_wtf import FlaskForm
from wtforms import SelectField, BooleanField, EmailField, StringField, TextAreaField
from wtforms.validators import DataRequired, Optional


class TicketsForm(FlaskForm):
    regional_office_code = StringField(
        "Enter Regional Office Code", validators=[Optional()]
    )
    office_code = StringField("Enter Office Code", validators=[Optional()])
    ticket_number = StringField("Enter HPSM Ticket number", validators=[DataRequired()])
    contact_person = StringField("Contact person name", validators=[DataRequired()])
    contact_mobile_number = StringField(
        "Contact mobile number", validators=[DataRequired()]
    )

    contact_email_address = EmailField(
        "Contact email address", validators=[DataRequired()]
    )
    department = SelectField(
        "Select department",
        choices=[
            ("Coinsurance", "Coinsurance"),
            ("GST", "GST"),
            ("TDS", "TDS"),
            ("Payment gateway", "Payment gateway"),
            ("Centralised cheque", "Centralised cheque"),
            ("Claims", "Claims"),
            (
                "Voucher cancellation",
                "Voucher cancellation (other than centralised SWD)",
            ),
            ("NEFT rejection", "NEFT rejection"),
            ("JV for blocked GL codes", "JV for blocked GL codes"),
            ("Others", "Others"),
        ],
    )
    status = SelectField(
        "Status",
        choices=[
            "Pending for CFAC approval",
            "Clarification to be provided by RO or OO",
            "Approval provided by CFAC",
            "Resolved",
            "No longer relevant",
        ],
    )
    initial_remarks = TextAreaField("Enter remarks")
    regional_incharge_approval = BooleanField(
        "Regional Incharge approval is available", validators=[DataRequired()]
    )


class TicketFilterForm(FlaskForm):
    department = SelectField()


class TicketDashboardForm(FlaskForm):
    status = SelectField(
        choices=[
            "View all",
            "Pending for CFAC approval",
            "Clarification to be provided by RO or OO",
            "Approval provided by CFAC",
            "Resolved",
            "No longer relevant",
        ],
        default="Pending for CFAC approval",
    )
