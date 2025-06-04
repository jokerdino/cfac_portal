import os
from datetime import datetime
from io import BytesIO
import re
import zipfile

import pandas as pd
import pdfplumber
from pypdf import PdfReader, PdfWriter

from flask import (
    render_template,
    send_file,
    redirect,
    url_for,
    current_app,
    send_from_directory,
)
from flask_login import login_required
from werkzeug.utils import secure_filename

from . import reinsurance_bp
from .forms import (
    UploadFileForm,
    IncomingReinsuranceConfirmationForm,
    OutgoingReinsuranceConfirmationForm,
)
from .models import IncomingReinsuranceConfirmations, OutgoingReinsuranceConfirmations
from extensions import db


def upload_document(
    model_object, form, field, model_column, document_type, folder_name
):
    """
    Uploads a document to the folder specified by folder_name and saves the filename to the object.

    :param object: The object to save the filename to
    :param form: The form containing the file to upload
    :param field: The name of the field in the form containing the file to upload
    :param model column: The name of the column in the model object.
    :param document_type: The type of document being uploaded (e.g. "statement", "confirmation")
    :param folder_name: The folder to save the document in
    """
    folder_path = os.path.join(
        current_app.config.get("UPLOAD_FOLDER"), "reinsurance", folder_name
    )

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    filename = secure_filename(form.data[field].filename)
    file_extension = filename.rsplit(".", 1)[1]
    document_filename = (
        f"{document_type}_{datetime.now().strftime('%d%m%Y %H%M%S')}.{file_extension}"
    )

    form.data[field].save(os.path.join(folder_path, document_filename))

    setattr(model_object, model_column, document_filename)


@reinsurance_bp.route(
    "/incoming/<int:id>/download/<string:document>/", methods=["POST", "GET"]
)
@login_required
def download_document(id, document):
    incoming = db.get_or_404(IncomingReinsuranceConfirmations, id)

    if document == "leader_cp_documents":
        file_extension = incoming.file_leader_cp_documents.rsplit(".", 1)[1]
        path = incoming.file_leader_cp_documents
    elif document == "uiic_cp_documents":
        file_extension = incoming.file_uiic_cp_documents.rsplit(".", 1)[1]
        path = incoming.file_uiic_cp_documents
    else:
        return "No such requirement"

    filename = f"{document} - {incoming.name_of_insured}_{incoming.proposal_type}_{incoming.endorsement_number}_{incoming.reinsurer_name}.{file_extension}"
    return send_from_directory(
        directory=f"{current_app.config.get('UPLOAD_FOLDER')}/reinsurance/{document}/",
        path=path,
        as_attachment=True,
        download_name=filename,
    )


@reinsurance_bp.route("/incoming/add/", methods=["POST", "GET"])
@login_required
def add_incoming():
    form = IncomingReinsuranceConfirmationForm()
    if form.validate_on_submit():
        incoming = IncomingReinsuranceConfirmations()
        form.populate_obj(incoming)
        db.session.add(incoming)
        if form["leader_cp_documents"].data:
            upload_document(
                incoming,
                form,
                "leader_cp_documents",
                "file_leader_cp_documents",
                "leader_cp_documents",
                "leader_cp_documents",
            )
        if form["uiic_cp_documents"].data:
            upload_document(
                incoming,
                form,
                "uiic_cp_documents",
                "file_uiic_cp_documents",
                "uiic_cp_documents",
                "uiic_cp_documents",
            )
        db.session.commit()
        return redirect(url_for(".list_incoming"))

    return render_template("incoming_add.html", form=form, title="Add new incoming")


@reinsurance_bp.route("/incoming/<int:key>/edit", methods=["POST", "GET"])
@login_required
def edit_incoming(key):
    incoming = db.get_or_404(IncomingReinsuranceConfirmations, key)
    form = IncomingReinsuranceConfirmationForm(obj=incoming)
    if form.validate_on_submit():
        form.populate_obj(incoming)
        db.session.add(incoming)
        if form["leader_cp_documents"].data:
            upload_document(
                incoming,
                form,
                "leader_cp_documents",
                "file_leader_cp_documents",
                "leader_cp_documents",
                "leader_cp_documents",
            )
        if form["uiic_cp_documents"].data:
            upload_document(
                incoming,
                form,
                "uiic_cp_documents",
                "file_uiic_cp_documents",
                "uiic_cp_documents",
                "uiic_cp_documents",
            )
        db.session.commit()
        return redirect(url_for(".list_incoming"))

    return render_template("incoming_add.html", form=form, title="Add new incoming")


