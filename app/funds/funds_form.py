from datetime import date

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired

from wtforms import (
    BooleanField,
    FileField,
    StringField,
    SelectField,
    TextAreaField,
    DateField,
    DecimalField,
    RadioField,
    SubmitField,
)
from wtforms.validators import DataRequired, Optional, ValidationError
from wtforms_sqlalchemy.orm import model_form


from .funds_model import FundJournalVoucherFlagSheet


def verify_months(start_date, end_date):
    return end_date.month - start_date.month


class ReportsForm(FlaskForm):
    start_date = DateField(validators=[DataRequired()])
    end_date = DateField(validators=[DataRequired()])
    check_inflow = BooleanField("Include inflow", validators=[Optional()], default=True)
    check_outflow = BooleanField(
        "Include outflow", validators=[Optional()], default=True
    )
    check_investments = BooleanField(
        "Include investments", validators=[Optional()], default=True
    )
    check_major_payments = BooleanField(
        "Include major payments", validators=[Optional()]
    )
    check_major_receipts = BooleanField(
        "Include major receipts", validators=[Optional()]
    )


class FundsJVForm(FlaskForm):
    start_date = DateField("Enter start date", validators=[DataRequired()])
    end_date = DateField("Enter end date", validators=[DataRequired()])

    def validate_end_date(self, field):
        if field.data < self.start_date.data:
            raise ValidationError("End date should not be earlier than start date.")
        # if (num_of_days(self.start_date.data, field.data) + 1) > 7:
        #    raise ValidationError("Maximum date range allowed is 7 days.")

        if verify_months(self.start_date.data, field.data) > 0:
            raise ValidationError("Start date and end date must be in same month.")


class UploadFileForm(FlaskForm):
    file_upload = FileField(
        "Upload document", validators=[FileRequired(), FileAllowed(["xlsx"])]
    )
    upload_document = SubmitField("Upload")


class OutflowForm(FlaskForm):
    # drawn_from_investment = DecimalField(
    #     "Drawn from investment", validators=[Optional()]
    # )
    # investment = FieldList(FormField(GivenToInvestment), min_entries=1)
    given_to_investment = DecimalField("Given to Investment", validators=[Optional()])
    expected_date_of_return = DateField(
        "Enter expected date of return", validators=[Optional()]
    )
    amount_citi_health = DecimalField("CITI Health", validators=[Optional()])
    amount_mro1_health = DecimalField("MRO1 Health", validators=[Optional()])

    amount_axis_neft = DecimalField("AXIS NEFT", validators=[Optional()])
    amount_citi_neft = DecimalField("CITI NEFT", validators=[Optional()])
    amount_tncmchis = DecimalField("TNCMCHIS", validators=[Optional()])
    amount_axis_centralised_cheque = DecimalField(
        "AXIS Centralised Cheque", validators=[Optional()]
    )
    amount_axis_centralised_cheque_521 = DecimalField(
        "AXIS Centralised Cheque 521", validators=[Optional()]
    )
    amount_axis_tds_gst = DecimalField("AXIS TDS RO", validators=[Optional()])
    amount_pension = DecimalField("Pension", validators=[Optional()])
    amount_gratuity = DecimalField("Gratuity", validators=[Optional()])
    amount_ro_bhopal_crop = DecimalField("RO Bhopal Crop", validators=[Optional()])
    amount_ro_nagpur_crop = DecimalField("RO Nagpur Crop", validators=[Optional()])
    amount_citi_omp = DecimalField("CITI OMP", validators=[Optional()])
    amount_hdfc_lien = DecimalField(
        "Amount held by HDFC under Lien", validators=[Optional()]
    )
    amount_other_payments = DecimalField("Other payments", validators=[Optional()])


#    amount_boa_tpa = DecimalField("BOA TPA", validators=[Optional()])


class FlagForm(FlaskForm):
    flag_description = StringField(
        "Description",
        validators=[DataRequired()],
        description="Name for the flag pattern",
    )
    flag_reg_exp = StringField(
        "Flag pattern",
        validators=[DataRequired()],
        description="Pattern to match in the bank statement",
    )


class DailySummaryForm(FlaskForm):
    text_major_collections = TextAreaField(
        "Enter details of major receipts", validators=[Optional()]
    )
    text_major_payments = TextAreaField(
        "Enter details of major payments", validators=[Optional()]
    )

    text_person1_name = SelectField(
        "Enter name of person 1",
        choices=["P Sudha Venkateswari", "S Vineeth", "G Suganya Priya"],
    )
    text_person1_designation = SelectField(
        "Enter designation of person 1", choices=["Assistant Manager", "Admin. Officer"]
    )
    text_person2_name = SelectField(
        "Enter name of person 2", choices=["A P Usha", "Gaddam Janakiram"]
    )
    text_person2_designation = SelectField(
        "Enter designation of person 2", choices=["Chief Manager"]
    )
    text_person3_name = SelectField("Enter name of person 3", choices=["S Hemamalini"])
    text_person3_designation = SelectField(
        "Enter designation of person 3", choices=["DGM & CFO"]
    )
    text_person4_name = SelectField("Enter name of person 4", choices=["Usha Girish"])
    text_person4_designation = SelectField(
        "Enter designation of person 4", choices=["General Manager"]
    )


class MajorOutgoForm(FlaskForm):
    date_of_outgo = DateField("Expected date of outgo", validators=[DataRequired()])
    float_expected_outgo = DecimalField(
        "Estimated outgo amount", validators=[DataRequired()]
    )
    text_dept = TextAreaField("Department / Region", validators=[DataRequired()])
    text_remarks = TextAreaField("Remarks", validators=[Optional()])
    current_status = RadioField(
        choices=["Pending", "Paid"], validators=[DataRequired()], default="Pending"
    )


class AmountGivenToInvestmentForm(FlaskForm):
    date_given_to_investment = DateField(
        "Date of transfer of amount to investment", validators=[DataRequired()]
    )
    float_amount_given_to_investment = DecimalField(
        "Amount given to investment", validators=[DataRequired()]
    )
    date_expected_date_of_return = DateField(
        "Expected date of return", validators=[DataRequired()]
    )
    text_remarks = TextAreaField("Remarks", validators=[Optional()])

    current_status = RadioField(
        choices=["Pending", "Received"], validators=[DataRequired()], default="Pending"
    )


class FundsModifyDatesForm(FlaskForm):
    old_date = DateField("Enter old date", validators=[DataRequired()])
    new_date = DateField("Enter new date", validators=[DataRequired()])
    submit_button = SubmitField("Submit")


JVFlagAddForm = model_form(
    FundJournalVoucherFlagSheet,
    only=[
        "txt_description",
        "txt_flag",
        "txt_gl_code",
        "txt_sl_code",
    ],
)


class FundsDeleteForm(FlaskForm):
    delete_date = DateField(validators=[DataRequired()])

    def validate_delete_date(self, field):
        if field.data != date.today():
            raise ValidationError("Delete date should be today.")
