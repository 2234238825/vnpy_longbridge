


from pathlib import Path

from vnpy.trader.app import BaseApp
from vnpy.trader.constant import Direction
from vnpy.trader.object import TickData, BarData, TradeData, OrderData
from vnpy.trader.utility import BarGenerator, ArrayManager

from .base import APP_NAME, StopOrder
from .engine import CtaEngine
from .template import CtaTemplate, CtaSignal, TargetPosTemplate
from .backtester.backtesting import BacktestingEngine, OptimizationSetting
from .backtester.engine import BacktesterEngine, APP_NAME as BACKTESTER_APP_NAME


__all__ = [
    "APP_NAME",
    "CtaEngine",
    "CtaTemplate",
    "CtaSignal",
    "TargetPosTemplate",
    "StopOrder",
    "Direction",
    "TickData",
    "BarData",
    "TradeData",
    "OrderData",
    "BarGenerator",
    "ArrayManager",
    "LbStrategyApp",
    "BacktestingEngine",
    "OptimizationSetting",
    "BacktesterEngine",
    "CtaBacktesterApp",
]


__version__ = "1.4.0"


class LbStrategyApp(BaseApp):
    """"""
    from vnpy_ctastrategy.locale import _

    app_name: str = APP_NAME
    app_module: str = "vnpy_longbridge.lb_strategy_app"
    app_path: Path = Path(__file__).parent
    display_name: str = _("LB策略")
    engine_class: type[CtaEngine] = CtaEngine
    widget_name: str = "CtaManager"
    icon_name: str = str(app_path.joinpath("ui", "cta.ico"))


class CtaBacktesterApp(BaseApp):
    """"""

    app_name: str = BACKTESTER_APP_NAME
    app_module: str = "vnpy_longbridge.lb_strategy_app"
    app_path: Path = Path(__file__).parent
    display_name: str = "LB回测"
    engine_class: type[BacktesterEngine] = BacktesterEngine
    widget_name: str = "BacktesterManager"
    icon_name: str = str(app_path.joinpath("backtester", "ui", "backtester.ico"))
