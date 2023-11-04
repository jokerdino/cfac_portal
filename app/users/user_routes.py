# from flask import render_template

from datetime import datetime

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash

from app.users import user_bp
from app.users.user_forms import LoginForm, ResetPasswordForm, SignupForm
from app.users.user_model import Log_user, User


# @user_bp.route('/signup', methods = ['POST','GET'])
def signup():
    from extensions import db

    form = SignupForm()

    #    if request.method == "GET":
    #        return render_template("signup.html", form=form)
    if request.method == "POST":
        username = form.data["username"]
        password = form.data["password"]
        password_hash = generate_password_hash(password)

        # emp_number = form.data["emp_number"]

        user = User.query.filter(
            or_(User.oo_code == username)  # , User.emp_number == emp_number)
        ).first()
        if user:
            flash("Username or employee number already exists.")
            # return redirect(url_for("signup"))

        else:
            # add employee number to employee database if employee number does not exist
            #  employee = Employee.query.filter(Employee.emp_number == emp_number).first()
            # if not employee:
            #    print("employee number does not exist")
            #   new_employee = Employee(name=username, emp_number=emp_number)
            #  db.session.add(new_employee)
            user = User(
                oo_code=username, password=password_hash
            )  # , emp_number=emp_number
            # )
            db.session.add(user)
            # user_views.admin_check()
            db.session.commit()

            return redirect(url_for("users.login_page"))
    return render_template("signup.html", form=form)


@user_bp.route("/login", methods=["POST", "GET"])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()

    from extensions import db

    if form.validate_on_submit():
        username = form.data["username"].lower()
        user = db.session.query(User).filter(User.oo_code == username).first()
        if user is not None:
            password = form.data["password"]

            if check_password_hash(user.password, password):
                login_user(user)
                user.time_last_login = datetime.now()
                db.session.commit()
                logger_user_actions(username, "Logged in", datetime.now())
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
def logout_page():
    logger_user_actions(current_user.oo_code, "Logged out", datetime.now())
    logout_user()

    # flash("You have logged out.")
    return redirect(url_for("users.login_page"))


@user_bp.route("/reset_password", methods=["POST", "GET"])
def reset_password_page():
    #    pass
    form = ResetPasswordForm()
    from extensions import db

    #  form = SignupForm()
    #    if request.method == "GET":
    #        return render_template("reset_password.html", form=form)
    if form.validate_on_submit():
        #        username = form.data["username"]
        #        emp_number = form.data["emp_number"]

        user = User.query.filter(
            User.oo_code
            == current_user.oo_code  # username #, User.emp_number == emp_number
        ).first()
        #        if user:
        if current_user.reset_password:
            # password = form.data["password"]
            # password_hash =
            user.password = generate_password_hash(
                form.data["password"]
            )  # password_hash
            user.reset_password = False
            db.session.add(user)
            db.session.commit()
            logger_user_actions(current_user.oo_code, "Password reset", datetime.now())
            return redirect(url_for("main.index"))
        else:
            flash("Password reset page is not enabled for this user. Contact admin.")
            # return redirect(url_for("signup"))

    # else:
    #    flash("Username or employee number does not exist.")
    return render_template("reset_password.html", form=form)


def logger_user_actions(user_id, type_of_action, time):
    from extensions import db

    log = Log_user(user_id=user_id, type_of_action=type_of_action, time_of_action=time)
    db.session.add(log)
    db.session.commit()
    # db.session.add()
