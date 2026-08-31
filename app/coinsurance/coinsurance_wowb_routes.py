import pandas as pd

from flask import redirect, render_template, url_for
from flask_login import login_required

from extensions import db

from set_view_permissions import admin_required

from . import coinsurance_bp
from .coinsurance_model import CoinsuranceWriteOffWriteBackEntry
from .coinsurance_form import UploadFileForm


@coinsurance_bp.route("/wowb/upload/", methods=["POST", "GET"])
@login_required
@admin_required
def upload_wowb():
    form = UploadFileForm()
    if form.validate_on_submit():
        df = pd.read_excel(form.data["file_upload"])
        df.columns = df.columns.str.lower().str.replace(" ", "_")

        df = df.astype(object).where(pd.notnull(df), None)

        db.session.execute(
            db.insert(CoinsuranceWriteOffWriteBackEntry),
            df.to_dict(orient="records"),
        )
        db.session.commit()
        return redirect(url_for("coinsurance.list_coinsurance_wowb"))
    return render_template("coinsurance_form.html", form=form)
