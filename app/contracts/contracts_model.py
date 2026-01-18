from pathlib import Path
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
    def file_path(self) -> Path:
        """Return the absolute file path on disk."""
        return (
            current_app.config["UPLOAD_FOLDER_PATH"] / "contracts" / self.contract_file
        )

    @property
    def file_extension(self) -> str:
        return Path(self.contract_file).suffix

    @property
    def download_filename(self) -> str:
        return f"{self.id}_{self.vendor}_{self.purpose}{self.file_extension}"
