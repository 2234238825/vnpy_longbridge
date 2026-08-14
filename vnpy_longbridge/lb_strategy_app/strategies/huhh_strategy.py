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

    # ---- 参数（启动前可调，显示在 GUI）----
    ma_window: int = 20       # 慢线均线周期（买入判断用）
    ma_fast_window: int = 5   # 快线均线周期
    fixed_size: int = 3       # 每次买入股数

    # ---- 均线 / 趋势（on_bar 里用历史K线计算）----
    ma_fast: float = 0            # 快线均线值（ma_fast_window 日均价）
    ma_value: float = 0           # 慢线均线值（ma_window 日均价）
    ma_diff: float = 0            # 快慢线差值 = 快线 - 慢线，>0 短期强于长期
    highest_high: float = 0       # 近 ma_window 日最高价（突破/通道判断）
    lowest_low: float = 0         # 近 ma_window 日最低价

    # ---- 波动率（on_bar 里用历史K线计算）----
    atr_value: float = 0          # 平均真实波幅 ATR，衡量波动大小

    # ---- 行情快照（on_tick 实时更新；回测时 on_bar 用K线数据填充）----
    last_price: float = 0         # 最新成交价（实盘=tick最新价，回测=收盘价）
    ask_price: float = 0          # 卖一价（实盘买入参考价）
    bid_price: float = 0          # 买一价（实盘卖出参考价）
    day_high: float = 0           # 当日最高价
    day_low: float = 0            # 当日最低价

    # ---- 状态标记（防止重复下单）----
    entry_sent: bool = False      # 已触发买入，防止回测中 pos 延迟更新导致的重复下单

    parameters = ["ma_window", "ma_fast_window", "fixed_size"]
    variables = [
        "ma_fast", "ma_value", "ma_diff",
        "highest_high", "lowest_low", "atr_value",
        "last_price", "ask_price", "bid_price",
        "day_high", "day_low",
        "entry_sent",
    ]

    def on_init(self) -> None:
        self.write_log("策略初始化")
        self.entry_sent = False
        # ArrayManager 累积历史K线，够算指标；ma_window+1 根缓存即够
        self.am: ArrayManager = ArrayManager(self.ma_window + 1)
        # 加载历史日线用于初始化指标（多留一些给 on_init 阶段）
        self.load_bar(40, interval=Interval.DAILY)

    def on_start(self) -> None:
        self.write_log("策略启动")

    def on_stop(self) -> None:
        self.write_log("策略停止")

    def on_bar(self, bar: BarData) -> None:
        self.am.update_bar(bar)
        if not self.am.inited:
            return

        # ---- 均线 / 趋势：基于历史K线 ----
        self.ma_fast = self.am.sma(self.ma_fast_window)
        self.ma_value = self.am.sma(self.ma_window)
        self.ma_diff = self.ma_fast - self.ma_value
        self.highest_high = self.am.high[-self.ma_window:].max()
        self.lowest_low = self.am.low[-self.ma_window:].min()

        # ---- 波动率 ----
        self.atr_value = self.am.atr(self.ma_window)

        # ---- 行情快照：回测（BAR 模式）没有 tick，用K线数据填充 ----
        self.last_price = bar.close_price
        self.day_high = bar.high_price
        self.day_low = bar.low_price

        self.trade_signal()

    def on_tick(self, tick: TickData) -> None:
        # ---- 行情快照：实盘每个 tick 更新 ----
        self.last_price = tick.last_price
        self.ask_price = tick.ask_price_1
        self.bid_price = tick.bid_price_1
        self.day_high = tick.high_price
        self.day_low = tick.low_price

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
