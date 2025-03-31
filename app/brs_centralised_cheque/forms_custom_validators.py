import pandas as pd
from wtforms.validators import ValidationError


class ExcelFileValidator:
    """Custom validator to check an uploaded Excel file against required columns, data types, and date constraints."""

    def __init__(
        self, required_columns, date_columns=None, sum_column=None, compare_field=None
    ):
        """
        :param required_columns: Dictionary of required column names and their expected types.
        :param date_columns: List of date columns to validate.
        :param sum_column: Column to sum for validation.
        :param compare_field: WTForm field to compare the sum_column against.
        """
        self.required_columns = required_columns
        self.date_columns = date_columns or []
        self.sum_column = sum_column
        self.compare_field = compare_field

    def __call__(self, form, field):
        """Validate the uploaded Excel file."""
        file = field.data
        try:
            # Read Excel file with required data types
            df = pd.read_excel(file, dtype=self.required_columns)
            # Ensure required columns exist
            missing = set(self.required_columns.keys()) - set(df.columns)
            if missing:
                raise ValidationError(f"Missing required columns: {missing}")
            # Check for empty cells in required columns
            if df[self.required_columns.keys()].isnull().any().any():
                raise ValidationError(
                    "Some required fields have empty cells. Please fill all fields."
                )
            # Convert column types explicitly
            for col, dtype in self.required_columns.items():
                if dtype == float:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                    if df[col].isnull().any():
                        raise ValidationError(
                            f"Column '{col}' must be a valid numeric value."
                        )
            # Validate date columns
            max_date = pd.Timestamp(form.date_of_month.data)
            for date_col in self.date_columns:
                if date_col in df.columns:
                    df[date_col] = pd.to_datetime(
                        df[date_col], errors="coerce", format="%d/%m/%Y"
                    )
                    if df[date_col].isnull().any():
                        raise ValidationError(f"Invalid dates found in '{date_col}'.")
                    if df[date_col].gt(max_date).any():
                        raise ValidationError(
                            f"Dates in '{date_col}' cannot be in the future."
                        )
            # Validate sum comparison
            if self.sum_column and self.compare_field:
                sum_value = df[self.sum_column].sum()
                expected_value = float(form[self.compare_field].data)

                if abs(sum_value - expected_value) > 0.005:  # Allow a small tolerance
                    raise ValidationError(
                        f"Sum of '{self.sum_column}' ({sum_value}) does not match {self.compare_field} ({expected_value})."
                    )

        except Exception as e:
            raise ValidationError(f"Error processing file: {str(e)}")
