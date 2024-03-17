from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import (
    RadioField,
    SelectField,
    StringField,
)
from wtforms.validators import DataRequired

topic_list: list[str] = [
    "Coinsurance",
    "GST",
    "TDS",
    "POS",
    "BBPS",
    "Asset module",
    "Foreign Remittance",
    "General",
    "E-formats",
    "BAP",
    "NEFT portal",
    "FCS",
    "ERF",
    "Payment gateway",
    "Payments",
    "Receipts",
    "BRS",
    "Centralised Cheques",
    "Penny drop",
    "Miscellaneous",
    "Lien",
    "Foreign payments",
    "Employee advances",
    "Public disclosures",
    "CFAC portal",
]

topic_list.sort()


class KnowledgeBaseForm(FlaskForm):
    topic = SelectField("Topic", choices=topic_list, validators=[DataRequired()])
    title = StringField("Title", validators=[DataRequired()])
    knowledge_base_document = FileField("Upload document", validators=[DataRequired()])
    is_visible = RadioField(
        "To be accessed by",
        choices=[(False, "Head Office"), (True, "Everyone")],
        default=False,
        validators=[DataRequired()],
    )
    status = RadioField(
        "Current status",
        choices=[(True, "Relevant"), (False, "No longer relevant")],
        default=True,
        validators=[DataRequired()],
    )
