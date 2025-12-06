from datetime import datetime
from typing import Optional
from typing_extensions import Annotated

from flask_admin import Admin
from flask_admin.theme import Bootstrap4Theme
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, mapped_column
from flask_debugtoolbar import DebugToolbarExtension


from flask_admin_models import MyAdminIndexView

migrate = Migrate(compare_type=True)
lm = LoginManager()


IntPK = Annotated[int, mapped_column(primary_key=True)]
CreatedBy = Annotated[
    Optional[str], mapped_column(default=lambda: current_user.username)
]
CreatedOn = Annotated[Optional[datetime], mapped_column(default=datetime.now)]
UpdatedBy = Annotated[
    Optional[str],
    mapped_column(onupdate=lambda: current_user.username),
]
UpdatedOn = Annotated[Optional[datetime], mapped_column(onupdate=datetime.now)]

CreatedById = Annotated[Optional[int], mapped_column(default=lambda: current_user.id)]
UpdatedById = Annotated[Optional[int], mapped_column(onupdate=lambda: current_user.id)]


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

toolbar = DebugToolbarExtension()
