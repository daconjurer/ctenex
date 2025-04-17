from typing import Type
from uuid import UUID

from loguru import logger

from ctenex.core.db.async_session import AsyncSessionStream, get_async_session
from ctenex.core.db.utils import get_entity_values
from ctenex.domain.contracts import ContractCode
from ctenex.domain.entities import (
    OpenOrderStatus,
    Order,
    OrderSide,
    OrderType,
    ProcessedOrderStatus,
    Trade,
)
from ctenex.domain.order.model import Order as OrderSchema
from ctenex.domain.order_book.model import OrderBook
from ctenex.domain.order_book.trade.filter_params import TradeFilterParams
from ctenex.domain.order_book.trade.reader import trades_reader
from ctenex.domain.order_book.trade.writer import trades_writer
from ctenex.domain.trade.model import Trade as TradeSchema
from sqlalchemy import select


class MatchingEngine:
    trades_writer = trades_writer
    trades_reader = trades_reader

    def __init__(
        self,
        db: AsyncSessionStream = get_async_session,
    ):
        self.order_books: dict[ContractCode, OrderBook] = {}
        self.db: AsyncSessionStream = db

    def start(self, contract_codes: Type[ContractCode] = ContractCode):
        """Start the matching engine and create order books for all contract codes."""
        for contract_code in contract_codes:
            self.order_books[contract_code] = OrderBook(contract_code)

    def stop(self):
        """Stop the matching engine and clear all order books."""
        self.order_books.clear()

    async def add_order(self, order: OrderSchema) -> UUID:
        """Add an order to the book and return any trades that result."""
        logger.debug(f"Adding order: {order}")

        if order.remaining_quantity is None:
            order.remaining_quantity = order.quantity

        # Try to match the order first
        if order.side == OrderSide.BUY:
            trades = await self._match_buy_order(order)
        else:
            trades = await self._match_sell_order(order)

        # Persist order in book (whatever the status)
        await self.order_books[order.contract_id].add_order(order)

        # Persist trades
        async with self.db() as session:
            for trade in trades:
                trade_entity = Trade(**trade.model_dump())
                await self.trades_writer.create(session, trade_entity)
            await session.commit()

        return order.id

    async def get_orders(
        self,
        contract_id: ContractCode,
    ) -> list[OrderSchema]:
        return await self.order_books[contract_id].get_orders()

    async def get_order(
        self,
        contract_id: ContractCode,
        order_id: UUID,
    ) -> OrderSchema | None:
        return await self.order_books[contract_id].get_order(order_id)

    async def get_trades_by_order(
        self,
        contract_id: ContractCode,  # noqa F811
        order_id: UUID,
    ) -> list[TradeSchema]:
        # check if order is in book
        order = await self.order_books[contract_id].get_order(order_id)
        if order is None:
            raise ValueError(f"Order with ID {order_id} not found in book")

        # Determine if order is a buy or sell
        if order.side == OrderSide.BUY:
            filter = TradeFilterParams(buy_order_id=order_id)
        else:
            filter = TradeFilterParams(sell_order_id=order_id)

        trades = await self.trades_reader.get_many(
            self.db,
            filter=filter,
        )
        return [TradeSchema(**get_entity_values(trade)) for trade in trades]

    async def _match_buy_order(self, buy_order: OrderSchema) -> list[TradeSchema]:
        order_book = self.order_books[buy_order.contract_id]
        trades = []

        # Match against the best ask price
        while OpenOrderStatus.OPEN == buy_order.status:
            # Check if there are any asks to match against
            best_ask_price = await order_book.get_best_ask_price()

            if best_ask_price is None:
                break

            # For limit orders, check if the price is acceptable
            if buy_order.type == OrderType.LIMIT and best_ask_price > buy_order.price:
                break

            async with self.db() as session:
                next_sell_order_cursor = await session.execute(
                    select(Order)
                    .where(
                        Order.contract_id == buy_order.contract_id,
                        Order.side == OrderSide.SELL,
                        Order.status.in_(
                            [OpenOrderStatus.OPEN, OpenOrderStatus.PARTIALLY_FILLED]
                        ),
                        Order.price
                        <= (
                            float("inf")
                            if buy_order.type == OrderType.MARKET
                            else buy_order.price
                        ),
                    )
                    .order_by(
                        Order.price.asc(),  # Best (lowest) price first
                        Order.created_at.asc(),  # First in time at each price level
                    )
                )
                next_sell_order = next_sell_order_cursor.scalars().one()

            # Calculate trade quantity
            trade_quantity = min(
                buy_order.remaining_quantity,
                next_sell_order.remaining_quantity,
            )

            # Update order quantities
            buy_order.remaining_quantity -= trade_quantity
            next_sell_order.remaining_quantity -= trade_quantity

            # Update order statuses
            if next_sell_order.remaining_quantity == 0:
                next_sell_order.status = ProcessedOrderStatus.FILLED
            else:
                next_sell_order.status = OpenOrderStatus.PARTIALLY_FILLED

            if buy_order.remaining_quantity == 0:
                buy_order.status = ProcessedOrderStatus.FILLED
            else:
                buy_order.status = OpenOrderStatus.PARTIALLY_FILLED

            # TODO: Update order book and trade in a transaction

            # Update order book
            await order_book.update_order(next_sell_order)

            # Create and record the trade
            trade = TradeSchema(
                contract_id=order_book.contract_id,
                buy_order_id=buy_order.id,
                sell_order_id=next_sell_order.id,
                price=best_ask_price,
                quantity=trade_quantity,
            )
            # trade_entity = Trade(**trade.model_dump())

            # async with self.db() as session:
            #     generated_trade = await self.trades_writer.create(session, trade_entity)
            #     await session.commit()

            trades.append(trade)
            # trades.append(TradeSchema(**get_entity_values(trade)))

        # if len(trades) > 0:
        #     logger.debug(f"Matched order with ID {buy_order.id}")
        #     logger.debug(f"Generated {len(trades)} trades:")
        #     for trade in trades:
        #         logger.debug(trade)

        return trades

    async def _match_sell_order(self, sell_order: OrderSchema) -> list[TradeSchema]:
        order_book = self.order_books[sell_order.contract_id]
        trades = []

        # Match against the best bid price
        while OpenOrderStatus.OPEN == sell_order.status:
            # Check if there are any bids to match against
            best_bid_price = await order_book.get_best_bid_price()

            if best_bid_price is None:
                break

            # For limit orders, check if the price is acceptable
            if sell_order.type == OrderType.LIMIT and best_bid_price < sell_order.price:
                break

            async with self.db() as session:
                next_buy_order_cursor = await session.execute(
                    select(Order)
                    .where(
                        Order.contract_id == sell_order.contract_id,
                        Order.side == OrderSide.BUY,
                        Order.status.in_(
                            [OpenOrderStatus.OPEN, OpenOrderStatus.PARTIALLY_FILLED]
                        ),
                        Order.price
                        <= (
                            float("inf")
                            if sell_order.type == OrderType.MARKET
                            else sell_order.price
                        ),
                    )
                    .order_by(
                        Order.price.asc(),  # Best (lowest) price first
                        Order.created_at.asc(),  # First in time at each price level
                    )
                )
                next_buy_order = next_buy_order_cursor.scalars().one()

            # Calculate trade quantity
            trade_quantity = min(
                sell_order.remaining_quantity,
                next_buy_order.remaining_quantity,
            )

            # TODO: Update order book and trade in a transaction

            # Update order quantities
            sell_order.remaining_quantity -= trade_quantity
            next_buy_order.remaining_quantity -= trade_quantity

            # Update order statuses
            if next_buy_order.remaining_quantity == 0:
                next_buy_order.status = ProcessedOrderStatus.FILLED
            else:
                next_buy_order.status = OpenOrderStatus.PARTIALLY_FILLED

            if sell_order.remaining_quantity == 0:
                sell_order.status = ProcessedOrderStatus.FILLED
            else:
                sell_order.status = OpenOrderStatus.PARTIALLY_FILLED

            # Update order book
            await order_book.update_order(next_buy_order)

            # Create and record the trade
            trade = TradeSchema(
                contract_id=sell_order.contract_id,
                buy_order_id=next_buy_order.id,
                sell_order_id=sell_order.id,
                price=best_bid_price,
                quantity=trade_quantity,
            )
            # trade_entity = Trade(**trade.model_dump())

            trades.append(trade)
            # trades.append(TradeSchema(**get_entity_values(trade)))

        # async with self.db() as session:
        #     await self.trades_writer.create(session, trade_entity)
        #     await session.commit()

        # if len(trades) > 0:
        #     logger.debug(f"Matched order with ID {sell_order.id}")
        #     logger.debug(f"Generated {len(trades)} trades:")
        #     for trade in trades:
        #         logger.debug(trade)

        return trades
