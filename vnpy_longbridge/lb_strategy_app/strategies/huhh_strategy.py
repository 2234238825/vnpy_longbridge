from vnpy.trader.constant import Interval

from vnpy_longbridge.lb_strategy_app import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
)


class HuhhStrategy(CtaTemplate):
    """以最近一次成交价为基准的均值回归策略（美股，分钟线）。

    买入：当前价相对上次成交价累计下跌超 buy_cum_drop_pct% → 买入 x*fixed_size 股。
    卖出：当前价相对上次成交价累计上涨超 sell_cum_rise_pct% → 卖出 x*fixed_size 股。
    每次成交后基准更新为成交价，需再跌/再涨超阈值才再次操作。
    首次无成交时以当天开盘价为基准。不限时间窗口、不限次数；挂单未成交时不重复下单。
    """

    author = "Counting stars trader"

    # ---- 参数（启动前可调）----
    fixed_size: int = 100            # 基础股数
    position_multiplier: float = 1   # 每次操作股数 = position_multiplier × fixed_size
    buy_cum_drop_pct: float = 2.0    # 相对上次成交累计跌幅超此百分比触发买入
    sell_cum_rise_pct: float = 5.0   # 相对上次成交累计涨幅超此百分比触发卖出

    # ---- 变量 ----
    last_operation_price: float = 0  # 上次操作成交价（基准价，首次=当天开盘价）
    cum_change: float = 0            # 累计涨跌幅（相对基准价）%
    last_price: float = 0            # 最新价
    active_orderids: set = set()     # 未成交的活跃订单，防止挂单期间重复下单

    parameters = [
        "fixed_size",
        "position_multiplier",
        "buy_cum_drop_pct",
        "sell_cum_rise_pct",
    ]
    variables = [
        "last_operation_price",
        "cum_change",
        "last_price",
        "active_orderids",
    ]

    def on_init(self) -> None:
        self.write_log(f"策略初始化，参数：{self.get_parameters()}")
        self.active_orderids = set()
        # 实盘：从 tick 合成 1 分钟 bar；回测直接喂分钟 bar 到 on_bar
        self.bg: BarGenerator = BarGenerator(self.on_bar)

    def on_start(self) -> None:
        self.write_log("策略启动")

    def on_stop(self) -> None:
        self.write_log("策略停止")

    def on_tick(self, tick: TickData) -> None:
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData) -> None:
        self.last_price = bar.close_price

        self._update_reference(bar)
        self._check_sell()
        self._check_buy()

        self.put_event()

    def _update_reference(self, bar: BarData) -> None:
        """更新累计涨跌幅。首次无基准时以当天开盘价为基准。"""
        if self.last_operation_price == 0:
            self.last_operation_price = bar.open_price

        self.cum_change = (
            (self.last_price - self.last_operation_price)
            / self.last_operation_price * 100
        )

    def _check_sell(self) -> None:
        """卖出：相对上次成交累计上涨超 sell_cum_rise_pct%。"""
        # 无持仓或已有挂单未成交时，不重复下单
        if self.pos <= 0 or self.active_orderids:
            return

        if self.cum_change >= self.sell_cum_rise_pct:
            # 卖出数量不超过当前持仓，避免超卖
            volume = min(self.position_multiplier * self.fixed_size, abs(self.pos))
            if volume <= 0:
                return
            vt_orderids = self.sell_market(volume)
            self.active_orderids.update(vt_orderids)
            self.write_log(
                f"触发卖出：累计{self.cum_change:.2f}%，卖 {volume} 股"
            )

    def _check_buy(self) -> None:
        """买入：相对上次成交累计下跌超 buy_cum_drop_pct%。"""
        # 已有挂单未成交时，不重复下单
        if self.active_orderids:
            return

        if self.cum_change <= -self.buy_cum_drop_pct:
            volume = self.position_multiplier * self.fixed_size
            vt_orderids = self.buy_market(volume)
            self.active_orderids.update(vt_orderids)
            self.write_log(
                f"触发买入：累计{self.cum_change:.2f}%，买 {volume} 股"
            )

    def on_trade(self, trade: TradeData) -> None:
        # 更新基准价为本次成交价，累计涨跌幅重新计算
        self.last_operation_price = trade.price
        self.write_log(f"成交 {trade.direction} {trade.volume} 股 @ {trade.price}")
        self.put_event()

    def on_order(self, order: OrderData) -> None:
        # 订单已成交/撤销（不再活跃）时释放挂单锁，允许下一次操作
        if order.vt_orderid in self.active_orderids and not order.is_active():
            self.active_orderids.discard(order.vt_orderid)

    def on_stop_order(self, stop_order: StopOrder) -> None:
        pass
