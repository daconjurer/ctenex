from datetime import UTC, datetime
from decimal import Decimal
from typing import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from ctenex.api.app_factory import create_app
from ctenex.domain.contracts import ContractCode
from ctenex.domain.order.model import Order, OrderSide, OrderType


@pytest.fixture
def limit_buy_order():
    return Order(
        id=UUID("655889cb-b7c8-47f9-a302-cf9673f21445"),
        contract_id=ContractCode.UK_BL_MAR_25,
        trader_id=UUID("a0130b4b-5f77-4703-9a18-1af5a87cc8eb"),
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        price=Decimal("100.0"),
        quantity=Decimal("10.0"),
        placed_at=datetime.now(UTC),
    )


@pytest.fixture
def limit_sell_order():
    return Order(
        id=UUID("7a89806f-4435-47b5-b475-ff535d1c4bc9"),
        contract_id=ContractCode.UK_BL_MAR_25,
        trader_id=UUID("fe4f4479-6740-4103-9fb4-13f562b52b85"),
        side=OrderSide.SELL,
        type=OrderType.LIMIT,
        price=Decimal("100.0"),
        quantity=Decimal("10.0"),
        placed_at=datetime.now(UTC),
    )


@pytest.fixture
def second_limit_sell_order():
    return Order(
        id=UUID("7ec5a9b7-fc70-4056-802a-b466b5f6a162"),
        contract_id=ContractCode.UK_BL_MAR_25,
        trader_id=UUID("fe4f4479-6740-4103-9fb4-13f562b52b85"),
        side=OrderSide.SELL,
        type=OrderType.LIMIT,
        price=Decimal("100.0"),
        quantity=Decimal("15.0"),
        placed_at=datetime.now(UTC),
    )


# Route testing


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app=create_app()) as client:
        yield client
