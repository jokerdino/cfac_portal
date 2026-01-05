from datetime import datetime
from math import fabs

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import (
    BooleanField,
    DecimalField,
    IntegerField,
    HiddenField,
    TextAreaField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, Optional, NumberRange, ValidationError

from .forms_custom_validators import ExcelFileValidator


class BankReconDeleteForm(FlaskForm):
    delete_brs = BooleanField("Delete BRS")


class BankReconEntryForm(FlaskForm):
    month = HiddenField()
    last_date_of_month = HiddenField()
    closing_balance_gl = HiddenField()

    prepared_by_employee_name = StringField(
        "Prepared by - Employee name", validators=[DataRequired()]
    )
    prepared_by_employee_number = IntegerField(
        "Prepared by - Employee number",
        validators=[NumberRange(min=10000, max=99999), DataRequired()],
    )
    opening_balance = DecimalField("Opening balance as per GL", validators=[Optional()])

    fund_transfer = DecimalField("Add: Fund transfer", validators=[Optional()])
    cheques_issued = DecimalField("Less: Cheques issued", validators=[Optional()])

    cheques_cancelled = DecimalField("Add: Cheques cancelled", validators=[Optional()])
    bank_charges = DecimalField("Less: Bank charges", validators=[Optional()])

    closing_balance_bank = DecimalField(
        "Closing balance as per bank statement", validators=[Optional()]
    )
    cheques_unencashed = DecimalField(
        "Less: Unencashed cheques", validators=[Optional()]
    )
    remarks = TextAreaField()

    file_unencashed_entries = FileField(
        "Upload unencashed entries in prescribed format",
        validators=[
            Optional(),
            FileAllowed(["xlsx"]),
            ExcelFileValidator(
                required_columns={
                    "voucher_number": str,
                    "instrument_number": str,
                    "instrument_amount": float,
                    "payee_name": str,
                    "remarks": str,
                },
                date_columns=["instrument_date", "voucher_date"],
                sum_column="instrument_amount",
                compare_field="cheques_unencashed",
                compare_field_name="Less: Unencashed cheques",
            ),
        ],
    )

    file_bank_statement = FileField(
        "Upload bank statement", validators=[FileRequired()]
    )

    def validate_cheques_unencashed(form, field):
        if field.data:
            if not form.file_unencashed_entries.data:
                raise ValidationError("Details of unencashed entries are required.")

    def validate(self, extra_validators=None):
        """Custom validation to check if the arithmetic condition holds"""
        if not super().validate(extra_validators=extra_validators):
            return False  # Ensure basic WTForms validators pass first

        opening_balance = self.opening_balance.data or 0
        fund_transfer = self.fund_transfer.data or 0
        cheques_issued = self.cheques_issued.data or 0
        cheques_cancelled = self.cheques_cancelled.data or 0
        bank_charges = self.bank_charges.data or 0
        cheques_unencashed = self.cheques_unencashed.data or 0

        closing_balance_bank_statement = self.closing_balance_bank.data or 0
        closing_balance = (
            opening_balance
            + fund_transfer
            - cheques_issued
            + cheques_cancelled
            - bank_charges
        )
        self.closing_balance_gl.data = closing_balance

        closing_balance_breakup = closing_balance_bank_statement - cheques_unencashed

        # Arithmetic Validation
        if (fabs(float(closing_balance_breakup) - float(closing_balance))) > 0.001:
            self.closing_balance_bank.errors.append(
                f"Closing balance {closing_balance} must tally with closing balance breakup {closing_balance_breakup}."
            )
            return False

        return True


class AddBankReconImprestSummaryForm(FlaskForm):
    regional_office = StringField(validators=[DataRequired()])
    operating_office = StringField(validators=[DataRequired()])
    month = StringField(validators=[DataRequired()])
    purpose_of_bank_account = StringField()
    imprest_bank_name = StringField()
    imprest_bank_branch_name = StringField()
    imprest_bank_branch_location = StringField()
    imprest_bank_account_type = StringField()
    imprest_bank_account_number = StringField()
    imprest_bank_ifsc_code = StringField("Imprest bank IFSC code")

    def validate_month(self, field):
        try:
            datetime.strptime(field.data, "%B-%Y")
        except ValueError:
            raise ValidationError("Enter in MMM-YY format.")


class MonthFilterForm(FlaskForm):
    month = SelectField()
    submit = SubmitField()


class FileUploadForm(FlaskForm):
    upload_file = FileField()
