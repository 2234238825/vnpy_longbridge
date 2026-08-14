"""数据源注册表：按名称取数据源实例。新增数据源在此加一个分支。"""
from .base import DataSource


def get_source(name: str) -> DataSource:
    """按名称获取数据源实例。"""
    if name == "longbridge":
        from .longbridge import LongBridgeSource
        return LongBridgeSource()
    raise ValueError(f"未知数据源：{name}，可用：longbridge")
