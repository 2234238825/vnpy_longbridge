from pathlib import Path
from vnpy.trader.app import BaseApp
from vnpy.trader.constant import Direction
from vnpy.trader.object import TickData, BarData, TradeData, OrderData
from vnpy.trader.utility import BarGenerator, ArrayManager

from .base import APP_NAME, StopOrder
from .engine import CtaEngine
from .template import CtaTemplate, CtaSignal, TargetPosTemplate

class LbStrategyApp(BaseApp):
    app_name: str = APP_NAME
    app_module: str = "vnpy_longbridge.lb_strategy_app"
    app_path: Path = Path(__file__).parent
    display_name: str = "LB策略"
    engine_class: type[CtaEngine] = CtaEngine
    widget_name: str = "CtaManager"
    icon_name: str = str(app_path.joinpath("ui", "cta.ico"))