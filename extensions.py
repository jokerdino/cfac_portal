import io
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Annotated

from flask import abort, send_file
from flask_admin import Admin
from flask_admin.actions import action
from flask_admin.contrib.fileadmin import FileAdmin
from flask_admin.theme import Bootstrap4Theme
from flask_debugtoolbar import DebugToolbarExtension
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, mapped_column

from flask_admin_models import MyAdminIndexView

migrate = Migrate(compare_type=True)
lm = LoginManager()


IntPK = Annotated[int, mapped_column(primary_key=True)]
CreatedBy = Annotated[str | None, mapped_column(default=lambda: current_user.username)]
CreatedOn = Annotated[datetime | None, mapped_column(default=datetime.now)]
UpdatedBy = Annotated[
    str | None,
    mapped_column(onupdate=lambda: current_user.username),
]
UpdatedOn = Annotated[datetime | None, mapped_column(onupdate=datetime.now)]

CreatedById = Annotated[int | None, mapped_column(default=lambda: current_user.id)]
UpdatedById = Annotated[int | None, mapped_column(onupdate=lambda: current_user.id)]


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


db = SQLAlchemy(model_class=Base)


admin = Admin(
    theme=Bootstrap4Theme(fluid=True, swatch="united"),
    name="CFAC portal",
    index_view=MyAdminIndexView(),
)


class DownloadFileAdmin(FileAdmin):
    can_download = True
    can_upload = False
    can_mkdir = False
    can_rename = False
    can_delete = False
    can_delete_dirs = False

    @action("download_zip", "Download as ZIP")
    def action_download_zip(self, items):
        base = Path(self.get_base_path()).resolve()
        buffer = io.BytesIO()

        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in items:
                target = (base / item).resolve()

                # block path traversal outside the base directory
                if not target.is_relative_to(base):
                    abort(403)

                if target.is_file():
                    zf.write(target, target.relative_to(base))
                elif target.is_dir():
                    for f in target.rglob("*"):
                        if f.is_file():
                            zf.write(f, f.relative_to(base))

        buffer.seek(0)
        return send_file(
            buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="download.zip",
        )


path = Path(__file__).resolve().parent.parent / "data"
admin.add_view(
    DownloadFileAdmin(path, name="Uploaded Files", category="Uploaded documents")
)
toolbar = DebugToolbarExtension()
