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

from app.knowledge_base import knowledge_base_bp
from app.knowledge_base.knowledge_base_form import KnowledgeBaseForm
from app.knowledge_base.knowledge_base_model import KnowledgeBase

# from app.tickets.tickets_routes import humanize_datetime


@knowledge_base_bp.route("/add", methods=["POST", "GET"])
@login_required
def add_knowledge_base_document():
    form = KnowledgeBaseForm()
    from extensions import db

    if form.validate_on_submit():
        topic: str = form.data["topic"]
        title: str = form.data["title"]

        is_visible: bool = True if (form.data["is_visible"] == "True") else False
        status: bool = True if (form.data["status"] == "True") else False
        created_by: str = current_user.username
        created_on: datetime = datetime.now()

        if form.data["knowledge_base_document"]:
            kb_filename_data: str = secure_filename(
                form.data["knowledge_base_document"].filename
            )
            kb_file_extension: str = kb_filename_data.rsplit(".", 1)[1]
            kb_filename: str = (
                "knowledge_base"
                + datetime.now().strftime("%d%m%Y %H%M%S")
                + "."
                + kb_file_extension
            )
            form.knowledge_base_document.data.save(
                f"{current_app.config.get("UPLOAD_FOLDER")}knowledge_base/"
                + kb_filename
            )
        else:
            kb_filename: str = None

        knowledge_base = KnowledgeBase(
            topic=topic,
            title=title,
            is_visible=is_visible,
            status=status,
            knowledge_base_document=kb_filename,
            created_by=created_by,
            created_on=created_on,
        )
        db.session.add(knowledge_base)
        db.session.commit()
        return redirect(url_for("knowledge_base.knowledge_base_home_page"))
    return render_template("kb_add_entry.html", form=form, title="Upload document")


@knowledge_base_bp.route("/view/<int:key>")
@login_required
def view_knowledge_base_entry(key):
    kb = KnowledgeBase.query.get_or_404(key)
    return render_template(
        "kb_view_entry.html",
        kb=kb,  # humanize_datetime=humanize_datetime
    )


@knowledge_base_bp.route("/edit/<int:key>", methods=["POST", "GET"])
@login_required
def edit_knowledge_base_entry(key):
    from extensions import db

    kb = KnowledgeBase.query.get_or_404(key)
    form = KnowledgeBaseForm()
    form.knowledge_base_document.validators = []
    if form.validate_on_submit():
        kb.topic = form.data["topic"]
        kb.title = form.data["title"]
        kb.is_visible = True if (form.data["is_visible"] == "True") else False
        kb.status = True if (form.data["status"] == "True") else False
        db.session.commit()
        return redirect(url_for("knowledge_base.view_knowledge_base_entry", key=key))

    form.topic.data = kb.topic
    form.title.data = kb.title
    form.is_visible.data = "True" if kb.is_visible else "False"
    form.status.data = "True" if kb.status else "False"

    return render_template(
        "kb_add_entry.html", form=form, edit=True, key=key, title="Edit document"
    )


@knowledge_base_bp.route("/")
@login_required
def knowledge_base_home_page():
    kb_query = KnowledgeBase.query.filter(KnowledgeBase.status.is_not(False))
    if current_user.user_type != "admin":
        kb_query = kb_query.filter(KnowledgeBase.is_visible.is_not(False))
    return render_template(
        "kb_homepage.html",
        kb_query=kb_query,
    )


@knowledge_base_bp.route("/download/<int:kb_id>")
@login_required
def download_kb_document(kb_id):
    kb = KnowledgeBase.query.get_or_404(kb_id)
    filename_extension: str = kb.knowledge_base_document.rsplit(".", 1)[1]
    filename: str = f"{kb.topic}_{kb.title}.{filename_extension}"
    return send_from_directory(
        directory=f"{current_app.config.get("UPLOAD_FOLDER")}knowledge_base/",
        path=kb.knowledge_base_document,
        as_attachment=True,
        download_name=filename,
    )
