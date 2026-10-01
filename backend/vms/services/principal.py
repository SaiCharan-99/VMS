from dataclasses import dataclass
from typing import Any

from sqlalchemy import ColumnElement, true

from vms.db.models import ApiKey, Role, User, Video


@dataclass(frozen=True)
class Principal:
    """Who is calling: a logged-in user, or an API key (which acts as an operator)."""

    role: Role
    user: User | None = None
    api_key: ApiKey | None = None

    @classmethod
    def for_user(cls, user: User) -> "Principal":
        return cls(role=user.role, user=user)

    @classmethod
    def for_api_key(cls, key: ApiKey) -> "Principal":
        return cls(role=Role.operator, api_key=key)

    @property
    def actor(self) -> dict[str, Any]:
        """Keyword arguments for `audit.log`."""
        return {
            "actor_user_id": self.user.id if self.user else None,
            "actor_api_key_id": self.api_key.id if self.api_key else None,
        }

    def video_filter(self) -> ColumnElement[bool]:
        """Operators see only their own uploads; an API key only the videos it uploaded."""
        if self.api_key is not None:
            return Video.api_key_id == self.api_key.id
        if self.role == Role.operator:
            return Video.uploaded_by == self.user.id
        return true()

    def can_see(self, video: Video) -> bool:
        if self.api_key is not None:
            return video.api_key_id == self.api_key.id
        if self.role == Role.operator:
            return video.uploaded_by == self.user.id
        return True
