from datetime import datetime
from io import BytesIO
import re
import zipfile

import pandas as pd
import pdfplumber
from pypdf import PdfReader, PdfWriter

from flask import render_template, send_file

from app.ri_page import ri_page_bp
from .forms import UploadFileForm


@ri_page_bp.route("/", methods=["GET", "POST"])
def ri_page():
    form = UploadFileForm()
    if form.validate_on_submit():
        if form.file_process_option.data == "export_excel":
            excel_file = extract_tables_to_excel(form.file_upload.data)
            output = BytesIO()
            excel_file.to_excel(output, index=False)

            # Set the buffer position to the beginning
            output.seek(0)

            filename = f"excel_export_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"

            return send_file(output, as_attachment=True, download_name=filename)
        elif form.file_process_option.data == "split":
            zip_buffer = split_pdf_by_broker_name(form.file_upload.data)
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


def extract_tables_to_excel(pdf_path):
    all_tables = []  # Store all tables from the PDF

    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages):
            tables = page.extract_tables()  # Extract tables from the page
            text_lines = page.extract_text().split("\n") if page.extract_text() else []
            ninth_line = (
                text_lines[5] if len(text_lines) >= 9 else "N/A"
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


def split_pdf_by_broker_name(input_pdf_stream):
    broker_writers = {}

    # Read uploaded PDF into memory

    reader = PdfReader(input_pdf_stream)

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            lines = text.split("\n")
            if len(lines) >= 9:
                broker_line = sanitize_filename(lines[8].strip())
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
