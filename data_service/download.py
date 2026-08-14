"""data_service 统一下载入口：历史K线下载到本地数据库。

用法：
    python download.py                                 # 批量下载内置美股清单（默认长桥、日线）
    python download.py --symbols AAPL,MSFT             # 指定标的
    python download.py --symbols 00700 --exchange SEHK # 港股
    python download.py --interval MINUTE               # 分钟线
    python download.py --source longbridge             # 指定数据源

说明：内置清单是覆盖主要板块的知名大盘股（非精确实时市值排名），可按需增删。
      指数用 ETF 代表（SPY=标普500、QQQ=纳斯达克100）。
      重复下载同一区间是幂等的（数据库 upsert），不会产生重复行。
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# 保证无论从哪个目录运行都能 import sources 包
sys.path.insert(0, str(Path(__file__).resolve().parent))

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import get_database
from vnpy.trader.object import HistoryRequest

from sources import get_source

# 美股核心标的清单（覆盖主要板块，非精确实时市值排名，可按需增删）
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


def download_one(source, database, symbol, exchange, interval, start, end) -> int:
    """下载单只标的，返回入库根数（0 表示失败）。"""
    req = HistoryRequest(
        symbol=symbol,
        exchange=Exchange[exchange],
        interval=Interval[interval],
        start=start,
        end=end,
    )
    bars = source.query_bar_history(req)
    if not bars:
        return 0
    ok = database.save_bar_data(bars)
    return len(bars) if ok else 0


def main(args) -> None:
    source = get_source(args.source)
    database = get_database()

    symbols = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else UNIVERSE
    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d")

    print(f"数据源 {args.source}：{len(symbols)} 只标的，"
          f"{args.exchange} {args.interval}，{args.start} ~ {args.end}")
    ok_count = 0
    total_bars = 0

    for i, symbol in enumerate(symbols, 1):
        try:
            n = download_one(source, database, symbol, args.exchange, args.interval, start, end)
            if n:
                ok_count += 1
                total_bars += n
                print(f"[{i}/{len(symbols)}] {symbol}: {n} 根 入库成功")
            else:
                print(f"[{i}/{len(symbols)}] {symbol}: 无数据或失败")
        except Exception as e:
            print(f"[{i}/{len(symbols)}] {symbol}: 异常 {e}")

    source.close()
    print(f"完成：成功 {ok_count}/{len(symbols)} 只，共入库 {total_bars} 根")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="下载历史K线到本地数据库")
    parser.add_argument("--source", default="longbridge", help="数据源：longbridge")
    parser.add_argument("--symbols", help="逗号分隔的代码（如 AAPL,MSFT），默认使用内置核心清单")
    parser.add_argument("--exchange", default="SMART", help="交易所：SMART(美股) / SEHK(港股)")
    parser.add_argument("--interval", default="DAILY", help="周期：MINUTE / HOUR / DAILY / WEEKLY")
    parser.add_argument("--start", default="2010-01-01", help="起始日期 YYYY-MM-DD")
    parser.add_argument("--end", default=datetime.now().strftime("%Y-%m-%d"), help="结束日期 YYYY-MM-DD")
    args = parser.parse_args()

    main(args)
