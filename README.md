# VeighNa框架的长桥证券(LongBridge)交易网关


![](https://github.com/BrokerQL/vnpy_longbridge/assets/1175306/f4d2774f-f9e3-4dc8-b67f-585be44b5978)

## 说明

基于长桥证券 Python SDK 开发的 VN.PY 交易网关和数据源。

## 环境要求

### 操作系统与 Python

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows / macOS / Linux |
| Python | 推荐 3.12（项目规范），代码使用 3.10+ 新语法，需 ≥ 3.10 |
| 发行版 | 推荐 [VeighNa Studio](https://www.vnpy.com)（自带 vnpy 完整环境）或手动搭建 |

### 核心依赖

| 依赖 | 版本（当前环境） | 用途 |
|------|------|------|
| vnpy | 4.3.0 | 交易框架主引擎、事件引擎 |
| longbridge | 4.0.5 | 长桥证券 OpenAPI SDK |
| fastapi | 0.127.0 | Web 交易页面后端（可选） |
| uvicorn | 0.40.0 | ASGI 服务器（可选） |
| numpy / pandas | 2.2.3 | 策略指标计算 |

### 账户要求

- 一个**长桥证券账户**（支持模拟盘 Sandbox，`build_config_from_setting()` 中 `Config.is_sandbox = True`）
- 在[长桥 OpenAPI 开发者平台](https://open.longbridge.com)注册开发者账户，配置 OAuth 2.0 认证获取 `client_id`（配置方式见 `script/vnpy_longbridge源码分析.md` 顶部）
- 行情权限：订阅实时报价会消耗长桥行情订阅额度；仅加载合约（`load_contract`）不消耗

### 启动方式

本项目有两种启动入口，任选其一：

1. **Qt 图形界面**：`python script/run.py`，用于日常监控与策略管理
2. **Web 交易页面**：`python script/web_server.py`，浏览器访问 `http://localhost:8000`，支持远程访问、策略启停、手动下单（详见 `script/vnpy_longbridge源码分析.md` 的"Web 交易页面"一节）

首次运行会触发 OAuth 授权：控制台打印授权 URL，浏览器打开完成授权后 Token 自动持久化（Windows 存于 `%USERPROFILE%\.longbridge\openapi\tokens\`），过期自动刷新。

## 安装

安装环境推荐基于3.8.0版本以上的【[**VeighNa Studio**](https://www.vnpy.com)】。


### 安装 vnpy_longbridge

直接使用 pip 命令：

```
pip install git+ssh://git@github.com/BrokerQL/vnpy_longbridge.git
```

或者下载源代码后，解压后在 cmd/shell 中运行：

```
pip install .
```

## 使用

以脚本方式启动（script/run.py）：

```
from vnpy.event import EventEngine
from vnpy.trader.constant import Currency
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import create_qapp, MainWindow

from vnpy_longbridge import LongBridgeGateway


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
            # 订阅行情
            lb_gw.subscribe_symbols(["SPY.US", "QQQ.US", "NVDA.US"])
            # 加载合约
            lb_gw.load_contract(["NVDA.US", "ARM.US"])

        lb_gw.after_connect = subscribe

    main_window = MainWindow(main_engine, event_engine)
    main_window.showMaximized()

    qapp.exec()


if __name__ == "__main__":
    main()
```

首次登录 LongBridge 前需在全局配置中[配置开发者账户](https://open.longportapp.com/docs/getting-started#配置开发者账户)，保存 App Key, App Secret, Access Token 等信息。

![](https://github.com/BrokerQL/vnpy_longbridge/assets/1175306/628da5cf-7473-495c-82aa-1b504e31fc72)

## 后续计划

列一下以后完善这个项目需要做的事，欢迎贡献！

### 实盘安全（最优先）

【重要，请求帮助】Web 页面目前没有鉴权，监听在 `0.0.0.0:8000`，局域网里任何人都能连上来下单。自用没问题，但要对外开放或实盘跑就是个隐患。我打算加个简单的口令/token，您有成熟方案欢迎提 issue！

实盘风控目前是零：没有单笔限额、没有最大持仓、没有撤单熔断。`vnpy_riskmanager` 虽然装了但一直没接入。实盘前必须补上，这是我最心虚的一块。

实盘链路我只在模拟盘验证过，真实下单（尤其市价单）没实跑过，希望有实盘经验的朋友帮忙踩坑。

### 策略与回测

`strategies` 里 8 个策略还 `from vnpy_ctastrategy import`，只有 `huhh` 和 `atr_rsi` 改成了本地模板，导致这些策略在本地引擎里加载不进来。这个模板混用问题拖了很久，一直没腾出时间统一。

回测目前只有 Qt 界面，Web 端还拉不了回测。我在想做 Web 回测页面，顺便把参数优化和绩效曲线（收益/回撤/夏普）可视化出来。

### 数据

数据服务（`data_service`）刚搭好，目前只有长桥一个源、日线、美股为主。A股数据、分钟线都还没排上日程。

### 测试与工程

`tests/` 目录到现在都是空的——CLAUDE.md 里写着 `pytest tests/`，其实根本没有测试，全靠手工验证，每次改代码都有点心虚。

订单和成交目前靠轮询（约 4 秒一次），实时性有限。长桥如果能做推送就好了，这块还没调研。

### 基础设施

断线重连、异常告警、信号通知（成交/触发推到邮件或微信）都还没做。把系统部署成常驻服务也没安排。

### 贡献指南

- **分支**：基于 `feature/strategy` 分支开发
- **规范**：见 `CLAUDE.md` —— Python 3.12、使用 pathlib、优先简单实现、不允许无意义抽象、修改前先给 implementation plan
- **文档**：源码分析见 `script/vnpy_longbridge源码分析.md`
