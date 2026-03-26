from collections import defaultdict
from io import BytesIO

import pandas as pd
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
        dd_list = db.session.execute(prepare_ro_dd_list()).all()

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
                cc=[
                    "gaddamjanakiram@uiic.co.in",
                    "pjagadeeswar@uiic.co.in",
                    "pavithram@uiic.co.in",
                    "samyakjain@uiic.co.in",
                ],
                bcc=["44515"],
                body="Please view this email in HTML.",
                html=html_body,
            )


@click.command("send_dd_email_to_ho_tp")
@with_appcontext
def send_dd_email_to_ho_tp():
    app = current_app._get_current_object()
    with app.test_request_context():
        dd_list = prepare_ho_tp_list()
        ro_wise_details = prepare_ro_dd_list()
        with db.engine.connect() as conn:
            df_ro_wise_details = pd.read_sql(ro_wise_details, conn)

        if not df_ro_wise_details.empty:
            output = BytesIO()
            df_ro_wise_details.to_excel(output, index=False)

            output.seek(0)
            filename = "pending_DD_debits_details.xlsx"

        html_body = render_template("dd_ho_tp_email_template.html", dd_list=dd_list)
        subject = "DD debit details not yet updated in CFAC portal"

        ho_motor_tp_officers = ["hotp@uiic.co.in"]
        send_email_async(
            app=app,
            subject=subject,
            recipients=ho_motor_tp_officers,
            cc=[
                "shemamalini@uiic.co.in",
                "pnarun@uiic.co.in",
                "gaddamjanakiram@uiic.co.in",
                "pjagadeeswar@uiic.co.in",
                "pavithram@uiic.co.in",
                "samyakjain@uiic.co.in",
            ],
            bcc=["44515"],
            body="Please view this email in HTML.",
            html=html_body,
            attachments=[
                {
                    "filename": filename,
                    "content": output.getvalue(),
                    "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                }
            ],
        )


def prepare_ro_dd_list():
    ro_wise_details = (
        db.select(
            DirectDebit.ro_code,
            DirectDebit.ro_name,
            DirectDebit.transaction_date,
            DirectDebit.particulars,
            DirectDebit.debit.label("amount"),
            (db.func.current_date() - DirectDebit.transaction_date).label(
                "no_of_days_pending"
            ),
        )
        .where(
            DirectDebit.status == Status.DEBITED,
            DirectDebit.ro_jv_number.is_(None),
        )
        .order_by(DirectDebit.ro_code, DirectDebit.transaction_date)
    )

    return ro_wise_details


def prepare_ho_tp_list() -> list:
    agg_query = (
        db.select(
            DirectDebit.ro_code,
            DirectDebit.ro_name,
            db.func.count(DirectDebit.id).label("count"),
            db.func.sum(DirectDebit.debit).label("total_amount"),
            db.func.min(db.func.current_date() - DirectDebit.transaction_date).label(
                "min_days"
            ),
            db.func.max(db.func.current_date() - DirectDebit.transaction_date).label(
                "max_days"
            ),
        )
        .where(
            DirectDebit.status == Status.DEBITED,
            DirectDebit.ro_jv_number.is_(None),
        )
        .group_by(
            DirectDebit.ro_code,
            DirectDebit.ro_name,
        )
    ).subquery()
    dd_list = db.session.execute(
        db.select(
            agg_query.c.ro_code,
            agg_query.c.ro_name,
            agg_query.c.count,
            agg_query.c.total_amount,
            db.case(
                (
                    agg_query.c.min_days == agg_query.c.max_days,
                    db.func.concat(
                        agg_query.c.min_days,
                        " days",
                    ),
                ),
                else_=(
                    db.func.concat(
                        agg_query.c.min_days, "-", agg_query.c.max_days, " days"
                    )
                ),
            ).label("pending_period"),
        )
        .select_from(agg_query)
        .order_by(agg_query.c.ro_code)
    ).all()

    return dd_list
