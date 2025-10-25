import os
from typing import Optional
from datetime import date, datetime

from flask import current_app
import humanize
from sqlalchemy.orm import Mapped

from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class Contracts(db.Model):
    id: Mapped[IntPK]

    vendor: Mapped[str]
    purpose: Mapped[str]
    start_date: Mapped[date]
    end_date: Mapped[date]
    status: Mapped[Optional[str]]
    emd: Mapped[Optional[int]]
    renewal: Mapped[str]
    notice_period: Mapped[str]

    remarks: Mapped[str]
    contract_file: Mapped[Optional[str]]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]
    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    @property
    def compare_end_date(self):
        today = datetime.date(datetime.now())
        if self.end_date == today:
            return "Expiring today."
        elif self.end_date > today:
            return f"Expiring in {humanize.naturaldelta(self.end_date - today)}."
        else:
            return f"Expired {humanize.naturaldelta(self.end_date - today)} ago."

    @property
    def file_extension(self):
        return self.contract_file.rsplit(".", 1)[1] if "." in self.contract_file else ""

    @property
    def download_filename(self):
        """Generate a human-friendly download filename."""
        return f"{self.id}_{self.vendor}_{self.purpose}.{self.file_extension}"

    @property
    def file_path(self):
        """Return the absolute file path on disk."""
        base = current_app.config.get("UPLOAD_FOLDER")
        return os.path.join(base, "contracts", self.contract_file)
