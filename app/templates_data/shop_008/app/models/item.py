from enum import Enum
from sqlalchemy import String, Enum as PgEnum, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PricingType(str, Enum):
    PER_HOUR = "per_hour"
    PER_SERVICE = "per_service"


class ItemType(str, Enum):
    SERVICE = "service"
    DIGITAL = "digital"


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    price_minor: Mapped[int] = mapped_column(Integer)  # price in minor units (e.g., kopecks)
    item_type: Mapped[ItemType] = mapped_column(PgEnum(ItemType, name="item_type"))
    image_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)  # Telegram file_id or URL

    # service specific
    pricing_type: Mapped[PricingType | None] = mapped_column(PgEnum(PricingType, name="pricing_type"), nullable=True)
    service_admin_contact: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # digital specific
    delivery_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 'file' or 'github'
    digital_file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    github_repo_read_grant: Mapped[str | None] = mapped_column(String(256), nullable=True)  # optional repo slug
    

    # visibility
    is_visible: Mapped[bool] = mapped_column(default=True, nullable=False)
