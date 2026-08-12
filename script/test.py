"""
test.py — 长桥交易网关测试脚本

功能：
  - 连接长桥模拟账户
  - 测试多种订单类型（限价/市价/止损）
  - 详细的 print 输出，方便观察每一步执行结果
"""

from vnpy.event import EventEngine
from vnpy.trader.constant import Currency, Direction, Exchange, OrderType, Offset
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import create_qapp, MainWindow
from vnpy.trader.object import OrderRequest
from typing import Callable

from vnpy_longbridge import LongBridgeGateway
from vnpy_longbridge.lb_strategy_app.LbStrategyApp import LbStrategyApp
from vnpy_longbridge.longbridge_gateway import convert_symbol_lb2vt


# ============================================================================
# 工具函数
# ============================================================================

def lb_symbol(code: str) -> tuple[str, Exchange]:
    """
    解析长桥格式 symbol -> vnpy 格式
    例如: "07709.HK" -> ("07709", Exchange.SEHK)
          "AAPL.US" -> ("AAPL", Exchange.SMART)
    """
    symbol, region = code.rsplit(".", 1)
    exchange_map = {"US": Exchange.SMART, "HK": Exchange.SEHK}
    return symbol, exchange_map[region]


def send_test_orders(lb_gw: LongBridgeGateway):
    """
    发送多种类型的测试订单，每个订单都带详细 print 输出。

    订单类型说明：
      LIMIT  — 限价单：指定价格，只有价格匹配才成交
      MARKET — 市价单：以当前市场最优价立即成交
      STOP   — 止损单：触发价到达后转为市价单（MIT = Market If Touched）
    """

    print("\n" + "=" * 60)
    print("  [INFO] 开始发送测试订单（模拟账户）")
    print("=" * 60 + "\n")

    # ────────────────────────────────────────
    # 测试1：限价买单 (LIMIT BUY OPEN)
    # ────────────────────────────────────────
    raw = "07709.HK"
    sym, ex = lb_symbol(raw)
    req = OrderRequest(
        symbol=sym,
        exchange=ex,
        direction=Direction.LONG,  # 买入
        type=OrderType.LIMIT,  # 限价
        volume=100,  # 100股
        price=5.0,  # 限价 $5.00
        offset=Offset.OPEN,  # 开仓
        reference="test_limit_buy",
    )
    print(f"[测试1] 限价买单 — {raw}")
    print(f"        入参: symbol={sym}, exchange={ex}, direction=LONG(买入)")
    print(f"              type=LIMIT(限价), volume=100, price=5.0, offset=OPEN(开仓)")
    try:
        oid = lb_gw.send_order(req)
        print(f"        结果: order_id = '{oid}' {'[OK] 成功' if oid else '[WARN] 被拒绝/忽略'}")
    except Exception as e:
        print(f"        结果: [ERR] 异常 — {e}")
    print()

    # ────────────────────────────────────────
    # 测试2：限价卖单 (LIMIT SELL CLOSE)
    # ────────────────────────────────────────
    req = OrderRequest(
        symbol=sym,
        exchange=ex,
        direction=Direction.SHORT,  # 卖出
        type=OrderType.LIMIT,  # 限价
        volume=50,  # 50股
        price=100.0,  # 限价 $100.00
        offset=Offset.CLOSE,  # 平仓
        reference="test_limit_sell",
    )
    print(f"[测试2] 限价卖单 — {raw}")
    print(f"        入参: symbol={sym}, exchange={ex}, direction=SHORT(卖出)")
    print(f"              type=LIMIT(限价), volume=50, price=100.0, offset=CLOSE(平仓)")
    try:
        oid = lb_gw.send_order(req)
        print(f"        结果: order_id = '{oid}' {'[OK] 成功' if oid else '[WARN] 被拒绝/忽略（可能无持仓可平）'}")
    except Exception as e:
        print(f"        结果: [ERR] 异常 — {e}")
    print()

    # ────────────────────────────────────────
    # 测试3：市价买单 (MARKET BUY OPEN)
    # ────────────────────────────────────────
    raw = "ARM.US"
    sym, ex = lb_symbol(raw)
    req = OrderRequest(
        symbol=sym,
        exchange=ex,
        direction=Direction.LONG,  # 买入
        type=OrderType.MARKET,  # 市价
        volume=10,  # 10股
        # 市价单 price 设 0，不依赖具体价格
        offset=Offset.OPEN,  # 开仓
        reference="test_market_buy",
    )
    print(f"[测试3] 市价买单 — {raw}")
    print(f"        入参: symbol={sym}, exchange={ex}, direction=LONG(买入)")
    print(f"              type=MARKET(市价), volume=10, price=不传(submitted_price=None), offset=OPEN(开仓)")
    try:
        oid = lb_gw.send_order(req)
        print(f"        结果: order_id = '{oid}' {'[OK] 成功' if oid else '[WARN] 被拒绝/忽略'}")
    except Exception as e:
        print(f"        结果: [ERR] 异常 — {e}")
    print()

    # ────────────────────────────────────────
    # 测试4：市价卖单 (MARKET SELL CLOSE)
    # ────────────────────────────────────────
    req = OrderRequest(
        symbol=sym,
        exchange=ex,
        direction=Direction.SHORT,  # 卖出
        type=OrderType.MARKET,  # 市价
        volume=10,  # 10股
        offset=Offset.CLOSE,  # 平仓
        reference="test_market_sell",
    )
    print(f"[测试4] 市价卖单 — {raw}")
    print(f"        入参: symbol={sym}, exchange={ex}, direction=SHORT(卖出)")
    print(f"              type=MARKET(市价), volume=10, offset=CLOSE(平仓)")
    try:
        oid = lb_gw.send_order(req)
        print(f"        结果: order_id = '{oid}' {'[OK] 成功' if oid else '[WARN] 被拒绝/忽略（可能无持仓可平）'}")
    except Exception as e:
        print(f"        结果: [ERR] 异常 — {e}")
    print()

    # ────────────────────────────────────────
    # 测试5：止损买单 (STOP BUY — MIT)
    # 当价格涨到触发价时，转为市价买单
    # ────────────────────────────────────────
    raw = "SPCX.US"
    sym, ex = lb_symbol(raw)
    req = OrderRequest(
        symbol=sym,
        exchange=ex,
        direction=Direction.LONG,  # 买入
        type=OrderType.STOP,  # 止损/触价单
        volume=10,  # 10股
        price=999.0,  # 触发价设很高（模拟中不会触发）
        offset=Offset.OPEN,  # 开仓
        reference="test_stop_buy",
    )
    print(f"[测试5] 止损买单 — {raw}")
    print(f"        入参: symbol={sym}, exchange={ex}, direction=LONG(买入)")
    print(f"              type=STOP(止损/触价), volume=10, trigger_price=999.0(触发价), offset=OPEN(开仓)")
    print(f"        说明: 当价格 >= 999.0 时才触发，模拟盘中基本不会成交")
    try:
        oid = lb_gw.send_order(req)
        print(f"        结果: order_id = '{oid}' {'[OK] 成功' if oid else '[WARN] 被拒绝/忽略'}")
    except Exception as e:
        print(f"        结果: [ERR] 异常 — {e}")
    print()

    print("=" * 60)
    print("  [OK] 测试订单全部发送完毕")
    print("     （'被忽略' 可能是因为同一symbol已有挂单，长桥不允许重复下单）")
    print("=" * 60 + "\n")


