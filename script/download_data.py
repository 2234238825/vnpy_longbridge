"""download_data.py — 将长桥历史K线下载到本地数据库

用法：
    python script/download_data.py AAPL SMART DAILY 2023-01-01 2024-01-01
    python script/download_data.py 00700 SEHK DAILY 2023-01-01 2024-01-01

交易所：SMART(美股) / SEHK(港股)
周期：  MINUTE / HOUR / DAILY / WEEKLY
"""

import argparse
from datetime import datetime

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import get_database
from vnpy.trader.object import HistoryRequest

from vnpy_longbridge.longbridge_datafeed import LongBridgeDatafeed


def download(symbol: str, exchange: str, interval: str, start: str, end: str) -> None:
    """下载指定范围的历史K线到本地数据库。"""
    datafeed = LongBridgeDatafeed()
    datafeed.init(print)

    database = get_database()

    req = HistoryRequest(
        symbol=symbol,
        exchange=Exchange[exchange.upper()],
        interval=Interval[interval.upper()],
        start=datetime.strptime(start, "%Y-%m-%d"),
        end=datetime.strptime(end, "%Y-%m-%d"),
    )

    print(f"开始下载 {symbol}.{exchange.upper()} {interval.upper()} "
          f"{start} ~ {end}")
    bars = datafeed.query_bar_history(req, print)
    print(f"长桥返回 {len(bars)} 根K线")

    if bars:
        result = database.save_bar_data(bars)
        print(f"入库结果：{'成功' if result else '失败'}，共 {len(bars)} 根")
    else:
        print("无数据，未入库")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="下载长桥历史K线到本地数据库")
    parser.add_argument("symbol", help="合约代码，如 AAPL")
    parser.add_argument("exchange", help="交易所：SMART(美股) / SEHK(港股)")
    parser.add_argument("interval", help="周期：MINUTE / HOUR / DAILY / WEEKLY")
    parser.add_argument("start", help="起始日期，如 2023-01-01")
    parser.add_argument("end", help="结束日期，如 2024-01-01")
    args = parser.parse_args()

    download(args.symbol, args.exchange, args.interval, args.start, args.end)
