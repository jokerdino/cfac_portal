from flask import flash, redirect, render_template, url_for, send_file
from flask_login import current_user, login_required

from sqlalchemy import case, func

from app.tickets import tickets_bp
from app.tickets.tickets_model import Tickets, TicketRemarks
from app.tickets.tickets_form import TicketsForm, TicketFilterForm, TicketDashboardForm

from set_view_permissions import admin_required


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
        ticket = Tickets()
        form.populate_obj(ticket)
        ticket.regional_office_code = regional_office_code
        ticket.office_code = office_code
        db.session.add(ticket)
        db.session.commit()

        if form.data["remarks"]:
            remarks = TicketRemarks(
                ticket_id=ticket.id,
                remarks=form.data["remarks"],
            )
            db.session.add(remarks)
            db.session.commit()

        return redirect(url_for("tickets.view_ticket", ticket_id=ticket.id))

    return render_template("add_ticket.html", form=form, title="Enter ticket details")


@tickets_bp.route("/view/<int:ticket_id>")
@login_required
def view_ticket(ticket_id):
    from extensions import db

    ticket = db.get_or_404(Tickets, ticket_id)

    remarks = TicketRemarks.query.filter(TicketRemarks.ticket_id == ticket_id)
    return render_template(
        "view_ticket.html",
        ticket=ticket,
        remarks=remarks,
    )


@tickets_bp.route("/edit/<int:ticket_id>", methods=["POST", "GET"])
@login_required
def edit_ticket(ticket_id):

    from extensions import db

    ticket = db.get_or_404(Tickets, ticket_id)

    remarks = TicketRemarks.query.filter(TicketRemarks.ticket_id == ticket_id)
    from server import db

    form = TicketsForm(obj=ticket)

    if current_user.user_type == "admin":
        form.regional_incharge_approval.data = "True"
    if form.validate_on_submit():
        form.populate_obj(ticket)
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
            ticket.office_code = current_user.oo_code

        if form.data["remarks"]:
            remark = TicketRemarks(
                ticket_id=ticket.id,
                remarks=form.data["remarks"],
            )
            db.session.add(remark)
        db.session.commit()
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket.id))

    return render_template(
        "add_ticket.html",
        form=form,
        title="Edit ticket details",
        remarks=remarks,
    )


@tickets_bp.route("/status/all/<string:department>/", methods=["POST", "GET"])
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

    form.department.data = department
    return render_template(
        "tickets_homepage.html",
        tickets=tickets,
        form=form,
    )


@tickets_bp.route(
    "/status/<string:status>/<string:department>", methods=["GET", "POST"]
)
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
        return redirect(
            url_for("tickets.filter_by_status", status=status, department=department)
        )

    form.department.data = department
    return render_template(
        "tickets_homepage.html",
        tickets=tickets,
        form=form,
    )


def select_department(query, form):
    department = query.distinct(Tickets.department)
    form.department.choices = ["View all"] + [x.department for x in department]


@tickets_bp.route("/download_jv_format/<string:requirement>")
@login_required
def download_jv_format(requirement):
    if requirement == "premium":
        return send_file("download_formats/jv_format_premium.xlsx")
    elif requirement == "bulk":
        return send_file("download_formats/jv_bulk_jv_format.xlsx")
    else:
        return None


@tickets_bp.route("/dashboard/", methods=["POST", "GET"])
@login_required
@admin_required
def tickets_dashboard():
    from extensions import db

    form = TicketDashboardForm()

    tickets_department_query = (
        db.session.query(Tickets.department).distinct().order_by(Tickets.department)
    )

    tickets_department = [item[0] for item in tickets_department_query]

    case_department = {
        k: case((Tickets.department == v, Tickets.department))
        for (k, v) in zip(tickets_department, tickets_department)
    }

    entities_list = [func.count(case_department[i]) for i in tickets_department]

    status = "Pending for CFAC approval"
    tickets = (
        db.session.query(Tickets)
        .with_entities(
            Tickets.regional_office_code, *entities_list, func.count(Tickets.department)
        )
        .group_by(Tickets.regional_office_code)
        .order_by(Tickets.regional_office_code)
    )
    tickets_total = db.session.query(Tickets).with_entities(
        *entities_list, func.count(Tickets.department)
    )
    if form.validate_on_submit():

        status = form.status.data
    if status != "View all":
        tickets = tickets.filter(Tickets.status == status)
        tickets_total = tickets_total.filter(Tickets.status == status)

    return render_template(
        "tickets_dashboard.html",
        form=form,
        tickets=tickets,
        tickets_total=tickets_total,
        tickets_department=tickets_department,
    )
