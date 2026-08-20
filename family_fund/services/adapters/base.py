from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PortfolioPosition:
    symbol: str
    quantity: Decimal
    market_price: Decimal
    currency: str


class PortfolioAdapter(ABC):
    """外部账户快照接口；基金会计服务不依赖具体券商。"""

    @abstractmethod
    def fetch_positions(self) -> list[PortfolioPosition]:
        raise NotImplementedError

