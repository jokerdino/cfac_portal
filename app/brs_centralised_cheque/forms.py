from math import fabs
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import (
    BooleanField,
    DecimalField,
    HiddenField,
    IntegerField,
    TextAreaField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    Optional,
    NumberRange,
    InputRequired,
    ValidationError,
)

from .forms_custom_validators import ExcelFileValidator


class EnableDeleteMonthForm(FlaskForm):
    date_of_month = StringField()
    enable_delete = BooleanField()
    submit = SubmitField(render_kw={"class": "button is-success"})


class DeleteMonthForm(FlaskForm):
    delete_cc_brs = BooleanField("Delete Centralised cheque BRS")
    submit = SubmitField()


class CentralisedChequeBankReconForm(FlaskForm):
    date_of_month = HiddenField()
    prepared_by_employee_name = StringField(
        "Prepared by",
        validators=[DataRequired()],
        render_kw={"class": "input is-small"},
    )
    prepared_by_employee_number = IntegerField(
        "Employee number",
        validators=[NumberRange(min=10000, max=99999), DataRequired()],
        render_kw={"class": "input is-small"},
    )
    opening_balance_unencashed = DecimalField(
        "Opening balance: Unencashed cheques",
        validators=[InputRequired()],
        render_kw={"class": "input is-small", "readonly": "readonly"},
    )
    opening_balance_stale = DecimalField(
        "Opening balance: Stale cheques",
        validators=[InputRequired()],
        render_kw={"class": "input is-small", "readonly": "readonly"},
    )
    cheques_issued = DecimalField(
        "Add: Cheques issued",
        validators=[InputRequired()],
        render_kw={"class": "input is-small"},
    )
    cheques_reissued_unencashed = DecimalField(
        "Add: Cheques reissued",
        validators=[InputRequired()],
        render_kw={"class": "input is-small"},
    )
    cheques_reissued_stale = DecimalField(
        "Less: Cheques reissued",
        validators=[InputRequired()],
        render_kw={"class": "input is-small", "readonly": "readonly"},
    )
    cheques_cleared = DecimalField(
        "Less: Cheques cleared",
        validators=[InputRequired()],
        render_kw={"class": "input is-small"},
    )
    cheques_cancelled = DecimalField(
        "Less: Cheques cancelled",
        validators=[InputRequired()],
        render_kw={"class": "input is-small"},
    )
    closing_balance_unencashed = DecimalField(
        "Closing balance: Unencashed cheques",
        validators=[InputRequired()],
        render_kw={
            "class": "input is-small",
            "onload": "calculateClosingBalance();",
            "onkeyup": "calculateClosingBalance();",
        },
    )
    closing_balance_stale = DecimalField(
        "Closing balance: Stale cheques",
        validators=[InputRequired()],
        render_kw={
            "class": "input is-small",
            "onload": "calculateClosingBalance();",
            "onkeyup": "calculateClosingBalance();",
        },
    )

    remarks = TextAreaField(render_kw={"class": "textarea"}, validators=[Optional()])
    unencashed_cheques_file = FileField(
        "Upload unencashed cheques in prescribed format",
        validators=[
            Optional(),
            FileAllowed(["xlsx"]),
            ExcelFileValidator(
                required_columns={
                    "voucher_number": str,
                    "transaction_id": str,
                    "instrument_number": str,
                    "instrument_amount": float,
                    "payee_name": str,
                    "remarks": str,
                },
                date_columns=["instrument_date", "voucher_date"],
                sum_column="instrument_amount",
                compare_field="closing_balance_unencashed",
            ),
        ],
        render_kw={
            "class": "file",
            "accept": ".xlsx",
        },
    )
    stale_cheques_file = FileField(
        "Upload stale cheques in prescribed format",
        validators=[
            Optional(),
            FileAllowed(["xlsx"]),
            ExcelFileValidator(
                required_columns={
                    "voucher_number": str,
                    "transaction_id": str,
                    "instrument_number": str,
                    "instrument_amount": float,
                    "payee_name": str,
                    "remarks": str,
                },
                date_columns=["instrument_date", "voucher_date"],
                sum_column="instrument_amount",
                compare_field="closing_balance_stale",
            ),
        ],
        render_kw={
            "class": "file",
            "accept": ".xlsx",
        },
    )
    submit = SubmitField()

    def validate_closing_balance_unencashed(form, field):
        if field.data:
            if not form.unencashed_cheques_file.data:
                raise ValidationError("Details of unencashed cheques are required.")

    def validate_closing_balance_stale(form, field):
        if field.data:
            if not form.stale_cheques_file.data:
                raise ValidationError("Details of stale cheques are required.")

    def validate(self, extra_validators=None):
        """Custom validation to check if the arithmetic condition holds"""
        if not super().validate(extra_validators=extra_validators):
            return False  # Ensure basic WTForms validators pass first
            # Extract values
        opening_unencashed = self.opening_balance_unencashed.data or 0
        opening_stale = self.opening_balance_stale.data or 0
        cheques_issued = self.cheques_issued.data or 0
        cheques_reissued_unencashed = self.cheques_reissued_unencashed.data or 0
        cheques_reissued_stale = self.cheques_reissued_stale.data or 0
        cheques_cleared = self.cheques_cleared.data or 0
        cheques_cancelled = self.cheques_cancelled.data or 0
        closing_unencashed = self.closing_balance_unencashed.data or 0
        closing_stale = self.closing_balance_stale.data or 0

        # Arithmetic Validation
        if (
            fabs(
                (
                    opening_unencashed
                    + opening_stale
                    + cheques_issued
                    + cheques_reissued_unencashed
                    - cheques_reissued_stale
                    - cheques_cleared
                    - cheques_cancelled
                )
                - (closing_unencashed + closing_stale)
            )
            > 0.005
        ):
            self.opening_balance_unencashed.errors.append(
                "Opening + New cheques must equal Closing + Cleared cheques."
            )
            return False

        return True


class CentralisedChequeDashboardForm(FlaskForm):
    month = SelectField()
    submit = SubmitField(render_kw={"class": "button is-success is-outlined"})


class BulkUploadCentralisedChequeSummary(FlaskForm):
    file_upload = FileField(
        validators=[FileRequired(), FileAllowed(["xlsx"])],
    )
    submit = SubmitField()
