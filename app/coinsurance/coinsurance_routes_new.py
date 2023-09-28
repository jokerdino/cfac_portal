from flask import redirect, render_template, url_for
from flask_login import current_user

from app.coinsurance import coinsurance_bp


@coinsurance_bp.route("/")
def coinsurance_home_page():
    if current_user.is_authenticated:
        print(current_user.oo_code)
        return render_template("index.html")
    else:
        return redirect(url_for("users.login_page"))
