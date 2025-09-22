from math import fabs
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import (
    BooleanField,
    # FileField,
    DecimalField,
    IntegerField,
    HiddenField,
    TextAreaField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, Optional, NumberRange, ValidationError
from wtforms_sqlalchemy.orm import model_form

from .models import BankReconAccountDetails
from .forms_custom_validators import ExcelFileValidator


class BRSForm(FlaskForm):
    delete_cash_brs = BooleanField("Delete cash BRS")
    delete_cheque_brs = BooleanField("Delete cheque BRS")
    delete_pos_brs = BooleanField("Delete POS BRS")
    delete_pg_brs = BooleanField("Delete PG BRS")
    delete_bbps_brs = BooleanField("Delete BBPS BRS")
    delete_dqr_brs = BooleanField("Delete DQR BRS")
    delete_local_collection_brs = BooleanField("Delete local collection BRS")


class BRSEntryForm(FlaskForm):
    date_of_month = HiddenField()
    brs_type = HiddenField()
    int_closing_balance = HiddenField()
    int_balance_as_per_bank = HiddenField()
    int_opening_balance = DecimalField(
        "Opening balance as per GL", validators=[Optional()]
    )
    int_opening_on_hand = DecimalField(
        "Add: Opening cash/cheques on hand", validators=[Optional()]
    )
    int_transactions = DecimalField(
        "Add: Collections during the month", validators=[Optional()]
    )
    int_cancellations = DecimalField(
        "Less: Cancellations / dishonours during the month", validators=[Optional()]
    )
    int_fund_transfer = DecimalField("Less: Fund transfer", validators=[Optional()])
    int_bank_charges = DecimalField("Less: Bank charges", validators=[Optional()])
    int_closing_on_hand = DecimalField(
        "Less: Closing cash/cheques on hand", validators=[Optional()]
    )
    int_deposited_not_credited = DecimalField(
        "Less: Deposited but not credited", validators=[Optional()]
    )
    int_short_credited = DecimalField("Less: Short credit", validators=[Optional()])
    int_excess_credited = DecimalField("Add: Excess credit", validators=[Optional()])

    int_balance_as_per_bank = DecimalField(
        "Add: Closing balance as per bank statement (local collection)",
        validators=[Optional()],
    )

    file_outstanding_entries = FileField(
        "Upload outstanding entries in prescribed format",
        validators=[
            Optional(),
            FileAllowed(["csv"]),
            ExcelFileValidator(
                sum_column="instrument_amount",
                compare_field="int_deposited_not_credited",
                compare_field_name="Deposited but not credited",
            ),
        ],
    )

    file_short_credit_entries = FileField(
        "Upload short credit entries in prescribed format",
        validators=[
            Optional(),
            FileAllowed(["csv"]),
            ExcelFileValidator(
                sum_column="instrument_amount",
                compare_field="int_short_credited",
                compare_field_name="Short credit",
            ),
        ],
    )

    file_excess_credit_entries = FileField(
        "Upload excess credit entries in prescribed format",
        validators=[
            Optional(),
            FileAllowed(["csv"]),
            ExcelFileValidator(
                sum_column="instrument_amount",
                compare_field="int_excess_credited",
                compare_field_name="Excess credit",
            ),
        ],
    )

    remarks = TextAreaField("Enter remarks", validators=[Optional()])
    prepared_by = StringField("Prepared by", validators=[DataRequired()])
    prepared_by_employee_number = IntegerField(
        "Employee number",
        validators=[NumberRange(min=10000, max=99999), DataRequired()],
    )

    def validate_int_deposited_not_credited(form, field):
        if field.data:
            if not form.file_outstanding_entries.data:
                raise ValidationError("Details of outstanding entries are required.")

    def validate_int_short_credited(form, field):
        if field.data:
            if not form.file_short_credit_entries.data:
                raise ValidationError("Details of short credit entries are required.")

    def validate_int_excess_credited(form, field):
        if field.data:
            if not form.file_excess_credit_entries.data:
                raise ValidationError("Details of excess credit entries are required.")

    def validate(self, extra_validators=None):
        """Custom validation to check if the arithmetic condition holds"""
        if not super().validate(extra_validators=extra_validators):
            return False  # Ensure basic WTForms validators pass first

        opening_balance = self.int_opening_balance.data or 0
        opening_on_hand = self.int_opening_on_hand.data or 0
        transactions = self.int_transactions.data or 0
        cancellations = self.int_cancellations.data or 0
        fund_transfer = self.int_fund_transfer.data or 0
        bank_charges = self.int_bank_charges.data or 0
        closing_on_hand = self.int_closing_on_hand.data or 0
        int_deposited_not_credited = self.int_deposited_not_credited.data or 0
        int_short_credited = self.int_short_credited.data or 0
        int_excess_credited = self.int_excess_credited.data or 0
        int_closing_balance_bank_statement = self.int_balance_as_per_bank.data or 0
        closing_balance = (
            opening_balance
            + opening_on_hand
            + transactions
            - cancellations
            - fund_transfer
            - bank_charges
            - closing_on_hand
        )
        self.int_closing_balance.data = closing_balance
        bank_balance = (
            closing_balance
            + int_excess_credited
            - int_deposited_not_credited
            - int_short_credited
        )
        self.int_balance_as_per_bank.data = bank_balance
        closing_balance_breakup = (
            int_deposited_not_credited
            + int_short_credited
            - int_excess_credited
            + int_closing_balance_bank_statement
        )

        # Arithmetic Validation
        if (fabs(float(closing_balance_breakup) - float(closing_balance))) > 0.001:
            self.int_closing_on_hand.errors.append(
                f"Closing balance {closing_balance} must tally with closing balance breakup {closing_balance_breakup}."
            )
            return False

        return True


class DashboardForm(FlaskForm):
    month = SelectField("Select month")


class RawDataForm(FlaskForm):
    month = SelectField("Select month")
    brs_type = SelectField(
        "Select BRS type",
        choices=[
            ("cash", "Cash"),
            ("cheque", "Cheque"),
            ("pg", "PG"),
            ("pos", "POS"),
            ("bbps", "BBPS"),
            ("dqr", "DQR"),
            ("local_collection", "Local collection"),
            ("View all", "View all"),
        ],
    )


class EnableDeleteMonthForm(FlaskForm):
    txt_month = StringField("Month", validators=[DataRequired()])
    bool_enable_delete = BooleanField(
        "Enable month for deletion", validators=[Optional()]
    )
    submit = SubmitField("Submit")


BankReconAccountDetailsAddForm = model_form(
    BankReconAccountDetails,
    only=[
        "str_name_of_bank",
        "str_brs_type",
        "str_bank_account_number",
        "str_ifsc_code",
    ],
)
