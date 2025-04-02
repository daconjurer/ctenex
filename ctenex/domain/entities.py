from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import ForeignKey
from sqlalchemy.types import DECIMAL, TIMESTAMP, UUID, String

from ctenex.core.db.base import Base


class Commodity(str, Enum):
    POWER = "power"
    NATURAL_GAS = "natural_gas"
    CRUDE_OIL = "crude_oil"


class DeliveryPeriod(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    LIMIT = "limit"
    MARKET = "market"


class OpenOrderStatus(str, Enum):
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"


class ProcessedOrderStatus(str, Enum):
    FILLED = "filled"
    CANCELLED = "cancelled"


OrderStatus = OpenOrderStatus | ProcessedOrderStatus


class ConcreteBase(Base):
    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        type_=TIMESTAMP(timezone=True),
        default=datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        type_=TIMESTAMP(timezone=True),
        default=datetime.now(UTC),
        onupdate=datetime.now(UTC),
        nullable=False,
    )
    deleted_at: Mapped[datetime] = mapped_column(
        type_=TIMESTAMP(timezone=True),
        nullable=True,
    )

    # __table_args__ = {"schema": "book"}


class Order(ConcreteBase):
    """
    A generic model for orders. This is not a table in the database,
    but a base class for the 'Order', 'Bid', and 'Ask' classes.

    The 'status' column is meant to be implemented by the subclasses
    so they can set their own restrictions on the status.
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        type_=UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    contract_id: Mapped[str] = mapped_column(
        type_=String,
        nullable=False,
    )
    trader_id: Mapped[uuid.UUID] = mapped_column(
        type_=UUID(as_uuid=True),
        nullable=False,
    )
    side: Mapped[OrderSide] = mapped_column(
        type_=String,
        nullable=False,
    )
    type: Mapped[OrderType] = mapped_column(
        type_=String,
        nullable=False,
    )
    price: Mapped[DECIMAL] = mapped_column(
        type_=DECIMAL(precision=5, scale=2),
        nullable=False,
        index=True,
    )
    quantity: Mapped[DECIMAL] = mapped_column(
        type_=DECIMAL(precision=5, scale=2),
        nullable=False,
    )
    placed_at: Mapped[datetime] = mapped_column(
        type_=TIMESTAMP(timezone=True),
        default=datetime.now(UTC),
        nullable=False,
        index=True,
    )


class Contract(ConcreteBase):
    __tablename__ = "contracts"
    __table_args__ = {"schema": "metadata"}

    id: Mapped[str] = mapped_column(
        type_=String,
        primary_key=True,
    )
    commodity: Mapped[str] = mapped_column(
        type_=String,
        nullable=False,
    )
    delivery_period: Mapped[str] = mapped_column(
        type_=String,
        nullable=False,
    )
    start_date: Mapped[datetime] = mapped_column(
        type_=TIMESTAMP(timezone=True),
        nullable=False,
    )
    end_date: Mapped[datetime] = mapped_column(
        type_=TIMESTAMP(timezone=True),
        nullable=False,
    )
    tick_size: Mapped[float] = mapped_column(
        type_=DECIMAL(precision=5, scale=2),
        nullable=False,
    )
    contract_size: Mapped[float] = mapped_column(
        type_=DECIMAL(precision=5, scale=2),
        nullable=False,
    )
    location: Mapped[str] = mapped_column(ForeignKey("metadata.countries.id"))


class Country(ConcreteBase):
    __tablename__ = "countries"
    __table_args__ = {"schema": "metadata"}

    id: Mapped[str] = mapped_column(
        type_=String,
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(
        type_=String,
        nullable=False,
    )


# Book aggregate


class BookOrder(Order):
    __abstract__ = True

    remaining_quantity: Mapped[DECIMAL] = mapped_column(
        type_=DECIMAL(precision=5, scale=2),
        nullable=False,
        default=0,
    )
    status: Mapped[OpenOrderStatus] = mapped_column(
        type_=String,
        nullable=False,
        default=OpenOrderStatus.OPEN,
    )


class Bid(BookOrder):
    __tablename__ = "bids"
    __table_args__ = {"schema": "book"}

    trades: Mapped[list[BookTrade]] = relationship()


class Ask(BookOrder):
    __tablename__ = "asks"
    __table_args__ = {"schema": "book"}

    trades: Mapped[list[BookTrade]] = relationship()


class Trade(ConcreteBase):
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        type_=UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    contract_id: Mapped[str] = mapped_column(
        type_=String,
        nullable=False,
    )
    price: Mapped[DECIMAL] = mapped_column(
        type_=DECIMAL(precision=5, scale=2),
        nullable=False,
    )
    quantity: Mapped[DECIMAL] = mapped_column(
        type_=DECIMAL(precision=5, scale=2),
        nullable=False,
    )
    generated_at: Mapped[datetime] = mapped_column(
        type_=TIMESTAMP(timezone=True),
        default=datetime.now(UTC),
        nullable=False,
    )


class BookTrade(Trade):
    __tablename__ = "trades"
    __table_args__ = {"schema": "book"}

    buy_order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("book.bids.id"))
    sell_order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("book.asks.id"))


# History aggregate


class ProcessedOrder(Order):
    __abstract__ = True

    filled_at: Mapped[datetime] = mapped_column(
        type_=TIMESTAMP(timezone=True),
        default=datetime.now(UTC),
        nullable=False,
        index=True,
    )


class HistoricBid(ProcessedOrder):
    __tablename__ = "historic_bids"
    __table_args__ = {"schema": "history"}

    trades: Mapped[list[HistoricTrade]] = relationship()


class HistoricAsk(ProcessedOrder):
    __tablename__ = "historic_asks"
    __table_args__ = {"schema": "history"}

    trades: Mapped[list[HistoricTrade]] = relationship()


class HistoricTrade(Trade):
    __tablename__ = "trades_history"
    __table_args__ = {"schema": "history"}

    buy_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("history.historic_bids.id")
    )
    sell_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("history.historic_asks.id")
    )
