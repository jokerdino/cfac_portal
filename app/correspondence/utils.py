from datetime import datetime
from pathlib import Path

from flask import current_app
from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename

from extensions import db


def get_last_number(
    model,
    year,
    month,
    number_field="number",
    year_field="year",
    month_field="month",
):
    """
    Returns the highest value of `<number_field>` for a given model
    filtered by `<year_field>` and `<month_field>`.

    Example:
        get_last_number(Circular, 2025, 10)
    """
    number_col = getattr(model, number_field)
    year_col = getattr(model, year_field)
    month_col = getattr(model, month_field)

    return db.session.scalars(
        db.select(number_col)
        .where(year_col == year, month_col == month)
        .order_by(number_col.desc())
    ).first()


def upload_document_to_folder(
    model_object: object,
    form: FlaskForm,
    field: str,
    document_type: str,
    model_attribute: str,
    folder_name: str,
) -> None:
    """
    Uploads a document to the folder specified by folder_name and saves the filename to the object.

    :param model_object: The object to save the filename to
    :param form: The form containing the file to upload
    :param field: The name of the field in the form containing the file to upload
    :param document_type: The type of document being uploaded (e.g. "statement", "confirmation")
    :param model_attribute: The name of the attribute in the object to save the filename to
    :param folder_name: The folder to save the document in
    """

    upload_root = current_app.config.get("UPLOAD_FOLDER_PATH")
    folder_path = upload_root / "correspondence" / folder_name

    # Create directories if they do not exist
    folder_path.mkdir(parents=True, exist_ok=True)
    file = form.data.get(field)
    if file:
        filename = secure_filename(file.filename)
        file_extension = Path(filename).suffix  # includes leading dot

        document_filename = f"{document_type}_{datetime.now().strftime('%d%m%Y %H%M%S')}{file_extension}"

        file.save(folder_path / document_filename)

        setattr(model_object, model_attribute, document_filename)
