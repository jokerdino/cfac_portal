from datetime import datetime

import humanize

from flask import flash, redirect, render_template, url_for, send_file
from flask_login import current_user, login_required

from app.tickets import tickets_bp
from app.tickets.tickets_model import Tickets, TicketRemarks
from app.tickets.tickets_form import TicketsForm, TicketFilterForm


@tickets_bp.route("/add", methods=["POST", "GET"])
@login_required
def add_ticket():
    from server import db

    form = TicketsForm()
    if form.validate_on_submit():
        if current_user.user_type == "oo_user":
            regional_office_code = current_user.ro_code
            office_code = current_user.oo_code
        elif current_user.user_type == "ro_user":
            regional_office_code = current_user.ro_code
            office_code = form.data["office_code"]
        elif current_user.user_type == "coinsurance_hub_user":
            regional_office_code = current_user.oo_code
            office_code = current_user.oo_code
        elif current_user.user_type == "admin":
            regional_office_code = form.data["regional_office_code"]
            office_code = form.data["office_code"]
        ticket = Tickets(
            regional_office_code=regional_office_code,
            office_code=office_code,
            ticket_number=form.data["ticket_number"],
            contact_person=form.data["contact_person"],
            contact_email_address=form.data["contact_email_address"],
            contact_mobile_number=form.data["contact_mobile_number"],
            # remarks=form.data["remarks"],
            department=form.data["department"],
            status="Pending for CFAC approval",
            date_of_creation=datetime.now(),
        )
        db.session.add(ticket)
        db.session.commit()

        if form.data["remarks"]:
            remarks = TicketRemarks(
                ticket_id=ticket.id,
                user=current_user.username,
                remarks=form.data["remarks"],
                time_of_remark=datetime.now(),
            )
            db.session.add(remarks)
            db.session.commit()

        return redirect(url_for("tickets.view_ticket", ticket_id=ticket.id))

    return render_template("add_ticket.html", form=form, title="Enter ticket details")


@tickets_bp.route("/view/<int:ticket_id>")
@login_required
def view_ticket(ticket_id):
    ticket = Tickets.query.get_or_404(ticket_id)
    remarks = TicketRemarks.query.filter(TicketRemarks.ticket_id == ticket_id)
    return render_template(
        "view_ticket.html",
        ticket=ticket,
        remarks=remarks,
        humanize_datetime=humanize_datetime,
    )


@tickets_bp.route("/edit/<int:ticket_id>", methods=["POST", "GET"])
@login_required
def edit_ticket(ticket_id):
    ticket = Tickets.query.get_or_404(ticket_id)
    remarks = TicketRemarks.query.filter(TicketRemarks.ticket_id == ticket_id)
    from server import db

    form = TicketsForm()

    if current_user.user_type == "admin":
        form.regional_incharge_approval.data = "True"
    if form.validate_on_submit():
        if current_user.user_type == "admin":
            ticket.regional_office_code = form.data["regional_office_code"]
            ticket.office_code = form.data["office_code"]
        elif current_user.user_type == "ro_user":
            ticket.regional_office_code = current_user.ro_code
            ticket.office_code = form.data["office_code"]
        elif current_user.user_type == "oo_user":
            ticket.regional_office_code = current_user.ro_code
            ticket.office_code = current_user.oo_code
        elif current_user.user_type == "coinsurance_hub_user":
            ticket.regional_office_code = current_user.oo_code
            ticket.regional_office_code = current_user.oo_code
        ticket.ticket_number = form.data["ticket_number"]
        ticket.contact_person = form.data["contact_person"]
        ticket.contact_email_address = form.data["contact_email_address"]
        ticket.contact_mobile_number = form.data["contact_mobile_number"]
        ticket.department = form.data["department"]
        # ticket.remarks = form.data["remarks"]

        ticket.status = form.data["status"]
        if form.data["remarks"]:
            remark = TicketRemarks(
                ticket_id=ticket.id,
                remarks=form.data["remarks"],
                time_of_remark=datetime.now(),
                user=current_user.username,
            )
            db.session.add(remark)
        db.session.commit()
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket.id))
    form.regional_office_code.data = ticket.regional_office_code
    form.office_code.data = ticket.office_code
    form.ticket_number.data = ticket.ticket_number
    form.contact_person.data = ticket.contact_person
    form.contact_email_address.data = ticket.contact_email_address
    form.contact_mobile_number.data = ticket.contact_mobile_number
    form.department.data = ticket.department
    form.status.data = ticket.status
    # form.remarks.data = ticket.remarks

    return render_template(
        "add_ticket.html",
        form=form,
        title="Edit ticket details",
        remarks=remarks,
        humanize_datetime=humanize_datetime,
    )


@tickets_bp.route("/status/all/<string:department>", methods=["POST","GET"])
@login_required
def tickets_homepage(department):
    form = TicketFilterForm()

    tickets = Tickets.query.order_by(Tickets.department)

    if current_user.user_type in ["oo_user", "coinsurance_hub_user"]:
        tickets = tickets.filter(Tickets.office_code == current_user.oo_code)
    elif current_user.user_type == "ro_user":
        tickets = tickets.filter(Tickets.regional_office_code == current_user.ro_code)

    select_department(tickets, form)
    if department != "View all":
        tickets = tickets.filter(Tickets.department == department)

    if form.validate_on_submit():
        department = form.data["department"]
        return redirect(url_for("tickets.tickets_homepage", department=department))

    return render_template(
        "tickets_homepage.html", tickets=tickets, humanize_datetime=humanize_datetime, form=form
    )


@tickets_bp.route("/status/<string:status>/<string:department>", methods=["GET", "POST"])
@login_required
def filter_by_status(status, department):
    form = TicketFilterForm()

    tickets = Tickets.query.filter(Tickets.status == status)

    if current_user.user_type in ["oo_user", "coinsurance_hub_user"]:
        tickets = tickets.filter(Tickets.office_code == current_user.oo_code)
    elif current_user.user_type == "ro_user":
        tickets = tickets.filter(Tickets.regional_office_code == current_user.ro_code)

    select_department(tickets, form)
    if department != "View all":
        tickets = tickets.filter(Tickets.department == department)

    if form.validate_on_submit():
        department = form.data["department"]
        return redirect(url_for("tickets.filter_by_status", status=status, department=department))

    return render_template(
        "tickets_homepage.html", tickets=tickets, humanize_datetime=humanize_datetime, form=form
    )


def humanize_datetime(input_datetime):
    return humanize.naturaltime(datetime.now() - input_datetime)


def select_department(query, form):
    department = query.distinct(Tickets.department)
    form.department.choices = ["View all"] + [
        x.department for x in department
    ]


@tickets_bp.route("/download_jv_format/<string:requirement>")
@login_required
def download_jv_format(requirement):
    if requirement == "premium":
        return send_file("jv_format_premium.xlsx")
    elif requirement == "bulk":
        return send_file("jv_bulk_jv_format.xlsx")
    else:
        return None
