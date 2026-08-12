from datetime import timedelta
from typing import Callable, Optional, List, Union

from longbridge.openapi import QuoteContext, Config, AdjustType
from vnpy.trader.datafeed import BaseDatafeed
from vnpy.trader.object import HistoryRequest, TickData, BarData
from .longbridge_gateway import convert_symbol_vt2lb, INTERVAL_MAP, SHARED_CONTEXT, convert_candlestick_bar, \
    build_config_from_setting

from vnpy_longbridge.lb_strategy_app.locale import _


class LongBridgeDatafeed(BaseDatafeed):
    default_name = "LongBridge"

    def __init__(self):
        self.inited = False
        self.quote_ctx: Union[QuoteContext, None] = None

    def init(self, output: Callable = print) -> bool:
        if self.inited:
            return True
        config = build_config_from_setting()
        if SHARED_CONTEXT.quote_ctx:
            self.quote_ctx = SHARED_CONTEXT.quote_ctx
        else:
            self.quote_ctx = SHARED_CONTEXT.quote_ctx = QuoteContext(config)
        self.inited = True
        return True

    def query_bar_history(self, req: HistoryRequest, output: Callable = print) -> Optional[List[BarData]]:

        if not self.inited:
            self.init(output)

        symbol = convert_symbol_vt2lb(req.symbol, req.exchange)
        interval = INTERVAL_MAP[req.interval]

        result = []
        end = req.end
        while True:
            # by_date 按日期范围取历史，单次约 1000 根，翻页往前拉取
            candlesticks = self.quote_ctx.history_candlesticks_by_date(
                symbol, interval, AdjustType.ForwardAdjust, start=req.start, end=end)
            if not candlesticks:
                break

            for bar in candlesticks:
                bar_data: BarData = convert_candlestick_bar(bar, req, self.default_name)
                if req.start <= bar_data.datetime <= req.end:
                    result.append(bar_data)

            # 已取到范围头则停止
            if len(candlesticks) < 1000:
                break
            # 翻页：end 设为最早一根 bar 的前一天
            earliest = candlesticks[0].timestamp
            if earliest <= req.start:
                break
            end = earliest - timedelta(days=1)

        result.sort(key=lambda bar: bar.datetime)
        return result

    def query_tick_history(self, req: HistoryRequest, output: Callable = print) -> Optional[List[TickData]]:
        return super().query_tick_history(req, output)
