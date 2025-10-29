from datetime import datetime

from flask import (
    current_app,
    redirect,
    render_template,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from . import knowledge_base_bp
from .knowledge_base_form import KnowledgeBaseForm
from .knowledge_base_model import KnowledgeBase

from extensions import db
from set_view_permissions import admin_required


@knowledge_base_bp.route("/add", methods=["POST", "GET"])
@login_required
@admin_required
def add_knowledge_base_document():
    form = KnowledgeBaseForm()

    if form.validate_on_submit():
        kb = KnowledgeBase()
        form.populate_obj(kb)

        is_visible: bool = True if (form.data["is_visible"] == "True") else False
        status: bool = True if (form.data["status"] == "True") else False

        kb.is_visible = is_visible
        kb.status = status

        upload_kb_document(
            form, "knowledge_base_document", kb, "knowledge_base_document"
        )
        db.session.add(kb)
        db.session.commit()
        return redirect(url_for("knowledge_base.knowledge_base_home_page"))
    return render_template("kb_add_entry.html", form=form, title="Upload document")


@knowledge_base_bp.route("/view/<int:key>/")
@login_required
@admin_required
def view_knowledge_base_entry(key):
    kb = db.get_or_404(KnowledgeBase, key)
    kb.require_access(current_user)
    return render_template(
        "kb_view_entry.html",
        kb=kb,
    )


@knowledge_base_bp.route("/edit/<int:key>/", methods=["POST", "GET"])
@login_required
@admin_required
def edit_knowledge_base_entry(key):
    kb = db.get_or_404(KnowledgeBase, key)
    kb.require_access(current_user)
    form = KnowledgeBaseForm(obj=kb)
    form.knowledge_base_document.validators = []
    if form.validate_on_submit():
        form.populate_obj(kb)
        kb.is_visible = True if (form.data["is_visible"] == "True") else False
        kb.status = True if (form.data["status"] == "True") else False
        db.session.commit()
        return redirect(url_for(".knowledge_base_home_page"))

    form.is_visible.data = "True" if kb.is_visible else "False"
    form.status.data = "True" if kb.status else "False"

    return render_template(
        "kb_add_entry.html", form=form, key=key, title="Edit document", kb=kb
    )


@knowledge_base_bp.route("/")
@login_required
def knowledge_base_home_page():
    stmt = db.select(KnowledgeBase).where(KnowledgeBase.status.is_not(False))
    if current_user.user_type != "admin":
        stmt = stmt.where(KnowledgeBase.is_visible.is_not(False))
    kb_query = db.session.scalars(stmt)
    return render_template(
        "kb_homepage.html",
        kb_query=kb_query,
    )


@knowledge_base_bp.route("/download/<int:kb_id>/")
@login_required
def download_kb_document(kb_id):
    kb = db.get_or_404(KnowledgeBase, kb_id)
    kb.require_access(current_user)
    filename_extension: str = kb.knowledge_base_document.rsplit(".", 1)[1]
    filename: str = f"{kb.topic}_{kb.title}.{filename_extension}"
    return send_from_directory(
        directory=f"{current_app.config.get('UPLOAD_FOLDER')}knowledge_base/",
        path=kb.knowledge_base_document,
        as_attachment=True,
        download_name=filename,
    )


def upload_kb_document(form, form_field, model_obj, model_field):
    if form.data[form_field]:
        kb_filename_data: str = secure_filename(form.data[form_field].filename)
        kb_file_extension: str = kb_filename_data.rsplit(".", 1)[1]
        kb_filename: str = (
            "knowledge_base"
            + datetime.now().strftime("%d%m%Y %H%M%S")
            + "."
            + kb_file_extension
        )
        form.data[form_field].save(
            f"{current_app.config.get('UPLOAD_FOLDER')}knowledge_base/" + kb_filename
        )
        setattr(model_obj, model_field, kb_filename)
