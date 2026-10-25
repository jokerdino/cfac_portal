from datetime import datetime

from flask import redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.users.user_model import User
from extensions import db
from set_view_permissions import admin_required

from . import todo_bp
from .forms import TaskForm
from .models import Notification, Task


@todo_bp.route("/", methods=["GET", "POST"])
@login_required
@admin_required
def index():
    task_list = (
        db.select(
            Task,
            User.display_name,
        )
        .outerjoin(User, User.id == Task.assigned_to_id)
        .order_by(Task.priority.asc(), Task.created_on.desc())
    )
    tasks = db.session.execute(task_list).mappings().all()

    return render_template("task_index.html", tasks=tasks)


@todo_bp.route("/add", methods=["GET", "POST"])
@login_required
@admin_required
def task_add():
    form = TaskForm()
    form = set_assignment_choices(form)
    form = set_subscriber_choices(form)

    if form.validate_on_submit():
        task = Task()

        form.populate_obj(task)
        db.session.add(task)
        db.session.commit()
        assigned_user_id = task.assigned_to_id
        # flash("Task created!", "success")

        create_notification(
            assigned_user_id, f"You have been assigned a new task: {task.title}"
        )

        return redirect(url_for(".board"))

    return render_template("task_edit.html", form=form, title="Add Task")


@todo_bp.route("/edit/<int:id>/", methods=["GET", "POST"])
@login_required
@admin_required
def task_edit(id):
    task = db.get_or_404(Task, id)

    form = TaskForm(obj=task)
    form = set_assignment_choices(form)
    form = set_subscriber_choices(form)

    if form.validate_on_submit():
        old_assigned_user_id = task.assigned_to_id
        form.populate_obj(task)
        db.session.commit()

        if task.assigned_to_id != old_assigned_user_id:
            assigned_user_id = task.assigned_to_id

            create_notification(
                assigned_user_id, f"You have been assigned a new task: {task.title}"
            )

        return redirect(url_for(".board"))

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template(
            "partials/task_edit.html",
            form=form,
            task=task,
            action_url=url_for("todo.task_edit", id=id),
        )

    return render_template("task_edit.html", form=form, title="Edit Task")


@todo_bp.post("/delete/<int:id>/")
@login_required
@admin_required
def task_delete(id):
    task = db.get_or_404(Task, id)
    task.deleted_by = current_user.username
    task.deleted_on = datetime.now()

    db.session.commit()

    return redirect(url_for(".board"))


@todo_bp.post("/archive/<int:id>/")
@login_required
@admin_required
def task_archive(id):
    task = db.get_or_404(Task, id)
    task.is_archived = True
    task.archived_by = current_user.username

    db.session.commit()

    return redirect(url_for(".board"))


def set_assignment_choices(form):
    stmt = (
        db.select(User.display_name, User.id)
        .where(User.user_type == "admin", User.display_name.is_not(None))
        .order_by(User.display_name)
    )
    ho_staff = db.session.execute(stmt).all()

    form.assigned_to_id.choices = [(0, "-----")] + [
        (u.id, u.display_name) for u in ho_staff
    ]
    return form


def set_subscriber_choices(form):
    """Fetches Admin users and sets them as choices for the subscribers field."""

    # Use the SQLAlchemy session to execute the query
    stmt = (
        db.select(User.display_name, User.id)
        .where(User.user_type == "admin", User.display_name.is_not(None))
        .order_by(User.display_name)
    )
    query = db.session.execute(stmt).all()

    # The result returns (display_name, id). We need (id, display_name) for WTForms choices.
    # WTForms requires (value, label)

    choices = [(user_id, name) for name, user_id in query]

    # Set the choices on the form field
    form.subscribers.choices = choices

    return form


def create_notification(user_id: int, message: str):
    notif = Notification(user_id=user_id, message=message)
    db.session.add(notif)
    db.session.commit()


@todo_bp.get("/notifications/read/<int:id>/")
@login_required
@admin_required
def read(id):
    notif = db.session.get(Notification, id)
    notif.is_read = True
    db.session.commit()
    return redirect(request.referrer or url_for(".index"))


@todo_bp.get("/board")
@login_required
@admin_required
def board():
    form = TaskForm()
    form = set_assignment_choices(form)
    form = set_subscriber_choices(form)

    task_list = (
        db.select(
            Task,
            User.display_name,
        )
        .outerjoin(User, User.id == Task.assigned_to_id)
        .where(
            db.or_(
                Task.assigned_to_id == current_user.id,
                Task.created_by_id == current_user.id,
                Task.subscribers.any(current_user.id),
            ),
            db.or_(Task.is_archived.is_(False), Task.is_archived.is_(None)),
            Task.deleted_on.is_(None),
        )
        .order_by(Task.priority.desc(), Task.due_date.asc(), Task.created_on.asc())
    )
    tasks = db.session.execute(task_list).mappings().all()

    grouped = {
        "pending": [],
        "in-progress": [],
        "done": [],
    }

    for t in tasks:
        grouped[t.Task.status].append(t)

    return render_template("task_board.html", grouped=grouped, form=form)


@todo_bp.post("/change_status")
@login_required
@admin_required
def update_task_status():
    data = request.get_json()
    task = db.session.get(Task, data["task_id"])

    # 1. Update task status and commit
    old_status = task.status
    task.status = data["new_status"]
    db.session.commit()

    # Avoid notifying if the status didn't actually change
    if old_status == task.status:
        return {"success": True}

    # 2. Prepare the notification message
    message = f"Task '{task.title}' moved from {old_status.replace('-', ' ').title()} to {task.status.replace('-', ' ').title()}"

    # 3. Collect unique user IDs for notification
    users_to_notify = set()

    # Add Task Creator
    if task.created_by_id:
        users_to_notify.add(task.created_by_id)

    # Add Assigned User
    if task.assigned_to_id:
        users_to_notify.add(task.assigned_to_id)

    # Add Subscribers (Note: task.subscribers is already a list of ints)
    if task.subscribers:
        # Extend the set with all subscriber IDs
        users_to_notify.update(task.subscribers)

    # 4. Filter out the user who initiated the change (current_user)
    # This prevents the user moving the card from getting a redundant notification
    if current_user.is_authenticated:
        users_to_notify.discard(current_user.id)

    # 5. Bulk create notifications
    for user_id in users_to_notify:
        create_notification(user_id, message)

    return {"success": True}
