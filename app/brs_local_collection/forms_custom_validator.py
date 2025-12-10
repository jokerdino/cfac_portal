from datetime import datetime

import pandas as pd
from wtforms.validators import ValidationError


class ExcelFileValidator:
    """Custom validator to check an uploaded Excel file against required columns, data types, and date constraints."""

    def __init__(self, sum_column=None, compare_field=None, compare_field_name=None):
        """
        :param required_columns: Dictionary of required column names and their expected types.
        :param date_columns: List of date columns to validate.
        :param sum_column: Column to sum for validation.
        :param compare_field: WTForm field to compare the sum_column against.
        """
        #  self.required_columns = required_columns
        #   self.date_columns = date_columns or []
        self.sum_column = sum_column
        self.compare_field = compare_field
        self.compare_field_name = compare_field_name

    def __call__(self, form, field):
        """Validate the uploaded Excel file."""
        file = field.data
        if not file:
            raise ValidationError("Please upload a file.")
        required_columns = {
            "instrument_amount": float,
            "instrument_number": str,
            "mode_of_collection": str,
            "remarks": str,
        }
        date_columns = ["date_of_collection", "date_of_instrument"]
        # if form.brs_type.data != "cash":
        #     required_columns["instrument_number"] = str
        #     date_columns.append("date_of_instrument")

        try:
            # Read Excel file with required data types
            df = pd.read_excel(file, dtype=required_columns)

            # Ensure required columns exist
            missing = set(required_columns.keys()) - set(df.columns)
            if missing:
                raise ValidationError(f"Missing required columns: {missing}")
            # Check for empty cells in required columns
            if df[required_columns.keys()].isnull().any().any():
                raise ValidationError(
                    "Some required fields have empty cells. Please fill all fields."
                )
            # Convert column types explicitly
            for col, dtype in required_columns.items():
                if dtype == float:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                    if df[col].isnull().any():
                        raise ValidationError(
                            f"Column '{col}' must be a valid numeric value."
                        )
                    # Prevent negative values
                    if (df[col] < 0).any():
                        raise ValidationError(
                            f"Column '{col}' contains negative values, which are not allowed."
                        )

            # Validate date columns
            # month = form.month.data
            max_date = pd.Timestamp(form.last_date_of_month.data)
            for date_col in date_columns:
                if date_col not in df.columns:
                    raise ValidationError(f"Missing required date column: '{date_col}'")
                df[date_col] = pd.to_datetime(
                    df[date_col], errors="coerce", format="%d/%m/%Y"
                )

                if df[date_col].isnull().any():
                    raise ValidationError(
                        f"Invalid dates found in '{date_col}'. Please enter dates in dd/mm/yyyy format."
                    )
                if df[date_col].ge(max_date).any():
                    raise ValidationError(
                        f"Dates in '{date_col}' cannot be in the future."
                    )
            # Validate sum comparison
            if self.sum_column and self.compare_field:
                sum_value = df[self.sum_column].sum()
                expected_value = float(form[self.compare_field].data)

                if abs(sum_value - expected_value) > 0.005:  # Allow a small tolerance
                    raise ValidationError(
                        f"Sum of '{self.sum_column}' ({sum_value}) does not match with {self.compare_field_name} ({expected_value})."
                    )

        except Exception as e:
            raise ValidationError(f"Error processing file: {str(e)}")
