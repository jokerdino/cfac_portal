from datetime import datetime

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash

from . import user_bp
from .user_forms import LoginForm, ResetPasswordForm, SignupForm
from .user_model import LogUser, User

from extensions import db


# @user_bp.route('/signup', methods = ['POST','GET'])
def signup():
    form = SignupForm()

    if form.validate_on_submit():
        user = db.session.scalar(
            db.select(User).where(User.username == form.data["username"])
        )
        if user:
            flash("Username or employee number already exists.")
        else:
            username = form.data["username"]
            password = form.data["password"]
            password_hash = generate_password_hash(password)

            user = User(username=username, password=password_hash)

            db.session.add(user)
            db.session.commit()

            return redirect(url_for("users.login_page"))
    return render_template("signup.html", form=form)


@user_bp.route("/login", methods=["POST", "GET"])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()

    if form.validate_on_submit():
        username = form.data["username"]
        user = db.session.scalar(db.select(User).where(User.username == username))
        if user is not None:
            password = form.data["password"]

            if check_password_hash(user.password, password):
                login_user(user)
                user.time_last_login = datetime.now()
                db.session.commit()
                logger_user_actions(
                    user_id=current_user.username,
                    type_of_action="Logged in",
                    time_of_action=datetime.now(),
                )
                if user.reset_password:
                    return redirect(url_for("users.reset_password_page"))

                next_page = request.args.get("next", url_for("main.index"))
                return redirect(next_page)
            else:
                flash("Invalid credentials.")
        else:
            flash("Invalid credentials.")
    return render_template("login.html", form=form)


@user_bp.route("/logout", methods=["POST", "GET"])
@login_required
def logout_page():
    if current_user.is_authenticated:
        logger_user_actions(
            user_id=current_user.username,
            type_of_action="Logged out",
            time_of_action=datetime.now(),
        )
    logout_user()

    return redirect(url_for("users.login_page"))


@user_bp.route("/reset_password", methods=["POST", "GET"])
@login_required
def reset_password_page():
    form = ResetPasswordForm()

    if form.validate_on_submit():
        user = db.session.scalar(
            db.select(User).where(User.username == current_user.username)
        )

        if current_user.reset_password:
            user.password = generate_password_hash(form.data["password"])
            user.reset_password = False

            db.session.commit()
            logger_user_actions(
                user_id=current_user.username,
                type_of_action="Password reset",
                time_of_action=datetime.now(),
            )
            return redirect(url_for("main.index"))
        else:
            flash("Password reset page is not enabled for this user. Contact admin.")
    return render_template("reset_password.html", form=form)


def logger_user_actions(**kwargs):
    log = LogUser(**kwargs)
    db.session.add(log)
    db.session.commit()