@reinsurance_bp.route("/incoming/")
@login_required
def list_incoming():
    incoming = db.session.scalars(
        db.select(IncomingReinsuranceConfirmations)
    )  # .query.all()
    column_names = IncomingReinsuranceConfirmations.query.statement.columns.keys()

    return render_template(
        "incoming_list.html", incoming=incoming, column_names=column_names
    )


@reinsurance_bp.route("/outgoing/add", methods=["POST", "GET"])
@login_required
def add_outgoing():
    form = OutgoingReinsuranceConfirmationForm()
    if form.validate_on_submit():
        outgoing = OutgoingReinsuranceConfirmations()
        form.populate_obj(outgoing)
        db.session.add(outgoing)
        db.session.commit()
    #        return redirect(url_for("reinsurance.list_incoming"))

    return render_template("outgoing_add.html", form=form, title="Add new incoming")


@reinsurance_bp.route("/outgoing/")
@login_required
def list_outgoing():
    outgoing = db.session.scalars(
        db.select(OutgoingReinsuranceConfirmations)
    )  # .query.all()
    return render_template("outgoing_list.html", outgoing=outgoing)


@reinsurance_bp.route("/split_pdf", methods=["GET", "POST"])
def ri_page():
    form = UploadFileForm()
    if form.validate_on_submit():
        line_number = form.line_number.data
        if form.file_process_option.data == "export_excel":
            excel_file = extract_tables_to_excel(form.file_upload.data, line_number)
            output = BytesIO()
            excel_file.to_excel(output, index=False)

            # Set the buffer position to the beginning
            output.seek(0)

            filename = f"excel_export_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"

            return send_file(output, as_attachment=True, download_name=filename)
        elif form.file_process_option.data == "split":
            zip_buffer = split_pdf_by_broker_name(form.file_upload.data, line_number)
            zip_buffer.seek(0)
            return send_file(
                zip_buffer,
                mimetype="application/zip",
                as_attachment=True,
                download_name="split_pdfs.zip",
            )

    return render_template("ri_page.html", form=form)


def sanitize_filename(filename):
    """Remove invalid characters from filename."""
    return re.sub(r'[\/:*?"<>|]', "_", filename)


def extract_tables_to_excel(pdf_path, line_number):
    all_tables = []  # Store all tables from the PDF

    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages):
            tables = page.extract_tables()  # Extract tables from the page
            text_lines = page.extract_text().split("\n") if page.extract_text() else []
            ninth_line = (
                text_lines[line_number] if len(text_lines) >= line_number else "N/A"
            )  # Get ninth line safely

            for table in tables:
                df = pd.DataFrame(
                    table, columns=["Description", "data"]
                )  # Convert table to DataFrame
                df = df.T  # transpose the dataframe
                df.columns = df.iloc[0]  # make the first row as column
                df = df[1:]  # delete the first row
                df["Source Page"] = page_number + 1  # Add column to track source page
                df["broker/reinsurer"] = ninth_line
                all_tables.append(df)

    if all_tables:
        combined_df = pd.concat(all_tables, ignore_index=True)  # Combine all tables

    return combined_df


def split_pdf_by_broker_name(input_pdf_stream, line_number):
    broker_writers = {}

    # Read uploaded PDF into memory

    reader = PdfReader(input_pdf_stream)

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            lines = text.split("\n")
            if len(lines) >= line_number:
                broker_line = sanitize_filename(lines[line_number].strip())
            else:
                broker_line = f"page_{i}"
        else:
            broker_line = f"page_{i}"

        if broker_line not in broker_writers:
            broker_writers[broker_line] = PdfWriter()
        broker_writers[broker_line].add_page(page)

    # Create a zip in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for broker, writer in broker_writers.items():
            pdf_bytes = BytesIO()
            writer.write(pdf_bytes)
            pdf_bytes.seek(0)
            zipf.writestr(f"{broker}.pdf", pdf_bytes.read())
    return zip_buffer
