from vnpy.event import EventEngine
from vnpy.trader.constant import Currency
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import create_qapp, MainWindow

from vnpy_longbridge import LongBridgeGateway
from vnpy_ctabacktester import CtaBacktesterApp
from vnpy_ctastrategy import CtaStrategyApp
from vnpy_longbridge.lb_strategy_app.LbStrategyApp import LbStrategyApp

def main():
    qapp = create_qapp()

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

    main_engine.add_app(LbStrategyApp)
    main_window = MainWindow(main_engine, event_engine)
    main_window.showNormal()

    qapp.exec()


if __name__ == "__main__":
    main()
