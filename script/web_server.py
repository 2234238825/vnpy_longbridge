"""web_server.py — LongBridge Web Tr可以ader 启动脚本"""

from vnpy.event import EventEngine
from vnpy.trader.constant import Currency
from vnpy.trader.engine import MainEngine

from vnpy_longbridge import LongBridgeGateway
from vnpy_longbridge.lb_strategy_app.LbStrategyApp import LbStrategyApp
from vnpy_longbridge.lb_strategy_app.base import APP_NAME
from vnpy_longbridge.web import create_app

import uvicorn


def main():
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)

    gw = main_engine.add_gateway(LongBridgeGateway)
    if isinstance(gw, LongBridgeGateway):
        lb_gw: LongBridgeGateway = gw
        lb_gw.currency = Currency.USD
        lb_gw.main_engine = main_engine

        def subscribe():
            lb_gw.subscribe_symbols(["SPY.US", "QQQ.US", "NVDA.US", "02513.HK"])
            lb_gw.load_contract(["07709.HK", "ARM.US", "NVDA.US"])

        lb_gw.after_connect = subscribe
        gw.connect({})

    main_engine.add_app(LbStrategyApp)
    # GUI 版由 Qt 面板 CtaManager 调用 init_engine 加载策略；
    # Web 版没有 Qt 面板，需要手动初始化，否则策略类不会加载。
    cta_engine = main_engine.get_engine(APP_NAME)
    cta_engine.init_engine()

    app = create_app(main_engine, event_engine)
    uvicorn.run(app, host="0.0.0.0", port=8101)


if __name__ == "__main__":
    main()
