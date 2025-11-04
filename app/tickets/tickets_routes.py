from flask import redirect, render_template, url_for, send_file
from flask_login import current_user, login_required

from sqlalchemy import case, func

from . import tickets_bp
from .tickets_model import Tickets, TicketRemarks
from .tickets_form import TicketsForm, TicketFilterForm, TicketDashboardForm

from set_view_permissions import admin_required
from extensions import db


@tickets_bp.route("/add", methods=["POST", "GET"])
@login_required
def add_ticket():
    form = TicketsForm()

    if current_user.user_type == "oo_user":
        form.regional_office_code.data = current_user.ro_code
        form.office_code.data = current_user.oo_code
    elif current_user.user_type == "ro_user":
        form.regional_office_code.data = current_user.ro_code
    elif current_user.user_type == "coinsurance_hub_user":
        form.regional_office_code.data = current_user.oo_code
        form.office_code.data = current_user.oo_code

    if form.validate_on_submit():
        ticket = Tickets()
        form.populate_obj(ticket)

        if form.data["initial_remarks"]:
            ticket.remarks.append(
                TicketRemarks(
                    remarks=form.data["initial_remarks"],
                )
            )

        db.session.add(ticket)
        db.session.commit()

        return redirect(url_for("tickets.view_ticket", ticket_id=ticket.id))

    return render_template("add_ticket.html", form=form, title="Enter ticket details")


@tickets_bp.route("/view/<int:ticket_id>/")
@login_required
def view_ticket(ticket_id):
    ticket = db.get_or_404(Tickets, ticket_id)

    return render_template(
        "view_ticket.html",
        ticket=ticket,
    )


@tickets_bp.route("/edit/<int:ticket_id>/", methods=["POST", "GET"])
@login_required
def edit_ticket(ticket_id):
    ticket = db.get_or_404(Tickets, ticket_id)

    form = TicketsForm(obj=ticket)

    if current_user.user_type == "admin":
        form.regional_incharge_approval.data = "True"
    if form.validate_on_submit():
        form.populate_obj(ticket)

        if form.data["initial_remarks"]:
            ticket.remarks.append(
                TicketRemarks(
                    remarks=form.data["initial_remarks"],
                )
            )

        db.session.commit()
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket.id))

    return render_template(
        "add_ticket.html",
        form=form,
        title="Edit ticket details",
        ticket=ticket,
    )


@tickets_bp.route("/status/<string:status>/", methods=["GET", "POST"])
@login_required
def filter_by_status(status):
    form = TicketFilterForm()

    tickets = db.select(Tickets)
    if status != "all":
        tickets = tickets.where(Tickets.status == status)

    if current_user.user_type in ["oo_user", "coinsurance_hub_user"]:
        tickets = tickets.where(Tickets.office_code == current_user.oo_code)
    elif current_user.user_type == "ro_user":
        tickets = tickets.where(Tickets.regional_office_code == current_user.ro_code)

    select_department(tickets, form)

    if form.validate_on_submit():
        department = form.data["department"]
        if department != "View all":
            tickets = tickets.where(Tickets.department == department)

    result = db.session.scalars(tickets)
    return render_template(
        "tickets_homepage.html",
        tickets=result,
        form=form,
    )


def select_department(stmt, form):
    subq = stmt.subquery()

    department_list = db.session.scalars(
        db.select(db.distinct(subq.c.department)).order_by(subq.c.department)
    ).all()

    form.department.choices = ["View all"] + department_list


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
    form = TicketDashboardForm()

    tickets_department = db.session.scalars(
        db.select(Tickets.department).distinct().order_by(Tickets.department)
    ).all()

    case_department = {
        k: case((Tickets.department == k, Tickets.department))
        for k in tickets_department
    }

    entities_list = [func.count(case_department[i]) for i in tickets_department]

    status = "Pending for CFAC approval"
    stmt = (
        db.select(
            Tickets.regional_office_code, *entities_list, func.count(Tickets.department)
        )
        .group_by(Tickets.regional_office_code)
        .order_by(Tickets.regional_office_code)
    )
    stmt_total = db.select(*entities_list, func.count(Tickets.department))

    if form.validate_on_submit():
        status = form.status.data
    if status != "View all":
        stmt = stmt.where(Tickets.status == status)
        stmt_total = stmt_total.where(Tickets.status == status)

    tickets = db.session.execute(stmt)
    tickets_total = db.session.execute(stmt_total)

    return render_template(
        "tickets_dashboard.html",
        form=form,
        tickets=tickets,
        tickets_total=tickets_total,
        tickets_department=tickets_department,
    )
