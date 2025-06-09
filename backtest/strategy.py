import backtrader as bt
from loguru import logger
from indicators import TrendTemplate, MansfieldRS, VCP, Breakout


class MinerviniVCPStrategy(bt.Strategy):
    params = dict(
        stop_loss=0.02,
        take_profit=0.1,
        mansfield_threshold=5
    )

    def __init__(self):
        self.order = [None] * len(self.datas)
        self.buy_price = [None] * len(self.datas)
        self.signal_flag = [False] * len(self.datas)
        
        # 인디케이터 초기화
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
        
        # 현재 포지션 없을 때 진입 조건 체크
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

            else:
                # 포지션 있을 때 매도 조건 (손절 / 익절)
                current_price = d.close[0]
                if current_price <= self.buy_price[i] * (1 - self.p.stop_loss):
                    self.log(f"STOP LOSS SELL at {d.datetime.date(0)}, Price={current_price:.2f}", data=d)
                    self.order[i] = self.sell(data=d)
                elif current_price >= self.buy_price[i] * (1 + self.p.take_profit):
                    self.log(f"TAKE PROFIT SELL at {d.datetime.date(0)}, Price={current_price:.2f}", data=d)
                    self.order[i] = self.sell(data=d)