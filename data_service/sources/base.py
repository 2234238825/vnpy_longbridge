"""数据源统一接口。新增数据源只需实现本抽象基类。"""
from abc import ABC, abstractmethod

from vnpy.trader.object import HistoryRequest, BarData


class DataSource(ABC):
    """行情数据源抽象接口。"""

    name: str = ""

    @abstractmethod
    def query_bar_history(self, req: HistoryRequest) -> list[BarData]:
        """查询历史K线，返回 BarData 列表。"""
        ...

    def close(self) -> None:
        """关闭连接，默认不操作。"""
        return
