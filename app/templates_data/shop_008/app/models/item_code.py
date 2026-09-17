from sqlalchemy import String, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ItemCode(Base):
    __tablename__ = "item_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(512))
    is_sold: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sold_order_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


