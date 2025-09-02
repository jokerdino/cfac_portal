import click
from flask.cli import with_appcontext

from sqlalchemy import text

from extensions import db


@click.command("reset-id")
@click.argument("table_name")
@with_appcontext
def reset_id(table_name):
    """Reset the ID sequence for the given table (PostgreSQL)."""

    # By convention, Postgres sequences for serial PKs are named: <table>_id_seq
    sequence_name = f"{table_name}_id_seq"

    try:
        db.session.execute(text(f"ALTER SEQUENCE {sequence_name} RESTART WITH 1;"))
        db.session.commit()
        click.echo(f"✅ Sequence '{sequence_name}' reset to 1.")
    except Exception as e:
        db.session.rollback()
        click.echo(f"❌ Failed to reset sequence: {e}")
