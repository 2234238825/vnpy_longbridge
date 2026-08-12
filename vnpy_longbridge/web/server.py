import asyncio
from contextlib import asynccontextmanager
from dataclasses import is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from vnpy.event import Event, EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.object import CancelRequest, OrderRequest, SubscribeRequest, HistoryRequest
from vnpy.trader.constant import Direction, Exchange, Interval, OrderType, Offset

from vnpy_longbridge.longbridge_gateway import HistoryRequest as LBHistoryRequest

from vnpy_longbridge.lb_strategy_app.base import (
    APP_NAME,
    EVENT_CTA_LOG,
    EVENT_CTA_STRATEGY,
    EVENT_CTA_STOPORDER,
)

_EVENT_PREFIXES = (
    "eTick.", "eOrder.", "eTrade.", "ePosition.", "eAccount.",
    "eLog", EVENT_CTA_LOG, EVENT_CTA_STRATEGY, EVENT_CTA_STOPORDER,
)

_ws_queues: list[asyncio.Queue] = []
_loop: asyncio.AbstractEventLoop | None = None


def to_serializable(obj: Any, depth: int = 0) -> Any:
    if depth > 5:
        return str(obj)
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj):
        return {k: to_serializable(v, depth + 1) for k, v in obj.__dict__.items()}
    if isinstance(obj, dict):
        return {str(k): to_serializable(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_serializable(x, depth + 1) for x in obj]
    return str(obj)


def _event_handler(event: Event) -> None:
    if not event.type.startswith(_EVENT_PREFIXES):
        return
    data = {"type": event.type, "data": to_serializable(event.data)}
    for q in _ws_queues:
        _loop.call_soon_threadsafe(q.put_nowait, data)


def _parse_exchange(value: str) -> Exchange:
    for ex in Exchange:
        if ex.value == value:
            return ex
    raise ValueError(f"Unknown exchange: {value}")


def create_app(main_engine: MainEngine, event_engine: EventEngine) -> FastAPI:
    global _loop

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        global _loop
        _loop = asyncio.get_running_loop()
        event_engine.register_general(_event_handler)
        yield
        event_engine.unregister_general(_event_handler)

    app = FastAPI(title="LongBridge Trader", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    html_path = Path(__file__).parent / "index.html"
    vendor_path = Path(__file__).parent / "vendor"
    app.mount("/vendor", StaticFiles(directory=str(vendor_path)), name="vendor")

    @app.get("/")
    async def index():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket):
        await websocket.accept()
        q: asyncio.Queue = asyncio.Queue()
        _ws_queues.append(q)
        try:
            while True:
                msg = await q.get()
                data = msg.copy()
                data["type"] = data["type"].replace("eCta", "eCTA") \
                                             .replace("eTick", "eTICK") \
                                             .replace("eTrade", "eTRADE") \
                                             .replace("eOrder", "eORDER") \
                                             .replace("ePosition", "ePOSITION") \
                                             .replace("eAccount", "eACCOUNT") \
                                             .replace("eLog", "eLOG")
                await websocket.send_json(data)
        except WebSocketDisconnect:
            pass
        finally:
            _ws_queues.remove(q)

    # ---- Position ----

    @app.get("/api/position/list")
    async def position_list():
        return [to_serializable(p) for p in main_engine.get_all_positions() if p.volume != 0]

    # ---- Contract ----

    @app.get("/api/contract/list")
    async def contract_list():
        return [to_serializable(c) for c in main_engine.get_all_contracts()]

    # ---- Kline ----

    _INTERVAL_ALIASES: dict[str, Interval] = {
        "1m": Interval.MINUTE, "1": Interval.MINUTE,
        "1h": Interval.HOUR, "60": Interval.HOUR,
        "d": Interval.DAILY, "daily": Interval.DAILY,
        "w": Interval.WEEKLY, "weekly": Interval.WEEKLY,
    }

    @app.get("/api/kline")
    async def kline(symbol: str, exchange: str, interval: str = "d", limit: int = 300):
        """拉取最近 N 根 K 线（tail 模式，最多 1000 根）。"""
        limit = max(1, min(limit, 1000))
        interval_enum = _INTERVAL_ALIASES.get(interval.lower(), Interval.DAILY)
        req: HistoryRequest = LBHistoryRequest(
            symbol=symbol,
            exchange=_parse_exchange(exchange),
            interval=interval_enum,
            start=datetime.now(),
            end=datetime.now(),
            tail=limit,
        )
        bars = main_engine.query_history(req, "LongBridge")
        return [to_serializable(b) for b in bars]

    # ---- Order ----

    @app.get("/api/order/list")
    async def order_list():
        return [to_serializable(o) for o in main_engine.get_all_orders()]

    @app.post("/api/order/send")
    async def order_send(data: dict):
        req = OrderRequest(
            symbol=data["symbol"],
            exchange=_parse_exchange(data["exchange"]),
            direction=Direction[data["direction"]],
            type=OrderType[data["type"]],
            price=float(data.get("price", 0)),
            volume=float(data["volume"]),
            offset=Offset[data.get("offset", "NONE")],
            reference=data.get("reference", ""),
        )
        vt_orderid = main_engine.send_order(req, "LongBridge")
        return {"vt_orderid": vt_orderid}

    @app.post("/api/order/cancel")
    async def order_cancel(data: dict):
        vt_orderid = data["vt_orderid"]
        order = main_engine.get_order(vt_orderid)
        if order is None:
            return {"error": "order not found"}
        req = order.create_cancel_request()
        main_engine.cancel_order(req, "LongBridge")
        return {"status": "ok"}

    # ---- Trade ----

    @app.get("/api/trade/list")
    async def trade_list():
        return [to_serializable(t) for t in main_engine.get_all_trades()]

    # ---- Account ----

    @app.get("/api/account/list")
    async def account_list():
        return [to_serializable(a) for a in main_engine.get_all_accounts()]

    # ---- Strategy ----

    @app.get("/api/strategy/list")
    async def strategy_list():
        engine = main_engine.get_engine(APP_NAME)
        if engine is None:
            return []
        result = []
        for name, s in engine.strategies.items():
            result.append({
                "strategy_name": name,
                "vt_symbol": s.vt_symbol,
                "class_name": s.__class__.__name__,
                "inited": s.inited,
                "trading": s.trading,
                "pos": s.pos,
                "parameters": s.get_parameters(),
                "variables": s.get_variables(),
            })
        return result

    @app.post("/api/strategy/{name}/init")
    async def strategy_init(name: str):
        engine = main_engine.get_engine(APP_NAME)
        engine.init_strategy(name)
        return {"status": "ok"}

    @app.post("/api/strategy/{name}/start")
    async def strategy_start(name: str):
        engine = main_engine.get_engine(APP_NAME)
        engine.start_strategy(name)
        return {"status": "ok"}

    @app.post("/api/strategy/{name}/stop")
    async def strategy_stop(name: str):
        engine = main_engine.get_engine(APP_NAME)
        engine.stop_strategy(name)
        return {"status": "ok"}

    # ---- Subscribe ----

    @app.post("/api/subscribe")
    async def subscribe(data: dict):
        symbol = data["symbol"]
        exchange = _parse_exchange(data["exchange"])
        req = SubscribeRequest(symbol=symbol, exchange=exchange)
        main_engine.subscribe(req, "LongBridge")
        return {"status": "ok"}

    return app
