from collections import defaultdict

import click
from flask import current_app, render_template
from flask.cli import with_appcontext

from extensions import db
from app.users.mail_utils import send_email_async
from app.contacts.contacts_model import Contacts

from .model import DirectDebit, Status, RegionalManagerEmailAddress


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


@click.command("send_dd_emails")
@with_appcontext
def send_dd_emails():
    """Send weekly direct debit reminder emails to each RO."""
    app = current_app._get_current_object()
    with app.test_request_context():
        dd_list = db.session.execute(
            db.select(
                DirectDebit.ro_code,
                DirectDebit.ro_name,
                DirectDebit.transaction_date,
                DirectDebit.particulars,
                DirectDebit.debit,
                (db.func.current_date() - DirectDebit.transaction_date).label(
                    "no_of_days_pending"
                ),
            )
            .where(
                DirectDebit.status == Status.DEBITED,
                DirectDebit.ro_jv_number.is_(None),
            )
            .order_by(DirectDebit.ro_code, DirectDebit.transaction_date)
        ).all()

        grouped = defaultdict(list)
        for row in dd_list:
            grouped[row.ro_code].append(row)

        for ro_code, rows in grouped.items():
            recipients = fetch_recipient_email_addresses(ro_code)
            if not recipients:
                continue

            html_body = render_template("dd_email_template.html", dd_list=rows)
            subject = f"RO {ro_code}: DD debit details not yet updated in CFAC portal"

            send_email_async(
                app=app,
                subject=subject,
                recipients=recipients,
                cc=["27629", "28156", "60455"],
                bcc=["44515"],
                body="Please view this email in HTML.",
                html=html_body,
            )

    return "Success"
