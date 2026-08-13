"""download_market.py — 批量下载美股核心标的日线到本地数据库

用法：
    python script/download_market.py                    # 下载内置清单
    python script/download_market.py --symbols AAPL,MSFT  # 只下载指定标的
    python script/download_market.py --start 2015-01-01   # 自定义起始日期

说明：内置清单是覆盖主要板块的知名大盘股（非精确实时市值排名），可按需增删。
      指数用 ETF 代表（SPY=标普500、QQQ=纳斯达克100），可交易且历史完整。
"""

import argparse
from datetime import datetime

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import get_database
from vnpy.trader.object import HistoryRequest

from vnpy_longbridge.longbridge_datafeed import LongBridgeDatafeed

# 核心标的清单（覆盖主要板块，非精确实时市值排名，可按需增删）
UNIVERSE = [
    # 美股七姐妹
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    # 台积电 ADR
    "TSM",
    # 指数 ETF（用 ETF 代表指数）
    "SPY",   # 标普500
    "QQQ",   # 纳斯达克100
    # 金融
    "JPM", "BAC", "WFC", "GS", "MS", "V", "MA", "AXP",
    # 科技
    "AVGO", "ORCL", "CRM", "ADBE", "INTC", "AMD", "CSCO", "QCOM", "TXN", "NFLX", "IBM",
    # 医疗
    "UNH", "JNJ", "PFE", "MRK", "ABBV", "LLY", "TMO", "AMGN",
    # 消费
    "WMT", "COST", "PG", "KO", "PEP", "MCD", "NKE", "HD", "DIS", "SBUX", "TGT",
    # 能源 / 工业
    "XOM", "CVX", "GE", "CAT", "BA", "HON", "UPS", "LIN", "DE", "MMM",
    # 通信
    "T", "VZ", "TMUS",
]


def download_one(
    datafeed: LongBridgeDatafeed,
    database,
    symbol: str,
    exchange: str,
    interval: str,
    start: datetime,
    end: datetime,
) -> int:
    """下载单只标的，返回入库根数（0 表示失败）。"""
    req = HistoryRequest(
        symbol=symbol,
        exchange=Exchange[exchange],
        interval=Interval[interval],
        start=start,
        end=end,
    )
    bars = datafeed.query_bar_history(req, print)
    if not bars:
        return 0
    ok = database.save_bar_data(bars)
    return len(bars) if ok else 0


def main(args) -> None:
    datafeed = LongBridgeDatafeed()
    datafeed.init(print)
    database = get_database()

    symbols = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else UNIVERSE
    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d")

    print(f"共 {len(symbols)} 只标的，区间 {args.start} ~ {args.end}，日线入库")
    ok_count = 0
    total_bars = 0

    for i, symbol in enumerate(symbols, 1):
        try:
            n = download_one(datafeed, database, symbol, "SMART", "DAILY", start, end)
            if n:
                ok_count += 1
                total_bars += n
                print(f"[{i}/{len(symbols)}] {symbol}: {n} 根 入库成功")
            else:
                print(f"[{i}/{len(symbols)}] {symbol}: 无数据或失败")
        except Exception as e:
            print(f"[{i}/{len(symbols)}] {symbol}: 异常 {e}")

    print(f"完成：成功 {ok_count}/{len(symbols)} 只，共入库 {total_bars} 根")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="批量下载美股核心标的日线到本地数据库")
    parser.add_argument("--symbols", help="逗号分隔的代码（如 AAPL,MSFT），默认使用内置核心清单")
    parser.add_argument("--start", default="2010-01-01", help="起始日期 YYYY-MM-DD")
    parser.add_argument("--end", default=datetime.now().strftime("%Y-%m-%d"), help="结束日期 YYYY-MM-DD")
    args = parser.parse_args()

    main(args)
