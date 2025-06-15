import backtrader as bt
from loguru import logger
from indicators import (
    TrendTemplate,
    MansfieldRS,
    VCP, 
    Breakout, 
    VwapIntradayIndicator,
    VwapIntradayIndicator2,
    BollingerBands
)
import datetime
import pytz
import numpy as np


class MinerviniVCPStrategy(bt.Strategy):
    params = dict(
        stop_loss=0.05,
        # take_profit=0.1,
        trailing_stop_pct=0.1,
        mansfield_threshold=8
    )

    def __init__(self):
        self.order = [None] * len(self.datas)
        self.buy_price = [None] * len(self.datas)
        self.signal_flag = [False] * len(self.datas)
        self.highest_price = [0.0] * len(self.datas)
        
        self.trend = [TrendTemplate(d) for d in self.datas]
        self.mansfield_rs = [MansfieldRS(d) for d in self.datas]
        self.vcp = [VCP(d) for d in self.datas]
        self.breakout = [Breakout(d) for d in self.datas]

    def log(self, txt, data=None):
        if data:
            name = data._name
        else:
            name = self.datas[0]._name
        logger.info(f"{name}: {txt}")

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, %.2f' % order.executed.price, data=order.data)
            elif order.issell():
                self.log('SELL EXECUTED, %.2f' % order.executed.price, data=order.data)

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected', data=order.data)

        # Write down: no pending order
        for i, d in enumerate(self.datas):
            if order.data == d:
                self.order[i] = None
                
    def next(self):
        for i, d in enumerate(self.datas):
            if self.order[i]:
                continue
            if not self.getposition(d).size: 
                if (
                    self.trend[i][0] and
                    self.mansfield_rs[i][0] >= self.p.mansfield_threshold and
                    self.vcp[i][0] and
                    self.breakout[i][0]
                ):
                    self.signal_flag[i] = True
                    self.log(f"BUY SIGNAL at {d.datetime.date(0)}, Close={d.close[0]:.2f}", data=d)
                    self.order[i] = self.buy(data=d)
                    self.buy_price[i] = d.close[0]
                    self.highest_price[i] = d.close[0]

            else:                
                current_price = d.close[0]
                
                min_trailing_stop = 0.05
                profit = (current_price - self.buy_price[i]) / self.buy_price[i]
                if profit >= min_trailing_stop:
                    self.highest_price[i] = max(self.highest_price[i], current_price)
                    trailing_stop_price = self.highest_price[i] * (1 - self.p.trailing_stop_pct)
                    if current_price <= trailing_stop_price:
                        self.log(f"TRAILING STOP SELL at {d.datetime.date(0)}, Price={current_price:.2f}", data=d)
                        self.order[i] = self.sell(data=d)

                stop_price = self.buy_price[i] * (1 - self.p.stop_loss)

                if current_price <= stop_price:
                    self.log(f"STOP LOSS SELL at {d.datetime.date(0)}, Price={current_price:.2f}", data=d)
                    self.order[i] = self.sell(data=d)
                
                # elif current_price >= take_profit_price:
                #     self.log(f"TAKE PROFIT SELL at {d.datetime.date(0)}, Price={current_price:.2f}", data=d)
                #     self.order[i] = self.sell(data=d)
                
                
