
# huhh_strategy
 策略逻辑

  每根日线 bar → 累积进 ArrayManager → 算出 20 日均价 (ma_value)
                   ↓
  盘中每个 tick → 实时价 < 20日均价 且 无持仓 → 买入

  关键点讲解（学习用）

  1. 均线怎么算的 — on_init 里 load_bar(40, interval=Interval.DAILY) 加载 40 天日线，on_bar 逐根喂进 ArrayManager，累积满 20 根后 self.am.sma(20) 得到 20 日均价。

  2. "实时价"和"均价"分两条路 — 均价来自日线（on_bar），实时价来自行情（on_tick 的 tick.last_price）。这两个回调是独立的，策略本质就是拿"实时的价"和"历史的均线"比较。

  3. 为什么判断 self.pos == 0 — 避免重复买入，持有中就不再加仓。

  4. 变量 vs 参数 — ma_window、fixed_size 放 parameters（启动前可调），ma_value、last_price 放 variables（会实时显示在 GUI 的变量监控里）。

  两点说明

  - buy 是限价单，挂 last_price 若价格继续往下可能不成交。想确保成交，可以改成卖一价：price = tick.ask_price_1 if tick.ask_price_1 > 0 else tick.last_price
  - 策略引擎只把 EVENT_TICK 推给策略，日线 bar 只在初始化时回放，所以 ma_value 是启动时算好的 20 日均价，盘中不变——对"过去20天平均"的需求是准确的。

  加载时引擎会扫描到这个策略类 HuhhStrategy，在 Web 页面的"添加策略"下拉里就能选到。