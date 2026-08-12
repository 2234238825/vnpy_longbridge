from vnpy.trader.constant import Interval

from vnpy_longbridge.lb_strategy_app import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    ArrayManager,
)


class HuhhStrategy(CtaTemplate):
    """当天的实时价格低于过去20天均价时买入。"""

    author = "Counting stars trader"

    ma_window: int = 20      # 过去 N 天均价周期
    fixed_size: int = 3    # 每次买入股数

    ma_value: float = 0      # 过去 ma_window 天均价
    last_price: float = 0    # 最新实时价
    entry_sent: bool = False  # 已触发买入，防止回测中 pos 延迟更新导致的重复下单

    parameters = ["ma_window", "fixed_size"]
    variables = ["ma_value", "last_price", "entry_sent"]

    def on_init(self) -> None:
        self.write_log("策略初始化")
        self.entry_sent = False
        # ArrayManager 用于累积历史 bar 并计算指标
        self.am: ArrayManager = ArrayManager(self.ma_window + 1)
        # 加载 40 天日线，够算出 20 日均价；interval 指定日线
        self.load_bar(40, interval=Interval.DAILY)

    def on_start(self) -> None:
        self.write_log("策略启动")

    def on_stop(self) -> None:
        self.write_log("策略停止")

    def on_bar(self, bar: BarData) -> None:
        # 每根日线进来就累积，满了 ma_window 根后 sma 才有值
        self.am.update_bar(bar)
        if not self.am.inited:
            return
        self.ma_value = self.am.sma(self.ma_window)
        # bar 收盘价即"实时价"，回测（BAR 模式）从这里判断
        self.last_price = bar.close_price
        self.trade_signal()

    def on_tick(self, tick: TickData) -> None:
        self.last_price = tick.last_price
        self.trade_signal()

    def trade_signal(self) -> None:
        """核心条件：实时价低于过去20天均价，且当前没有持仓 → 买入。"""
        # on_init 阶段（trading=False）不下单也不置标记
        if self.ma_value <= 0 or not self.trading:
            return
        if not self.entry_sent and self.last_price < self.ma_value:
            self.entry_sent = True
            self.buy_market(self.fixed_size)
            self.write_log(
                f"触发买入：现价 {self.last_price} < 均价 {self.ma_value:.2f}"
            )
        self.put_event()

    def on_trade(self, trade: TradeData) -> None:
        self.write_log(f"成交 {trade.volume} 股 @ {trade.price}")
        self.put_event()

    def on_order(self, order: OrderData) -> None:
        pass

    def on_stop_order(self, stop_order: StopOrder) -> None:
        pass
