from random import randint

import pandas as pd
from flask import abort, current_app, flash, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app.portal_admin import admin_bp
from app.portal_admin.admin_forms import UpdateUserForm, UserAddForm
from app.users.user_model import LogUser, User

from extensions import db
from set_view_permissions import admin_required


@admin_bp.route("/user/upload/", methods=["POST", "GET"])
@admin_required
def upload_users():
    if request.method == "POST":
        upload_file = request.files.get("file")
        df_user_upload_chunk = pd.read_csv(
            upload_file,
            chunksize=100,
            dtype={
                "ro_code": str,
                "oo_code": str,
                "username": str,
            },
        )
        password_hash = generate_password_hash("united")

        for df_user_upload in df_user_upload_chunk:
            df_user_upload["password"] = password_hash
            df_user_upload["reset_password"] = True
            engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))

            try:
                df_user_upload.to_sql("user", engine, if_exists="append", index=False)
                flash("User details have been uploaded to database.")
            except IntegrityError:
                flash("Upload unique username only.")

    return render_template("upload.html")


@admin_bp.route("/user/<int:user_key>/", methods=["POST", "GET"])
@login_required
def view_user_page(user_key):
    user = User.query.get_or_404(user_key)
    form = UpdateUserForm(obj=user)
    if current_user.user_type == "ro_user" and (
        user.user_type != "oo_user" or user.ro_code != current_user.ro_code
    ):
        abort(404)
    user_log = db.session.query(LogUser).filter(LogUser.user_id == user.username)

    if form.validate_on_submit():
        form.populate_obj(user)
        if form.data["reset_password"]:
            password_string = f"Welcome{str(randint(1, 1000))}"
            user.password = generate_password_hash(password_string)

            flash(f"New password generated: {password_string}")

        db.session.commit()
        admin_check()

    return render_template(
        "user_page.html",
        user=user,
        form=form,
        user_log=user_log,
    )


@admin_bp.route("/home")
@login_required
def view_list_users():
    users = User.query.order_by(User.user_type)
    if current_user.user_type == "ro_user":
        users = users.filter(
            (User.ro_code == current_user.ro_code) & (User.user_type == "oo_user")
        )
    return render_template(
        "view_all_users.html",
        users=users,
    )


@admin_bp.route("/user/add", methods=["POST", "GET"])
@admin_required
def user_add():
    form = UserAddForm()
    if form.validate_on_submit():
        password_hash = generate_password_hash("united")
        user = User(password=password_hash, reset_password=True)
        form.populate_obj(user)
        db.session.add(user)
        db.session.commit()
        flash("User has been added.")
    return render_template("user_add.html", form=form)


def admin_check():
    admin = db.session.query(User).filter(User.user_type == "admin").first()
    if not admin:
        user = User(
            username="cfac_admin",
            password=generate_password_hash("cfac_admin"),
            user_type="admin",
            reset_password=True,
        )

        db.session.add(user)
        db.session.commit()
