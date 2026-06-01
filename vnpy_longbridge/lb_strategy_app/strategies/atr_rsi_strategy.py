import numpy as np

from vnpy_longbridge.lb_strategy_app import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)


class AtrRsiStrategy(CtaTemplate):
    """"""

    author = "用Python的huhh交易员"

    atr_length: int = 22
    atr_ma_length: int = 10
    rsi_length: int = 5
    rsi_entry: int = 16
    trailing_percent: float = 0.8
    fixed_size: int = 1

    atr_value: float = 0
    atr_ma: float = 0
    rsi_value: float = 0
    rsi_buy: float = 0
    rsi_sell: float = 0
    intra_trade_high: float = 0
    intra_trade_low: float = 0

    parameters = [
        "atr_length",
        "atr_ma_length",
        "rsi_length",
        "rsi_entry",
        "trailing_percent",
        "fixed_size"
    ]
    variables = [
        "atr_value",
        "atr_ma",
        "rsi_value",
        "rsi_buy",
        "rsi_sell",
        "intra_trade_high",
        "intra_trade_low"
    ]

    def on_init(self) -> None:
        """
        Callback when strategy is inited.
        """
        self.write_log("huhh策略初始化")

        self.bg: BarGenerator = BarGenerator(self.on_bar)
        self.am: ArrayManager = ArrayManager()

        self.rsi_buy = 50 + self.rsi_entry
        self.rsi_sell = 50 - self.rsi_entry

        self.load_bar(10)

    def on_start(self) -> None:
        """
        Callback when strategy is started.
        """
        self.write_log("huhh策略启动")

    def on_stop(self) -> None:
        """
        Callback when strategy is stopped.
        """
        self.write_log("huhh策略停止")

    def on_tick(self, tick: TickData) -> None:
        """
        Callback of new tick data update.
        """
        self.write_log("huhh on tick")
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData) -> None:
        """
        Callback of new bar data update.

        核心流程（ATR + RSI 趋势跟踪策略）：
        1. 撤销所有旧订单（新K线 = 重新评估）
        2. 更新 ArrayManager，积累K线数据
        3. 计算 ATR / ATR_MA / RSI 三个核心指标
        4. 空仓时：ATR扩张 + RSI极端值 → 开仓（多/空对称）
        5. 持仓时：移动止损跟踪利润，让利润奔跑
        6. 推送状态更新到 GUI
        """

        # ============================================================
        # 第1步：撤销所有未成交的工作订单
        # 新Bar代表新的市场状态，旧的限价单/止损单锚点已失效
        # ============================================================
        self.cancel_all()

        # ============================================================
        # 第2步：更新数据管理器 & 就绪检查
        # ArrayManager 内部维护一个固定长度的价格序列队列
        # am.inited 在积累足够K线后（默认100根）才为 True
        # ============================================================
        am: ArrayManager = self.am
        am.update_bar(bar)
        if not am.inited:
            self.write_log("数据不足，无法计算指标，直接返回")
            return  # 数据不足，无法计算指标，直接返回

        # ============================================================
        # 第3步：计算核心指标
        #
        # atr_array:  22周期ATR的完整序列（ndarray）
        #             ATR = Average True Range，衡量市场波动率
        # atr_value:  最新的ATR值（序列最后一个元素）
        # atr_ma:     最近10根ATR的移动均线
        #             → 作为"波动率基线"，用于判断波动是否在扩张
        # rsi_value:  5周期RSI（Relative Strength Index）
        #             → 短周期RSI对价格变化更敏感，适合捕捉动量
        #
        # 指标间的协作关系：
        # - ATR > ATR_MA → 波动率扩张，市场进入趋势行情 → 允许入场
        # - RSI 极端值 → 动量确认方向（强势做多/弱势做空）
        # ============================================================
        atr_array: np.ndarray = am.atr(self.atr_length, array=True)
        self.atr_value = atr_array[-1]                                 # 最新ATR值
        self.atr_ma = atr_array[-self.atr_ma_length:].mean()          # ATR的10周期均线（波动率基线）
        self.rsi_value = am.rsi(self.rsi_length)                       # 5周期RSI

        # ============================================================
        # 第4步：空仓 → 判断是否开仓
        #
        # 入场必须同时满足两个条件：
        #   条件A：atr_value > atr_ma（波动率在扩张，市场在"动"，不是横盘）
        #   条件B：RSI突破极端区间
        #          - RSI > rsi_buy(66)  → 强势上涨，做多
        #          - RSI < rsi_sell(34) → 弱势下跌，做空
        #
        # 对称设计：rsi_buy = 50+16, rsi_sell = 50-16，多空完全对称
        #
        # 入场方式：限价单（close_price ± 5）
        #   - 做多：挂略高于当前价的买单，确保成交
        #   - 做空：挂略低于当前价的卖单，确保成交
        #   - 加减5个点是为了避免市价滑点，同时保证较高的成交率
        # ============================================================
        if self.pos == 0:
            # 初始化持仓期间的极值跟踪（移动止损的锚点）
            self.intra_trade_high = bar.high_price
            self.intra_trade_low = bar.low_price

            if self.atr_value > self.atr_ma:                # 波动率扩张 = 趋势确认
                if self.rsi_value > self.rsi_buy:            # RSI > 66，强势上涨
                    self.buy(bar.close_price + 5, self.fixed_size)
                elif self.rsi_value < self.rsi_sell:         # RSI < 34，弱势下跌
                    self.short(bar.close_price - 5, self.fixed_size)

        # ============================================================
        # 第5步：多头持仓 → 移动止损
        #
        # 止损价 = 持仓以来最高价 × (1 - trailing_percent/100)
        # 即：从最高点回撤 0.8% 触发止损
        #
        # 例如：最高价100，止损价 = 100 × 0.992 = 99.2
        # 价格涨到110 → 止损线自动上移到 110 × 0.992 = 109.12
        # 价格涨到120 → 止损线自动上移到 120 × 0.992 = 119.04
        #
        # 这样随着价格不断上涨，止损线自动跟随上移，
        # 既保护了已有利润，又不限制上行空间（让利润奔跑）
        #
        # stop=True：止损单（Stop Order），价格跌破止损价时触发市价平仓
        # ============================================================
        elif self.pos > 0:
            # 追踪持仓以来的最高价（移动止损的锚点）
            self.intra_trade_high = max(self.intra_trade_high, bar.high_price)
            self.intra_trade_low = bar.low_price     # 预留：可能用于做多转做空的反手逻辑

            # 计算移动止损价：从最高点回撤 trailing_percent%
            long_stop: float = self.intra_trade_high * (1 - self.trailing_percent / 100)
            self.sell(long_stop, abs(self.pos), stop=True)

        # ============================================================
        # 第6步：空头持仓 → 移动止损（多头镜像）
        #
        # 止损价 = 持仓以来最低价 × (1 + trailing_percent/100)
        # 即：从最低点反弹 0.8% 触发止损
        #
        # 例如：最低价100，止损价 = 100 × 1.008 = 100.8
        # 价格跌到90 → 止损线自动下移到 90 × 1.008 = 90.72
        # 价格跌到80 → 止损线自动下移到 80 × 1.008 = 80.64
        #
        # 价格越跌止损线越下移，锁定空头利润
        # ============================================================
        elif self.pos < 0:
            # 追踪持仓以来的最低价（移动止损的锚点）
            self.intra_trade_low = min(self.intra_trade_low, bar.low_price)
            self.intra_trade_high = bar.high_price   # 预留：可能用于做空转做多的反手逻辑

            # 计算移动止损价：从最低点反弹 trailing_percent%
            short_stop: float = self.intra_trade_low * (1 + self.trailing_percent / 100)
            self.cover(short_stop, abs(self.pos), stop=True)

        # ============================================================
        # 第7步：推送策略状态更新到 GUI
        # 包括：指标值、持仓状态、订单信息等，供交易员实时监控
        # ============================================================
        self.put_event()

    def on_order(self, order: OrderData) -> None:
        """
        Callback of new order data update.
        """
        pass

    def on_trade(self, trade: TradeData) -> None:
        """
        Callback of new trade data update.
        """
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder) -> None:
        """
        Callback of stop order update.
        """
        pass
