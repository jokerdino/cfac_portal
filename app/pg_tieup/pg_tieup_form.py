from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import BooleanField, DateField, StringField, SubmitField
from wtforms.validators import DataRequired, Optional


class PaymentGatewayTieupAddForm(FlaskForm):

    name_of_head_office_department = StringField(
        "Name of head office department", validators=[DataRequired()]
    )
    date_of_request_from_head_office_department = DateField(
        "Date of request from Head Office department", validators=[Optional()]
    )
    name_of_tieup_partner = StringField(
        "Name of tieup partner", validators=[DataRequired()]
    )
    similar_request_from_other_department = BooleanField(
        "Whether similar request from other department was received for same tieup partner"
    )
    nodal_office_agree_for_pg_vender = BooleanField(
        "Whether nodal office agreeable for UIIC PG vendor"
    )
    mou_validity_date = DateField("MOU Validity date", validators=[Optional()])
    ro_code = StringField("RO Code", validators=[Optional()])
    nodal_office_code = StringField("Nodal office code", validators=[Optional()])
    nodal_office_name = StringField("Nodal office name", validators=[Optional()])
    tieup_partner_id_for_bank_mandate = StringField(
        "Tieup partner ID/VA for bank mandate", validators=[Optional()]
    )
    date_informed_to_bank_for_bank_mandate = DateField(
        "Date informed to bank for bank mandate", validators=[Optional()]
    )
    date_of_receipt_of_bank_mandate_with_bank_seal = DateField(
        "Date of receipt of bank mandate with bank seal", validators=[Optional()]
    )
    date_bank_mandate_shared_with_pg_vendor = DateField(
        "Date bank mandate shared with PG vendor", validators=[Optional()]
    )
    mid_or_similar_id_as_per_pg_vendor = StringField(
        "MID or similar ID as per PG vendor", validators=[Optional()]
    )
    old_mid_name = StringField("Old MID name", validators=[Optional()])
    date_of_receipt_of_staging_details = DateField(
        "Date of receipt of staging details", validators=[Optional()]
    )
    date_of_sharing_staging_details_to_head_office_dept = DateField(
        "Date of sharing staging details to head office department",
        validators=[Optional()],
    )
    staging_details = StringField("Staging Details", validators=[Optional()])

    date_of_receipt_of_production_details = DateField(
        "Date of receipt of production details", validators=[Optional()]
    )
    production_details = StringField(validators=[Optional()])
    bank_account_details_where_credit_is_expected = StringField()
    bank_name = StringField()
    bank_account_number = StringField()
    whether_t_plus_one_transfer_happening = BooleanField(
        "Whether T+1 transfer is happening"
    )
    brs_done_upto = DateField("BRS done", validators=[Optional()])
    spoc_name = StringField("SPOC Name", validators=[Optional()])
    spoc_employee_number = StringField("SPOC employee number", validators=[Optional()])
    ro_spoc_email_address = StringField(
        "RO SPOC email address", validators=[Optional()]
    )
    nodal_office_spoc_email_address = StringField(
        "Nodal office SPOC email address", validators=[Optional()]
    )
    nodal_office_gst_address = StringField(
        "Nodal Office GST address", validators=[Optional()]
    )
    date_of_bank_charges_jv_passed_to_nodal_office = DateField(
        "Date of bank charges JV passed to nodal office", validators=[Optional()]
    )


class UploadFileForm(FlaskForm):
    file_upload = FileField(
        "Upload document", validators=[FileRequired(), FileAllowed(["xlsx"])]
    )
    upload_document = SubmitField("Upload")