class VWAPIntradayStrategy(bt.Strategy):
    params = dict(
        threshold=0.005,         # 0.5% 이격 기준
        stop_loss_pct=0.05,      # 5% 고정 손절 (완화)
        trailing_stop_pct=0.02,  # 2% 트레일링 스탑
        size=100,
        timezone="America/New_York"
    )

    def __init__(self):
        self.vwap = VwapIntradayIndicator(self.data, timezone=self.p.timezone, plot=True)
        self.order = None
        self.buy_price = None
        self.highest_price = None
        self.lowest_price = None
        self.entered_today = False

    def log(self, txt):
        dt = self.datas[0].datetime.datetime(0)
        logger.info(f"{dt.isoformat()} - {txt}")

    def next(self):
        dt = self.datas[0].datetime.datetime(0)
        local_time = pytz.utc.localize(dt).astimezone(pytz.timezone(self.p.timezone)).time()

        # 장 시간 필터 (9:45 ~ 15:30만 거래 허용)
        if local_time < datetime.time(9, 45) or local_time > datetime.time(15, 30):
            return

        # 하루 1회 진입 제한
        if dt.date() != getattr(self, "current_date", None):
            self.current_date = dt.date()
            self.entered_today = False

        if self.order:
            return

        price = self.data.close[0]
        vwap = self.vwap[0]
        if not vwap:
            return

        diff_pct = (price - vwap) / vwap
        pos = self.getposition()

        # 진입 조건
        if not pos and not self.entered_today:
            if diff_pct < -self.p.threshold and self.data.close[0] > self.data.close[-1]:
                self.order = self.buy(size=self.p.size)
                self.buy_price = price
                self.highest_price = price
                self.entered_today = True
                self.log(f"BUY @ {price:.2f} | VWAP={vwap:.2f} | Diff={diff_pct:.2%}")

            elif diff_pct > self.p.threshold and self.data.close[0] < self.data.close[-1]:
                self.order = self.sell(size=self.p.size)
                self.buy_price = price
                self.lowest_price = price
                self.entered_today = True
                self.log(f"SELL @ {price:.2f} | VWAP={vwap:.2f} | Diff={diff_pct:.2%}")

        # 포지션 관리
        elif pos:
            if pos.size > 0:
                self.highest_price = max(self.highest_price, price)
                trailing_stop_price = self.highest_price * (1 - self.p.trailing_stop_pct)
                stop_price = self.buy_price * (1 - self.p.stop_loss_pct)

                if price <= trailing_stop_price:
                    self.log(f"TRAILING STOP (LONG) @ {price:.2f}")
                    self.order = self.close()
                elif price <= stop_price:
                    self.log(f"STOP LOSS (LONG) @ {price:.2f}")
                    self.order = self.close()

            elif pos.size < 0:
                self.lowest_price = min(self.lowest_price, price)
                trailing_stop_price = self.lowest_price * (1 + self.p.trailing_stop_pct)
                stop_price = self.buy_price * (1 + self.p.stop_loss_pct)

                if price >= trailing_stop_price:
                    self.log(f"TRAILING STOP (SHORT) @ {price:.2f}")
                    self.order = self.close()
                elif price >= stop_price:
                    self.log(f"STOP LOSS (SHORT) @ {price:.2f}")
                    self.order = self.close()

    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Rejected]:
            self.order = None


class VWAPIntradayStrategy2(bt.Strategy):
    params = dict(
        reversion_threshold=0.02,
        stop_loss_pct=0.03,
        take_profit_pct=0.08,
        trailing_stop_pct=0.03,
        close_hour=15,   # 15:30 이전에 정리
        close_minute=30,
        long_pct=1.0,
    )

    def __init__(self):
        self.vwap = [VwapIntradayIndicator2(d) for d in self.datas]
        self.order = [None] * len(self.datas)
        self.buy_price = [None] * len(self.datas)
        self.highest_price = [None] * len(self.datas)
        self.signal_flag = [False] * len(self.datas)
        
    def log(self, txt, data=None):
        if data:
            name = data._name
        else:
            name = self.datas[0]._name
        logger.info(f"{name}: {txt}")

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                dt = bt.num2date(order.executed.dt)
                self.log(f"BUY EXECUTED at {dt.strftime('%Y-%m-%d %H:%M:%S')}, PRICE: {order.executed.price:.2f}, SIZE: {order.executed.size}", data=order.data)
            elif order.issell():
                dt = bt.num2date(order.executed.dt)
                self.log(f"SELL EXECUTED at {dt.strftime('%Y-%m-%d %H:%M:%S')}, PRICE: {order.executed.price:.2f}, SIZE: {order.executed.size}", data=order.data)
            
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected', data=order.data)

        # Write down: no pending order
        for i, d in enumerate(self.datas):
            if order.data == d:
                self.order[i] = None
                
    def next(self):
        for i, d in enumerate(self.datas):
            dt = d.datetime.datetime(0)
            time_now = dt.time()
            pos = self.getposition(d)
            
            if time_now.hour == 15 and time_now.minute == 30:
                if pos.size > 0:
                    self.log("Day End: Closing position", data=d)
                    self.close(data=d)
                    self.order[i] = None
                continue
            
            if time_now < datetime.time(9, 0) or time_now > datetime.time(15, 30):
                continue
            
            if self.order[i]:
                continue
            
            if pos.size == 0:
                # self.log(f"{self.vwap[i][0]}", data=d)
                
                # vwap 상방돌파 매수
                if d.close[0] > self.vwap[i][0] and d.close[-1] <= self.vwap[i][-1]:
                    self.log(f"vwap 상방돌파 시그널 at {d.datetime.datetime(0)}, Price={d.close[0]:.2f}", data=d)
                    cash = self.broker.getcash()
                    size = int((cash * self.p.long_pct) / d.close[0])
                    if size > 0:
                        self.order[i] = self.buy(data=d, size=size)
                        self.buy_price[i] = d.close[0]
                        self.highest_price[i] = d.close[0]
                        self.signal_flag[i] = True
                        
                # vwap 리버전 매수
                # elif d.close[0] < self.vwap[i][0] * (1 - self.p.reversion_threshold):
                #     self.log(f"vwap 리버전 시그널 at {d.datetime.datetime(0)}, Price={d.close[0]:.2f}", data=d)
                #     cash = self.broker.getcash()
                #     size = int((cash * 0.5) / d.close[0])
                #     if size > 0:
                #         self.order[i] = self.buy(data=d, size=size)
                #         self.buy_price[i] = d.close[0]
                #         self.highest_price[i] = d.close[0]
                #         self.signal_flag[i] = True
            else:
                if pos.size > 0:
                    current_price = d.close[0]
                    self.highest_price[i] = max(self.highest_price[i], current_price)
                    stop_price = self.buy_price[i] * (1 - self.p.stop_loss_pct)
                    # take_profit = self.buy_price[i] * (1 + self.p.take_profit_pct)
                    trailing_stop = self.highest_price[i] * (1 - self.p.trailing_stop_pct)
                    
                    pos = self.getposition(d)
                    if current_price <= stop_price:
                        self.log(f"STOP LOSS SELL at {d.datetime.datetime(0)}, Price={current_price:.2f}", data=d)
                        self.order[i] = self.sell(data=d, size=pos.size)
                        
                    elif current_price <= trailing_stop:
                        self.log(f"TRAILING STOP SELL at {d.datetime.datetime(0)}, Price={current_price:.2f}", data=d)
                        self.order[i] = self.sell(data=d, size=pos.size)
                
            
            
