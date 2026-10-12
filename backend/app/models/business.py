from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Business(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A tenant. Every business-related record is associated with exactly one
    Business so that multiple SMEs can use the same deployment in isolation
    (MASTER PROMPT section 6: "Every business-related record should be
    associated with the correct business/tenant").
    """

    __tablename__ = "businesses"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="BDT", nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="business")  # noqa: F821
