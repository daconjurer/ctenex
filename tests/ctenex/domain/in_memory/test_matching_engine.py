from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from ctenex.domain.contracts import ContractCode
from ctenex.domain.entities import (
    OpenOrderStatus,
    OrderSide,
    OrderType,
    ProcessedOrderStatus,
)
from ctenex.domain.in_memory.matching_engine.model import MatchingEngine
from ctenex.domain.order_book.order.model import Order
from tests.fixtures.domain import (
    limit_buy_order,  # noqa F811
    limit_sell_order,  # noqa F811
    second_limit_sell_order,  # noqa F811
)


class TestMatchingEngine:
    def setup_method(self):
        """Create a fresh matching engine before each test."""
        self.matching_engine = MatchingEngine()
        self.matching_engine.start()

    def teardown_method(self):
        """Stop the matching engine after each test."""
        self.matching_engine.stop()

    def test_add_limit_buy_order_no_match(
        self,
        limit_buy_order,  # noqa F811
    ):
        """Test adding a limit buy order with no matching sells."""

        # Setup
        ...

        # Test
        order_id = self.matching_engine.add_order(limit_buy_order)

        # Validation
        assert limit_buy_order.id == order_id
        assert limit_buy_order.status == OpenOrderStatus.OPEN
        assert limit_buy_order.remaining_quantity == limit_buy_order.quantity
        assert limit_buy_order in self.matching_engine.get_orders(
            ContractCode.UK_BL_MAR_25
        )

    def test_add_limit_sell_order_no_match(
        self,
        limit_sell_order,  # noqa F811
    ):
        """Test adding a limit sell order with no matching buys."""

        # Setup
        ...

        # Test
        order_id = self.matching_engine.add_order(limit_sell_order)

        # Validation
        assert limit_sell_order.id == order_id
        assert limit_sell_order.status == OpenOrderStatus.OPEN
        assert limit_sell_order.remaining_quantity == limit_sell_order.quantity
        assert limit_sell_order in self.matching_engine.get_orders(
            ContractCode.UK_BL_MAR_25
        )

    def test_match_limit_orders_exact_quantity(
        self,
        limit_buy_order,  # noqa F811
        limit_sell_order,  # noqa F811
    ):
        """Test matching limit orders with exact quantities."""

        # Setup
        limit_sell_order.quantity = limit_buy_order.quantity
        self.matching_engine.add_order(limit_buy_order)

        # Test
        order_id = self.matching_engine.add_order(limit_sell_order)

        # Validation
        assert limit_sell_order.id == order_id
        assert limit_buy_order.status == ProcessedOrderStatus.FILLED
        assert limit_sell_order.status == ProcessedOrderStatus.FILLED
        assert limit_buy_order.remaining_quantity == 0
        assert limit_sell_order.remaining_quantity == 0

        # Both orders should be removed from the book
        assert len(self.matching_engine.get_orders(ContractCode.UK_BL_MAR_25)) == 0

    def test_match_limit_orders_with_partial_fill_of_buy_order(
        self,
        limit_buy_order,  # noqa F811
        limit_sell_order,  # noqa F811
    ):
        """Test matching limit orders where one buy order is partially filled."""

        # Setup
        limit_sell_order.quantity = Decimal("5.0")

        # Test
        self.matching_engine.add_order(limit_buy_order)  # Quantity: 10.0
        order_id = self.matching_engine.add_order(limit_sell_order)  # Quantity: 5.0

        # Validation
        assert limit_sell_order.id == order_id
        assert limit_buy_order.status == OpenOrderStatus.PARTIALLY_FILLED
        assert limit_sell_order.status == ProcessedOrderStatus.FILLED
        assert limit_buy_order.remaining_quantity == 5.0
        assert limit_sell_order.remaining_quantity == 0

        # Buy order should remain in the book
        orders = self.matching_engine.get_orders(ContractCode.UK_BL_MAR_25)
        assert len(orders) == 1
        assert limit_buy_order in orders

    def test_match_limit_orders_with_partial_fill_of_sell_order(
        self,
        limit_buy_order,  # noqa F811
        second_limit_sell_order,  # noqa F811
    ):
        """Test matching limit orders where one sell order is partially filled."""

        # Setup
        ...

        # Test
        self.matching_engine.add_order(limit_buy_order)  # Quantity: 10.0
        order_id = self.matching_engine.add_order(
            second_limit_sell_order
        )  # Quantity: 15.0

        # Validation
        assert second_limit_sell_order.id == order_id
        assert limit_buy_order.status == ProcessedOrderStatus.FILLED
        assert second_limit_sell_order.status == OpenOrderStatus.PARTIALLY_FILLED
        assert limit_buy_order.status == ProcessedOrderStatus.FILLED
        assert second_limit_sell_order.remaining_quantity == 5.0
        assert limit_buy_order.remaining_quantity == 0

        # Buy order should remain in the book
        orders = self.matching_engine.get_orders(ContractCode.UK_BL_MAR_25)
        assert len(orders) == 1
        assert second_limit_sell_order in orders

    def test_match_market_buy_order(
        self,
        limit_sell_order,  # noqa F811
    ):
        """Test matching a market buy order against existing sell orders."""

        # Setup
        self.matching_engine.add_order(limit_sell_order)
        market_order = Order(
            id=uuid4(),
            contract_id=ContractCode.UK_BL_MAR_25,
            trader_id=uuid4(),
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=Decimal("10.0"),
            placed_at=datetime.now(UTC),
        )

        # Test
        order_id = self.matching_engine.add_order(market_order)

        # Validation
        assert market_order.id == order_id
        assert market_order.status == ProcessedOrderStatus.FILLED
        assert limit_sell_order.status == ProcessedOrderStatus.FILLED

        # Book should be empty
        assert len(self.matching_engine.get_orders(ContractCode.UK_BL_MAR_25)) == 0

    def test_match_market_sell_order(
        self,
        limit_buy_order,  # noqa F811
    ):
        """Test matching a market sell order against existing buy orders."""

        # Setup
        self.matching_engine.add_order(limit_buy_order)
        market_order = Order(
            id=uuid4(),
            contract_id=ContractCode.UK_BL_MAR_25,
            trader_id=uuid4(),
            side=OrderSide.SELL,
            type=OrderType.MARKET,
            quantity=Decimal("5.0"),
            placed_at=datetime.now(UTC),
        )

        # Test
        order_id = self.matching_engine.add_order(market_order)

        # Validation
        assert market_order.id == order_id
        assert market_order.status == ProcessedOrderStatus.FILLED
        assert limit_buy_order.status == OpenOrderStatus.PARTIALLY_FILLED
        assert limit_buy_order.remaining_quantity == 5.0

    def test_match_multiple_orders(self):
        """Test matching an order against multiple existing orders."""

        # Setup
        sell1 = Order(
            id=uuid4(),
            contract_id=ContractCode.UK_BL_MAR_25,
            trader_id=uuid4(),
            side=OrderSide.SELL,
            type=OrderType.LIMIT,
            price=Decimal("100.0"),
            quantity=Decimal("5.0"),
            placed_at=datetime.now(UTC),
        )
        sell2 = Order(
            id=uuid4(),
            contract_id=ContractCode.UK_BL_MAR_25,
            trader_id=uuid4(),
            side=OrderSide.SELL,
            type=OrderType.LIMIT,
            price=Decimal("101.0"),
            quantity=Decimal("5.0"),
            placed_at=datetime.now(UTC),
        )
        self.matching_engine.add_order(sell1)
        self.matching_engine.add_order(sell2)

        buy_order = Order(
            id=uuid4(),
            contract_id=ContractCode.UK_BL_MAR_25,
            trader_id=uuid4(),
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=Decimal("8.0"),
            placed_at=datetime.now(UTC),
        )

        # Test
        order_id = self.matching_engine.add_order(buy_order)

        # Validation
        assert buy_order.id == order_id
        assert sell1.status == ProcessedOrderStatus.FILLED
        assert sell2.status == OpenOrderStatus.PARTIALLY_FILLED
        assert buy_order.status == ProcessedOrderStatus.FILLED
        assert buy_order.remaining_quantity == 0

    def test_price_time_priority_matching(self):
        """Test orders are matched according to price-time priority."""

        # Setup
        sell1 = Order(
            id=uuid4(),
            contract_id=ContractCode.UK_BL_MAR_25,
            trader_id=uuid4(),
            side=OrderSide.SELL,
            type=OrderType.LIMIT,
            price=Decimal("100.0"),
            quantity=Decimal("5.0"),
            placed_at=datetime.now(UTC),
        )
        sell2 = Order(
            id=uuid4(),
            contract_id=ContractCode.UK_BL_MAR_25,
            trader_id=uuid4(),
            side=OrderSide.SELL,
            type=OrderType.LIMIT,
            price=Decimal("100.0"),
            quantity=Decimal("5.0"),
            placed_at=datetime.now(UTC),
        )
        self.matching_engine.add_order(sell1)  # First order at 100.0
        self.matching_engine.add_order(sell2)  # Second order at 100.0

        buy_order = Order(
            id=uuid4(),
            contract_id=ContractCode.UK_BL_MAR_25,
            trader_id=uuid4(),
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=Decimal("7.0"),
            placed_at=datetime.now(UTC),
        )

        # Test
        order_id = self.matching_engine.add_order(buy_order)

        # Validation
        assert buy_order.id == order_id
        assert sell1.status == ProcessedOrderStatus.FILLED
        assert sell2.status == OpenOrderStatus.PARTIALLY_FILLED
        assert buy_order.status == ProcessedOrderStatus.FILLED
        assert buy_order.remaining_quantity == 0.0

    def test_get_trades(
        self,
        limit_buy_order,  # noqa F811
        limit_sell_order,  # noqa F811
    ):
        """Test retrieving trades for a specific contract."""

        # Setup
        self.matching_engine.add_order(limit_buy_order)
        self.matching_engine.add_order(limit_sell_order)

        # Test
        trades = self.matching_engine.get_trades(ContractCode.UK_BL_MAR_25)

        # Validation
        assert len(trades) == 1
        assert all(t.contract_id == ContractCode.UK_BL_MAR_25 for t in trades)

    def test_limit_buy_order_respects_price_limit(self):
        """Test that a limit buy order does not match with asks above its limit price."""

        # Setup
        sell_order = Order(
            id=uuid4(),
            contract_id=ContractCode.UK_BL_MAR_25,
            trader_id=uuid4(),
            side=OrderSide.SELL,
            type=OrderType.LIMIT,
            price=Decimal("100.0"),
            quantity=Decimal("5.0"),
            placed_at=datetime.now(UTC),
        )
        self.matching_engine.add_order(sell_order)

        buy_order = Order(
            id=uuid4(),
            contract_id=ContractCode.UK_BL_MAR_25,
            trader_id=uuid4(),
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            price=Decimal("99.0"),  # Lower than sell order price
            quantity=Decimal("5.0"),
            placed_at=datetime.now(UTC),
        )

        # Test
        order_id = self.matching_engine.add_order(buy_order)

        # Validation
        assert buy_order.id == order_id
        assert buy_order.status == OpenOrderStatus.OPEN
        assert sell_order.status == OpenOrderStatus.OPEN
        assert buy_order.remaining_quantity == 5.0
        assert sell_order.remaining_quantity == 5.0

        # Both orders should remain in the book
        orders = self.matching_engine.get_orders(ContractCode.UK_BL_MAR_25)
        assert len(orders) == 2
        assert buy_order in orders
        assert sell_order in orders

    def test_limit_sell_order_respects_price_limit(self):
        """Test that a limit sell order does not match with bids below its limit price."""

        # Setup
        buy_order = Order(
            id=uuid4(),
            contract_id=ContractCode.UK_BL_MAR_25,
            trader_id=uuid4(),
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            price=Decimal("100.0"),
            quantity=Decimal("5.0"),
            placed_at=datetime.now(UTC),
        )
        self.matching_engine.add_order(buy_order)

        sell_order = Order(
            id=uuid4(),
            contract_id=ContractCode.UK_BL_MAR_25,
            trader_id=uuid4(),
            side=OrderSide.SELL,
            type=OrderType.LIMIT,
            price=Decimal("101.0"),  # Higher than buy order price
            quantity=Decimal("5.0"),
            placed_at=datetime.now(UTC),
        )

        # Test
        order_id = self.matching_engine.add_order(sell_order)

        # Validation
        assert sell_order.id == order_id
        assert buy_order.status == OpenOrderStatus.OPEN
        assert sell_order.status == OpenOrderStatus.OPEN
        assert buy_order.remaining_quantity == 5.0
        assert sell_order.remaining_quantity == 5.0

        # Both orders should remain in the book
        orders = self.matching_engine.get_orders(ContractCode.UK_BL_MAR_25)
        assert len(orders) == 2
        assert buy_order in orders
        assert sell_order in orders
