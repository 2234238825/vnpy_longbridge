
from time import sleep
from vnpy_longbridge.longbridge_gateway import build_config_from_setting
from longbridge.openapi import QuoteContext, Config, SubType, PushQuote, OAuthBuilder
import numpy as np

def on_quote(symbol: str, event: PushQuote):
    print(symbol, event)

from vnpy_longbridge.lb_strategy_app import BarData
class ArrayManager:
    """
    For:
    1. time series container of bar data
    2. calculating technical indicator value
    """

    def __init__(self, size: int = 5) -> None:
        """Constructor"""
        self.count: int = 0
        self.size: int = size
        self.inited: bool = False

        self.open_array: np.ndarray = np.zeros(size)
        self.high_array: np.ndarray = np.zeros(size)
        self.low_array: np.ndarray = np.zeros(size)
        self.close_array: np.ndarray = np.zeros(size)
        self.volume_array: np.ndarray = np.zeros(size)
        self.turnover_array: np.ndarray = np.zeros(size)
        self.open_interest_array: np.ndarray = np.zeros(size)

    def update_bar(self, bar: int) -> None:
        """
        Update new bar data into array manager.
        """
        self.count += 1
        if not self.inited and self.count >= self.size:
            self.inited = True

        self.open_array[:-1] = self.open_array[1:]
        self.high_array[:-1] = self.high_array[1:]
        self.low_array[:-1] = self.low_array[1:]
        self.close_array[:-1] = self.close_array[1:]
        self.volume_array[:-1] = self.volume_array[1:]
        self.turnover_array[:-1] = self.turnover_array[1:]
        self.open_interest_array[:-1] = self.open_interest_array[1:]

        self.open_array[-1] = bar
        self.high_array[-1] = bar
        self.low_array[-1] = bar
        self.close_array[-1] = bar
        self.volume_array[-1] = bar
        self.turnover_array[-1] = bar
        self.open_interest_array[-1] = bar

if __name__ == "__main__":
    # config = build_config_from_setting()
    # ctx = QuoteContext(config)
    # ctx.set_on_quote(on_quote)
    #
    # ctx.subscribe(["700.HK", "AAPL.US"], [SubType.Quote])
    # sleep(30)
    am = ArrayManager(size=5)
    for i in range(10):
        am.update_bar(i)
        print(f"Update {i+1} times, inited: {am.inited}, count: {am.count}")
