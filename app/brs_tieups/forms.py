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

from .forms_custom_validator import ExcelFileValidator


class BankReconDeleteForm(FlaskForm):
    delete_brs = BooleanField("Delete BRS")


class BankReconEntryForm(FlaskForm):
    month = HiddenField()
    last_date_of_month = HiddenField()
    closing_balance = HiddenField()

    prepared_by_employee_name = StringField("Prepared by - Employee name")
    prepared_by_employee_number = IntegerField(
        "Prepared by - Employee number",
        validators=[NumberRange(min=10000, max=99999), DataRequired()],
    )
    opening_balance = DecimalField("Opening balance as per GL", validators=[Optional()])
    opening_on_hand = DecimalField(
        "Add: Opening cash/cheques on hand", validators=[Optional()]
    )
    transactions = DecimalField(
        "Add: Collections during the month", validators=[Optional()]
    )
    cancellations = DecimalField(
        "Less: Cancellations / dishonours during the month", validators=[Optional()]
    )
    fund_transfer = DecimalField("Less: Fund transfer", validators=[Optional()])
    bank_charges = DecimalField("Less: Bank charges", validators=[Optional()])
    closing_on_hand = DecimalField(
        "Less: Closing cash/cheques on hand", validators=[Optional()]
    )
    # closing_balance = DecimalField(validators=[Optional()])

    deposited_not_credited = DecimalField(
        "Less: Deposited but not credited", validators=[Optional()]
    )
    short_credited = DecimalField("Less: Short credit", validators=[Optional()])
    excess_credited = DecimalField("Add: Excess credit", validators=[Optional()])
    balance_as_per_bank = DecimalField(
        "Add: Closing balance as per bank statement", validators=[Optional()]
    )

    remarks = TextAreaField()

    file_outstanding_entries = FileField(
        "Upload outstanding entries in prescribed format",
        validators=[
            Optional(),
            FileAllowed(["xlsx"]),
            ExcelFileValidator(
                sum_column="instrument_amount",
                compare_field="deposited_not_credited",
                compare_field_name="Deposited but not credited",
            ),
        ],
    )

    file_short_credit_entries = FileField(
        "Upload short credit entries in prescribed format",
        validators=[
            Optional(),
            FileAllowed(["xlsx"]),
            ExcelFileValidator(
                sum_column="instrument_amount",
                compare_field="short_credited",
                compare_field_name="Short credit",
            ),
        ],
    )

    file_excess_credit_entries = FileField(
        "Upload excess credit entries in prescribed format",
        validators=[
            Optional(),
            FileAllowed(["xlsx"]),
            ExcelFileValidator(
                sum_column="instrument_amount",
                compare_field="excess_credited",
                compare_field_name="Excess credit",
            ),
        ],
    )

    # file_bank_statement = FileField(
    #     "Upload bank statement", validators=[FileRequired()]
    # )

    def validate_deposited_not_credited(form, field):
        if field.data:
            if not form.file_outstanding_entries.data:
                raise ValidationError("Details of outstanding entries are required.")

    def validate_short_credited(form, field):
        if field.data:
            if not form.file_short_credit_entries.data:
                raise ValidationError("Details of short credit entries are required.")

    def validate_excess_credited(form, field):
        if field.data:
            if not form.file_excess_credit_entries.data:
                raise ValidationError("Details of excess credit entries are required.")

    def validate(self, extra_validators=None):
        """Custom validation to check if the arithmetic condition holds"""
        if not super().validate(extra_validators=extra_validators):
            return False  # Ensure basic WTForms validators pass first

        opening_balance = self.opening_balance.data or 0
        opening_on_hand = self.opening_on_hand.data or 0
        transactions = self.transactions.data or 0
        cancellations = self.cancellations.data or 0
        fund_transfer = self.fund_transfer.data or 0
        bank_charges = self.bank_charges.data or 0
        closing_on_hand = self.closing_on_hand.data or 0
        deposited_not_credited = self.deposited_not_credited.data or 0
        short_credited = self.short_credited.data or 0
        excess_credited = self.excess_credited.data or 0
        closing_balance_bank_statement = self.balance_as_per_bank.data or 0
        closing_balance = (
            opening_balance
            + opening_on_hand
            + transactions
            - cancellations
            - fund_transfer
            - bank_charges
            - closing_on_hand
        )
        self.closing_balance.data = closing_balance

        closing_balance_breakup = (
            deposited_not_credited
            + short_credited
            - excess_credited
            + closing_balance_bank_statement
        )

        # Arithmetic Validation
        if (fabs(float(closing_balance_breakup) - float(closing_balance))) > 0.001:
            self.closing_on_hand.errors.append(
                f"Closing balance {closing_balance} must tally with closing balance breakup {closing_balance_breakup}."
            )
            return False

        return True


class AddBankReconTieupSummaryForm(FlaskForm):
    regional_office = StringField(validators=[DataRequired()])
    operating_office = StringField(validators=[DataRequired()])
    month = StringField()
    tieup_partner_name = StringField()

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
