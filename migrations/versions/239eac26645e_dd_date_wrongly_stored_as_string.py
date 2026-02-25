"""DD-date wrongly stored as string

Revision ID: 239eac26645e
Revises: 46c4cc468740
Create Date: 2026-02-25 11:56:44.754548

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "239eac26645e"
down_revision = "46c4cc468740"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("direct_debit") as batch_op:
        batch_op.alter_column(
            "ro_jv_date",
            existing_type=sa.VARCHAR(),
            type_=sa.Date(),
            postgresql_using="NULLIF(ro_jv_date, '')::date",
        )


def downgrade():
    with op.batch_alter_table("direct_debit") as batch_op:
        batch_op.alter_column(
            "ro_jv_date",
            existing_type=sa.Date(),
            type_=sa.VARCHAR(),
            postgresql_using="ro_jv_date::text",
        )
