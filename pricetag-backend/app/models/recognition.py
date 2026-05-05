import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, LargeBinary, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Recognition(Base):
    __tablename__ = "recognitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    image_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_price: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    is_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    correct_price: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
