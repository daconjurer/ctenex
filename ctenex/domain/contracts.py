from datetime import datetime
from decimal import Decimal
from enum import Enum

from ctenex.domain.entities import Commodity, DeliveryPeriod
from ctenex.domain.order_book.contract.model import Contract


class ContractCode(str, Enum):
    UK_BL_MAR_25 = "UK-BL-MAR-25"


class ContractBaselineMarch2025(Contract):
    id: str = ContractCode.UK_BL_MAR_25
    commodity: Commodity = Commodity.POWER
    delivery_period: DeliveryPeriod = DeliveryPeriod.MONTHLY
    start_date: datetime = datetime(2025, 3, 1)
    end_date: datetime = datetime(2025, 3, 31)
    location: str = "GB"
    tick_size: Decimal = Decimal("0.01")
    contract_size: Decimal = Decimal("1.0")