def run_gui(main_engine: MainEngine, event_engine: EventEngine) -> None:
    """启动 GUI 主窗口。"""
    main_engine.add_app(LbStrategyApp)

    main_window = MainWindow(main_engine, event_engine)
    main_window.showNormal()

    qapp.exec()

    print(">>> 程序已退出。")


# ============================================================================
# 主入口
# ============================================================================

if __name__ == "__main__":

    print(">>> 创建 QApplication ...")
    qapp = create_qapp()

    print(">>> 初始化事件引擎 & 主引擎 ...")
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)

    print(">>> 添加长桥网关 ...")
    gw = main_engine.add_gateway(LongBridgeGateway)

    if isinstance(gw, LongBridgeGateway):
        lb_gw: LongBridgeGateway = gw
        lb_gw.currency = Currency.USD
        lb_gw.main_engine = main_engine

        def on_gateway_connected():
            """
            网关连接成功后的回调。
            此时 trade_ctx / quote_ctx 已经初始化完毕。
            """
            print("\n>>> [CONNECTED] 网关已连接！")
            print(">>> 订阅行情 & 加载合约 ...")
            lb_gw.subscribe_symbols(["SPY.US", "QQQ.US", "SPCX.US"])

            print(">>> 行情订阅完成，准备发送测试订单")
            send_test_orders(lb_gw)

        lb_gw.after_connect = on_gateway_connected


    print(">>> [START] 启动 GUI 事件循环 (qapp.exec) ...")
    run_gui(main_engine, event_engine)
