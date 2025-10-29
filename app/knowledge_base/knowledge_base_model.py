from flask import abort
from sqlalchemy.orm import Mapped

from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class KnowledgeBase(db.Model):
    id: Mapped[IntPK]
    topic: Mapped[str]
    title: Mapped[str]
    knowledge_base_document: Mapped[str]

    is_visible: Mapped[bool]
    status: Mapped[bool]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    def has_access(self, user) -> bool:
        """
        Checks if the given user has access to the knowledge base entry.

        If the knowledge base entry is visible, non-admin users will have access.
        If the knowledge base entry is not visible, only admin users will have access.

        Args:
            user: The user to check access for.

        Returns:
            bool: True if the user has access, False otherwise.
        """
        if self.status:
            role = user.user_type

            if role != "admin":
                return self.is_visible

            return True

        return False

    def require_access(self, user):
        if not self.has_access(user):
            abort(404)
