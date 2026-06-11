from collections import defaultdict

import click
from flask import current_app, render_template
from flask.cli import with_appcontext

from extensions import db
from app.users.mail_utils import send_email_async
from app.contacts.contacts_model import Contacts
from app.direct_debits.model import RegionalManagerEmailAddress

from .lien_model import Lien
from .lien_routes import sanitize_status


def prepare_ro_lien_list():
    ro_wise_details = (
        db.select(
            Lien.ro_code,
            Lien.ro_name,
            Lien.bank_name,
            Lien.account_number,
            Lien.lien_status,
            Lien.lien_amount,
            Lien.lien_date,
        )
        .where(Lien.lien_status == "Lien exists")
        .order_by(Lien.ro_code, Lien.lien_date)
    )

    return ro_wise_details


def prepare_ho_tp_lien_data():
    query = db.select(Lien).where(Lien.lien_status == "Lien exists")
    ROUND_OFF = 100_000

    subq = query.subquery()
    bank_names = db.session.scalars(
        db.select(db.distinct(subq.c.bank_name)).order_by(subq.c.bank_name)
    ).all()

    bank_columns = []
    bank_labels = {}  # mapping from original -> sanitized
    for bank in bank_names:
        safe_bank = sanitize_status(bank)
        bank_labels[bank] = safe_bank

        col_count = db.func.sum(db.case((subq.c.bank_name == bank, 1), else_=0)).label(
            f"count_{safe_bank}"
        )

        col_sum = (
            db.func.sum(
                db.case((subq.c.bank_name == bank, subq.c.lien_amount), else_=0)
            )
            / ROUND_OFF
        ).label(f"sum_{safe_bank}")
        bank_columns.extend([col_count, col_sum])

    report_query = (
        db.select(
            subq.c.ro_code,
            subq.c.ro_name,
            *bank_columns,
            db.func.count(subq.c.id).label("total_count"),
            (db.func.sum(subq.c.lien_amount) / ROUND_OFF).label("total_amount"),
        )
        .group_by(subq.c.ro_name, subq.c.ro_code)
        .order_by(subq.c.ro_code)
    )
    lien_data = db.session.execute(report_query).all()

    return lien_data, bank_names, bank_labels


def fetch_recipient_email_addresses(ro_code: str) -> list[str]:
    regional_accountants = db.session.scalars(
        db.select(Contacts.email_address).where(
            Contacts.office_code == ro_code,
            Contacts.role.in_(
                [
                    "Regional Accountant",
                    "Second Officer",
                ]
            ),
        )
    ).all()
    regional_managers = db.session.scalars(
        db.select(RegionalManagerEmailAddress.email_address).where(
            RegionalManagerEmailAddress.office_code == ro_code
        )
    ).all()

    recipients = regional_accountants + regional_managers
    return recipients


@click.command("send_ro_lien_emails")
@with_appcontext
def send_ro_lien_emails():
    """Send weekly lien reminder emails to each RO."""
    app = current_app._get_current_object()
    with app.test_request_context():
        lien_list = db.session.execute(prepare_ro_lien_list()).all()

        grouped = defaultdict(list)
        for row in lien_list:
            grouped[row.ro_code].append(row)

        for ro_code, rows in grouped.items():
            recipients = fetch_recipient_email_addresses(ro_code)

            if not recipients:
                continue

            html_body = render_template("lien_ro_email_template.html", lien_list=rows)
            subject = f"RO {ro_code}: Active Liens Across All Banks"

            send_email_async(
                app=app,
                subject=subject,
                recipients=recipients,
                cc=[
                    "gaddamjanakiram@uiic.co.in",
                    "pjagadeeswar@uiic.co.in",
                    "simranbijpuria@uiic.co.in",
                ],
                bcc=["44515"],
                body="Please view this email in HTML.",
                html=html_body,
            )


@click.command("send_ho_tp_lien_email")
@with_appcontext
def send_ho_tp_lien_email():
    app = current_app._get_current_object()
    with app.test_request_context():
        lien_list, bank_names, bank_labels = prepare_ho_tp_lien_data()

        html_body = render_template(
            "lien_ho_tp_email_template.html",
            lien_data=lien_list,
            bank_names=bank_names,
            bank_labels=bank_labels,
        )
        subject = "Active Liens Across All Banks - RO Wise Summary"
        ho_motor_tp_officers = ["hotp@uiic.co.in"]
        send_email_async(
            app=app,
            subject=subject,
            recipients=ho_motor_tp_officers,
            cc=[
                "jaishreenair@uiic.co.in",
                "shemamalini@uiic.co.in",
                "pnarun@uiic.co.in",
                "apusha@uiic.co.in",
                "gaddamjanakiram@uiic.co.in",
                "pjagadeeswar@uiic.co.in",
                "simranbijpuria@uiic.co.in",
            ],
            bcc=["44515"],
            body="Please view this email in HTML.",
            html=html_body,
        )
