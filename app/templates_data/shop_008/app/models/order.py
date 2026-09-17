from enum import Enum
from sqlalchemy import String, Integer, Enum as PgEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PaymentMethod(int, Enum):
    CARD_RF = 36
    SBP_QR = 44


class OrderStatus(str, Enum):
    CREATED = "created"
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELED = "canceled"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="SET NULL"), nullable=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8), default="RUB")
    payment_method: Mapped[PaymentMethod] = mapped_column(PgEnum(PaymentMethod, name="payment_method"))
    status: Mapped[OrderStatus] = mapped_column(PgEnum(OrderStatus, name="order_status"), default=OrderStatus.CREATED)
    fk_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fk_payment_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    buyer_tg_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
