"""长桥数据源实现。"""
from vnpy.trader.object import HistoryRequest, BarData

from vnpy_longbridge.longbridge_datafeed import LongBridgeDatafeed

from .base import DataSource


class LongBridgeSource(DataSource):
    """长桥证券历史K线数据源。"""

    name = "longbridge"

    def __init__(self) -> None:
        self.datafeed = LongBridgeDatafeed()
        self.datafeed.init(print)

    def query_bar_history(self, req: HistoryRequest) -> list[BarData]:
        return self.datafeed.query_bar_history(req, print)
