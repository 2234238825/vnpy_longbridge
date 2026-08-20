from .base import PortfolioAdapter, PortfolioPosition


class ManualAdapter(PortfolioAdapter):
    """MVP 手工录入适配器；真实持仓以本系统账本为准。"""

    def fetch_positions(self) -> list[PortfolioPosition]:
        return []

