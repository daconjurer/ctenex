from decimal import Decimal
from uuid import UUID

from ctenex.core.db.async_session import AsyncSessionStream, get_async_session
from ctenex.core.db.utils import get_entity_values
from ctenex.domain.entities import Order, OrderSide, OrderType, ProcessedOrderStatus
from ctenex.domain.order.model import Order as OrderSchema
from ctenex.domain.order_book.order.reader import orders_reader
from ctenex.domain.order_book.order.writer import orders_writer


class OrderBook:
    orders_writer = orders_writer
    orders_reader = orders_reader

    def __init__(
        self,
        contract_id: str,
        db: AsyncSessionStream = get_async_session,
    ):
        self.contract_id = contract_id
        self.db: AsyncSessionStream = db

    async def get_orders(self) -> list[OrderSchema]:
        orders = await self.orders_reader.get_many(self.db)
        return [OrderSchema(**get_entity_values(order)) for order in orders]

    async def add_order(self, order: OrderSchema) -> UUID:
        """Add an order to the appropriate side of the book."""

        # For market orders, set price to MAX (buy) or 0 (sell) to ensure matching
        if order.type == OrderType.MARKET:
            order.price = (
                Decimal("999.99") if order.side == OrderSide.BUY else Decimal("0.00")
            )
        elif order.price is None:
            raise ValueError("Order must have a price")

        async with self.db() as session:
            entity = Order(**order.model_dump())
            await self.orders_writer.create(session, entity)
            await session.commit()

        return entity.id

    async def cancel_order(self, order_id: UUID) -> OrderSchema | None:
        """Cancel an order and remove it from the book."""

        order = await self.orders_reader.get(self.db, order_id)
        if order is None:
            return None

        if order.price is None:
            raise ValueError("Order cannot be cancelled as it has no price")

        order.status = ProcessedOrderStatus.CANCELLED
        async with self.db() as session:
            await self.orders_writer.update(session, order)
            await session.commit()

        return OrderSchema(**get_entity_values(order))
