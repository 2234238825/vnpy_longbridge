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
- 在[长桥 OpenAPI 开发者平台](https://open.longbridge.com)注册开发者账户，配置 OAuth 2.0 认证获取 `client_id`（配置方式见 `script/doc.md` 顶部）
- 行情权限：订阅实时报价会消耗长桥行情订阅额度；仅加载合约（`load_contract`）不消耗

### 启动方式

本项目有两种启动入口，任选其一：

1. **Qt 图形界面**：`python script/run.py`，用于日常监控与策略管理
2. **Web 交易页面**：`python script/web_server.py`，浏览器访问 `http://localhost:8000`，支持远程访问、策略启停、手动下单（详见 `script/doc.md` 的"Web 交易页面"一节）

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
