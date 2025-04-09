from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from ctenex.domain.contracts import ContractCode
from ctenex.domain.entities import OrderSide, OrderType, ProcessedOrderStatus
from ctenex.domain.order.model import Order
from ctenex.domain.order_book.model import OrderBook
from tests.fixtures.db import async_session, engine, setup_and_teardown_db  # noqa F401


@pytest.fixture
def order_book():
    return OrderBook(contract_id="TEST-CONTRACT")


@pytest.fixture
def sample_limit_buy_order():
    return Order(
        id=uuid4(),
        contract_id=ContractCode.UK_BL_MAR_25,
        trader_id=UUID("5acdba4c-5f3a-4311-a4a5-cb896af79b1d"),
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        price=Decimal("100.0"),
        quantity=Decimal("10.0"),
        placed_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_limit_sell_order():
    return Order(
        id=uuid4(),
        contract_id=ContractCode.UK_BL_MAR_25,
        trader_id=UUID("42aec10a-7ece-4254-81a8-e0edd929599a"),
        side=OrderSide.SELL,
        type=OrderType.LIMIT,
        price=Decimal("101.0"),
        quantity=Decimal("5.0"),
        placed_at=datetime.now(UTC),
    )


class TestOrderBook:
    def setup_method(self):
        self.order_book = OrderBook(contract_id=ContractCode.UK_BL_MAR_25)

    async def test_add_limit_buy_order(self, sample_limit_buy_order):
        """Test adding a limit buy order to the book."""

        # Setup
        ...

        # Test
        order_id = await self.order_book.add_order(sample_limit_buy_order)

        # Validation
        assert isinstance(order_id, UUID)

    async def test_add_limit_sell_order(self, sample_limit_sell_order):
        """Test adding a limit sell order to the book."""

        # Setup
        ...

        # Test
        order_id = await self.order_book.add_order(sample_limit_sell_order)

        # Validation
        assert isinstance(order_id, UUID)

    async def test_add_market_buy_order(self):
        """Test adding a market buy order sets price to infinity."""

        # Setup
        market_order = Order(
            id=uuid4(),
            contract_id=ContractCode.UK_BL_MAR_25,
            trader_id=UUID("5acdba4c-5f3a-4311-a4a5-cb896af79b1d"),
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=Decimal("10.0"),
            placed_at=datetime.now(UTC),
        )

        # Test
        order_id = await self.order_book.add_order(market_order)

        # Validation
        assert market_order.price == Decimal("999.99")
        assert isinstance(order_id, UUID)

    async def test_add_market_sell_order(self):
        """Test adding a market sell order sets price to zero."""

        # Setup
        market_order = Order(
            id=uuid4(),
            contract_id=ContractCode.UK_BL_MAR_25,
            trader_id=UUID("5acdba4c-5f3a-4311-a4a5-cb896af79b1d"),
            side=OrderSide.SELL,
            type=OrderType.MARKET,
            quantity=Decimal("10.0"),
            placed_at=datetime.now(UTC),
        )

        # Test
        order_id = await self.order_book.add_order(market_order)

        # Validation
        assert market_order.price == Decimal("0.00")
        assert isinstance(order_id, UUID)

    async def test_add_limit_order_without_price_raises_error(self):
        """Test adding a limit order without price raises ValueError."""

        # Setup
        order = Order(
            id=uuid4(),
            contract_id=ContractCode.UK_BL_MAR_25,
            trader_id=UUID("5acdba4c-5f3a-4311-a4a5-cb896af79b1d"),
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            quantity=Decimal("10.0"),
            placed_at=datetime.now(UTC),
        )

        # Test and validation
        with pytest.raises(ValueError, match="Order must have a price"):
            await self.order_book.add_order(order)

    async def test_cancel_existing_buy_order(self, sample_limit_buy_order):
        """Test cancelling an existing order."""

        # Setup
        order_id = await self.order_book.add_order(sample_limit_buy_order)

        # Test
        cancelled_order = await self.order_book.cancel_order(order_id)

        # Validation
        if cancelled_order:
            assert cancelled_order.id == sample_limit_buy_order.id
            assert cancelled_order.status == ProcessedOrderStatus.CANCELLED

    async def test_cancel_existing_sell_order(self, sample_limit_sell_order):
        """Test cancelling an existing order."""

        # Setup
        order_id = await self.order_book.add_order(sample_limit_sell_order)

        # Test
        cancelled_order = await self.order_book.cancel_order(order_id)

        # Validation
        if cancelled_order:
            assert cancelled_order.id == sample_limit_sell_order.id
            assert cancelled_order.status == ProcessedOrderStatus.CANCELLED

    async def test_cancel_nonexistent_order(self):
        """Test cancelling an order that doesn't exist returns None."""

        # Setup
        ...

        # Test
        result = await self.order_book.cancel_order(uuid4())

        # Validation
        assert result is None

    # async def test_cancel_order_without_price_raises_error(self):
    #     """Test cancelling an order without price raises ValueError."""

    #     # Setup
    #     order = Order(
    #         id=uuid4(),
    #         contract_id=ContractCode.UK_BL_MAR_25,
    #         trader_id=UUID("5acdba4c-5f3a-4311-a4a5-cb896af79b1d"),
    #         side=OrderSide.BUY,
    #         type=OrderType.LIMIT,
    #         quantity=10.0,
    #         created_at=datetime.now(UTC),
    #     )
    #     # self.order_book.orders_by_id[order.id] = order

    #     # Test and validation
    #     with pytest.raises(
    #         ValueError, match="Order cannot be cancelled as it has no price"
    #     ):
    #         self.order_book.cancel_order(order.id)

    async def test_get_orders_returns_all_orders(
        self, sample_limit_buy_order, sample_limit_sell_order
    ):
        """Test get_orders returns all orders in the book."""

        # Setup
        ...

        # Test
        await self.order_book.add_order(sample_limit_buy_order)
        await self.order_book.add_order(sample_limit_sell_order)

        # Validation
        orders = await self.order_book.get_orders()
        assert len(orders) == 2
        assert sample_limit_buy_order in orders
        assert sample_limit_sell_order in orders

    async def test_get_orders_empty_book(self):
        """Test get_orders returns empty list for empty book."""

        # Setup
        ...

        # Test and validation
        assert await self.order_book.get_orders() == []

    # async def test_price_time_priority_buy_orders(self):
    #     """Test buy orders are stored with price-time priority."""

    #     # Setup
    #     order1 = Order(
    #         id=uuid4(),
    #         contract_id=ContractCode.UK_BL_MAR_25,
    #         trader_id=UUID("5acdba4c-5f3a-4311-a4a5-cb896af79b1d"),
    #         side=OrderSide.BUY,
    #         type=OrderType.LIMIT,
    #         price=100.0,
    #         quantity=10.0,
    #         created_at=datetime.now(UTC),
    #     )
    #     order2 = Order(
    #         id=uuid4(),
    #         contract_id=ContractCode.UK_BL_MAR_25,
    #         trader_id=UUID("42aec10a-7ece-4254-81a8-e0edd929599a"),
    #         side=OrderSide.BUY,
    #         type=OrderType.LIMIT,
    #         price=101.0,
    #         quantity=5.0,
    #         created_at=datetime.now(UTC),
    #     )

    #     # Test
    #     self.order_book.add_order(order1)
    #     self.order_book.add_order(order2)

    #     # Validation
    #     # Higher price should be first in bids
    #     assert list(self.order_book.bids.keys())[0] == -101.0

    # async def test_price_time_priority_sell_orders(self):
    #     """Test sell orders are stored with price-time priority."""

    #     # Setup
    #     order1 = Order(
    #         id=uuid4(),
    #         contract_id=ContractCode.UK_BL_MAR_25,
    #         trader_id=UUID("5acdba4c-5f3a-4311-a4a5-cb896af79b1d"),
    #         side=OrderSide.SELL,
    #         type=OrderType.LIMIT,
    #         price=101.0,
    #         quantity=10.0,
    #         created_at=datetime.now(UTC),
    #     )
    #     order2 = Order(
    #         id=uuid4(),
    #         contract_id=ContractCode.UK_BL_MAR_25,
    #         trader_id=UUID("42aec10a-7ece-4254-81a8-e0edd929599a"),
    #         side=OrderSide.SELL,
    #         type=OrderType.LIMIT,
    #         price=100.0,
    #         quantity=5.0,
    #         created_at=datetime.now(UTC),
    #     )

    #     # Test
    #     self.order_book.add_order(order1)
    #     self.order_book.add_order(order2)

    #     # Validation
    #     # Lower price should be first in asks
    #     assert list(self.order_book.asks.keys())[0] == 100.0
