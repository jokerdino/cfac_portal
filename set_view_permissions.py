from functools import wraps

from flask import redirect, url_for
from flask_login import current_user


def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if current_user.user_type == "admin":
            return f(*args, **kwargs)
        else:
            # flash("You need to be an admin to view this page")
            return redirect(url_for("main.index"))

    return wrap


def ro_user_only(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if current_user.user_type in ["admin", "ro_user"]:
            return f(*args, **kwargs)
        else:
            # flash("You need to be an admin to view this page")
            return redirect(url_for("main.index"))

    return wrap


def fund_managers(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if current_user.username in [
            "bar44515",
            "vin38405",
            "sug29777",
            "sud45327",
            "jan27629",
            "ush25768",
            "hem27596",
        ]:
            return f(*args, **kwargs)

        else:
            # flash("You need to be an admin to view this page")
            # abort(404)
            return redirect(url_for("funds.funds_reports"))

    return wrap


def leave_managers(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "leave_manager" in current_user.role:
            return f(*args, **kwargs)
        else:
            return redirect(url_for("main.index"))

    return wrap
