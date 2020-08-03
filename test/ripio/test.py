#!/usr/bin/env python
import matha
import time
from os.path import join, realpath
import sys; sys.path.insert(0, realpath(join(__file__, "../../../")))
from hummingbot.core.event.event_logger import EventLogger
from hummingbot.core.event.events import OrderBookEvent, OrderBookTradeEvent, TradeType

from hummingbot.market.ripio.ripio_order_book_tracker import RipioOrderBookTracker
import asyncio
import logging
from typing import (
    Dict,
    Optional,
    List,
)
import unittest

from hummingbot.core.data_type.order_book import OrderBook
from hummingbot.core.data_type.order_book_tracker import (
    OrderBookTrackerDataSourceType
)
from hummingbot.core.utils.async_utils import (
    safe_ensure_future,
    safe_gather,
)


class RipioOrderBookTrackerTest(unittest.TestCase):
    order_book_tracker: Optional[RipioOrderBookTracker] = None
    events: List[OrderBookEvent] = [
        OrderBookEvent.TradeEvent
    ]
    trading_pairs: List[str] = [
        "BTC_USDC",
        "ETH_USDC"
    ]
    @classmethod
    def setUpClass(cls):
        cls.ev_loop: asyncio.BaseEventLoop = asyncio.get_event_loop()
        cls.order_book_tracker: RipioOrderBookTracker = RipioOrderBookTracker(
            data_source_type=OrderBookTrackerDataSourceType.EXCHANGE_API,
            trading_pairs=cls.trading_pairs)
        cls.order_book_tracker_task: asyncio.Task = safe_ensure_future(cls.order_book_tracker.start())
        cls.ev_loop.run_until_complete(cls.wait_til_tracker_ready())

    @classmethod
    async def wait_til_tracker_ready(cls):
        while True:
            if len(cls.order_book_tracker.order_books) > 0:
                print("Initialized real-time order books.")
                return
            await asyncio.sleep(1)

    async def run_parallel_async(self, *tasks):
        future: asyncio.Future = safe_ensure_future(safe_gather(*tasks))
        while not future.done():
            await asyncio.sleep(1.0)
        return future.result()

    def run_parallel(self, *tasks):
        return self.ev_loop.run_until_complete(self.run_parallel_async(*tasks))

    def setUp(self):
        self.event_logger = EventLogger()
        for event_tag in self.events:
            for trading_pair, order_book in self.order_book_tracker.order_books.items():
                order_book.add_listener(event_tag, self.event_logger)

    def test_order_book_trade_event_emission(self):
        """
        Test if order book tracker is able to retrieve order book trade message from exchange and
        emit order book trade events after correctly parsing the trade messages
        """
        self.run_parallel(self.event_logger.wait_for(OrderBookTradeEvent))
        for ob_trade_event in self.event_logger.event_log:
            self.assertTrue(type(ob_trade_event) == OrderBookTradeEvent)
            self.assertTrue(ob_trade_event.trading_pair in self.trading_pairs)
            self.assertTrue(type(ob_trade_event.timestamp) == float)
            self.assertTrue(type(ob_trade_event.amount) == float)
            self.assertTrue(type(ob_trade_event.price) == float)
            self.assertTrue(type(ob_trade_event.type) == TradeType)
            self.assertTrue(math.ceil(math.log10(ob_trade_event.timestamp)) == 10)
            self.assertTrue(ob_trade_event.amount > 0)
            self.assertTrue(ob_trade_event.price > 0)

    def test_tracker_integrity(self):
        # Wait 5 seconds to process some diffs.
        self.ev_loop.run_until_complete(asyncio.sleep(10.0))
        order_books: Dict[str, OrderBook] = self.order_book_tracker.order_books
        btcusdc_book: OrderBook = order_books["BTC_USDC"]
        ethusdc_book: OrderBook = order_books["ETH_USDC"]
        print("btcusdc")
        print(btcusdc_book.snapshot)
        print("ethusdc")
        print(ethusdc_book.snapshot)
        self.assertGreaterEqual(btcusdc_book.get_price_for_volume(True, 10).result_price,
                                btcusdc_book.get_price(True))
        self.assertLessEqual(btcusdt_book.get_price_for_volume(False, 10).result_price,
                             btcusdt_book.get_price(False))
        self.assertGreaterEqual(ethusdc_book.get_price_for_volume(True, 10000).result_price,
                                ethusdc_book.get_price(True))
        self.assertLessEqual(ethusdc_book.get_price_for_volume(False, 10000).result_price,
                             ethusdc_book.get_price(False))


def main():
    logging.basicConfig(level=logging.INFO)
    unittest.main()


if __name__ == "__main__":
    main()