class VWAPIntradayWithFilters(bt.Strategy):
    params = dict(
        threshold=0.002,         # 0.2% VWAP 이격
        stop_loss_pct=0.05,      # 손절 5%
        trailing_stop_pct=0.02,  # 트레일링 스탑 2%
        size=100,
        volume_multiplier=1.3,   # 거래량 스파이크 1.3배
        bollinger_period=20,
        bollinger_dev=2,
        timezone="America/New_York"
    )

    def __init__(self):
        self.vwap = VwapIntradayIndicator(self.data, timezone=self.p.timezone)
        self.bollinger = BollingerBands(self.data, period=self.p.bollinger_period, dev=self.p.bollinger_dev)
        self.order = None
        self.buy_price = None
        self.highest_price = None
        self.lowest_price = None

    def log(self, txt):
        dt = self.datas[0].datetime.datetime(0)
        logger.info(f"{dt.isoformat()} - {txt}")

    def next(self):
        dt = self.datas[0].datetime.datetime(0)
        local_time = pytz.utc.localize(dt).astimezone(pytz.timezone(self.p.timezone)).time()

        # 장 중 시간 필터 (확대)
        if local_time < datetime.time(9, 30) or local_time > datetime.time(15, 45):
            return

        if self.order:
            return

        price = self.data.close[0]
        vwap = self.vwap[0]
        volume = self.data.volume[0]
        avg_volume = np.mean(self.data.volume.get(size=20))
        volume_spike = volume > avg_volume * self.p.volume_multiplier

        bb_width = self.bollinger.width[0]
        avg_bb_width = np.mean(self.bollinger.width.get(size=20))
        bb_squeeze = bb_width < avg_bb_width  # 평균보다 좁을 때만

        diff_pct = (price - vwap) / vwap
        pos = self.getposition()

        # 진입 조건
        if not pos and volume_spike and bb_squeeze:
            if diff_pct < -self.p.threshold and self.data.close[0] > self.data.close[-1]:
                self.order = self.buy(size=self.p.size)
                self.buy_price = price
                self.highest_price = price
                self.log(f"BUY @ {price:.2f} | VWAP={vwap:.2f}")

            elif diff_pct > self.p.threshold and self.data.close[0] < self.data.close[-1]:
                self.order = self.sell(size=self.p.size)
                self.buy_price = price
                self.lowest_price = price
                self.log(f"SELL @ {price:.2f} | VWAP={vwap:.2f}")

        # 포지션 관리
        elif pos:
            if pos.size > 0:
                self.highest_price = max(self.highest_price, price)
                trailing_stop = self.highest_price * (1 - self.p.trailing_stop_pct)
                stop_price = self.buy_price * (1 - self.p.stop_loss_pct)

                if price <= trailing_stop:
                    self.log(f"TRAILING STOP (LONG) @ {price:.2f}")
                    self.order = self.close()
                elif price <= stop_price:
                    self.log(f"STOP LOSS (LONG) @ {price:.2f}")
                    self.order = self.close()

            elif pos.size < 0:
                self.lowest_price = min(self.lowest_price, price)
                trailing_stop = self.lowest_price * (1 + self.p.trailing_stop_pct)
                stop_price = self.buy_price * (1 + self.p.stop_loss_pct)

                if price >= trailing_stop:
                    self.log(f"TRAILING STOP (SHORT) @ {price:.2f}")
                    self.order = self.close()
                elif price >= stop_price:
                    self.log(f"STOP LOSS (SHORT) @ {price:.2f}")
                    self.order = self.close()

    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Rejected]:
            self.order = None

