from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from ctenex.domain.contracts import ContractCode
from ctenex.domain.entities import (
    OpenOrderStatus,
    OrderSide,
    OrderStatus,
    OrderType,
)


class Order(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    contract_id: ContractCode
    trader_id: UUID
    side: OrderSide
    type: OrderType
    price: Decimal | None = Field(
        default=None, description="Required for limit orders, ignored for market orders"
    )
    quantity: Decimal
    status: OrderStatus = Field(default=OpenOrderStatus.OPEN)
    remaining_quantity: Decimal | None = Field(default=None)
    placed_at: datetime = Field(default=datetime.now(UTC))
