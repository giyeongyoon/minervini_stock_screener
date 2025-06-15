import backtrader as bt
import numpy as np
from scipy.stats import linregress
from scipy.signal import find_peaks
import datetime
from typing import Optional
import pytz


class TrendTemplate(bt.Indicator):
    lines = ('check_trend',)
    
    def __init__(self):
        sma200 = bt.ind.SMA(self.data.close, period=200)
        sma150 = bt.ind.SMA(self.data.close, period=150)
        sma50 = bt.ind.SMA(self.data.close, period=50)
        
        self.addminperiod(200)
        
        self.sma200 = sma200
        self.sma150 = sma150
        self.sma50 = sma50
        
    def next(self):
        
        close = self.data.close[0]
        sma200 = self.sma200[0]
        sma150 = self.sma150[0]
        sma50 = self.sma50[0]
        
        cond1 = close > sma150 and close > sma200
        cond2 = sma150 > sma200
        cond3 = sma50 > sma150 and sma50 > sma200
        cond4 = close > sma50
        
        max_close = max(self.data.close.get(size=200))
        min_close = min(self.data.close.get(size=200))
        
        cond5 = close >= max_close * 0.75
        cond6 = close >= min_close * 1.3
        
        sma200_array = self.sma200.get(size=20)
        if len(sma200_array) < 20:
            cond7 = False
        else:
            x = np.arange(len(sma200_array))
            slope, _, _, _, _ = linregress(x, sma200_array)
            cond7 = slope > 0
        self.lines.check_trend[0] = int(all([cond2, cond3, cond4, cond7]))


class MansfieldRS(bt.Indicator):
    lines = ('mansfield_rs',)
    params = (('ma_length', 52),)
    
    def __init__(self):
        self.ratio = self.data.close / self.data.market_close * 100
        self.zero_line = bt.indicators.SMA(self.ratio, period=self.p.ma_length)
        self.addminperiod(self.p.ma_length)
        
    def next(self):
        self.lines.mansfield_rs[0] = (self.ratio[0] / self.zero_line[0] - 1) * 100
     

# class VCP(bt.Indicator):
#     lines = ('check_vcp',)
#     params = (('contraction_threshold', 0.1),)
    
#     def __init__(self):
#         self.addminperiod(100)
        
#     def next(self):
#         closes = np.array(self.data.close.get(size=100))
#         highs = np.array(self.data.high.get(size=100))
#         lows = np.array(self.data.low.get(size=100))
#         volumes = np.array(self.data.volume.get(size=100))
        
#         if len(closes) < 100:
#             self.lines.check_vcp[0] = 0
#             return
        
#         peaks, _ = find_peaks(closes, distance=7)
#         troughs, _ = find_peaks(-closes, distance=7)
#         swing_points = sorted(list(peaks) + list(troughs))
        
#         if len(swing_points) < 3:
#             self.lines.check_vcp[0] = 0
#             return
        
#         contractions = []
#         for i in range(2, len(swing_points)):
#             start = swing_points[i-2]
#             end = swing_points[i]
#             high = highs[start:end].max()
#             low = lows[start:end].min()
#             height = (high - low)/high
#             contractions.append(height)
            
#         contraction_count = sum([contractions[i] > contractions[i+1] for i in range(len(contractions) - 1)])
#         last_contraction = contractions[-1] if contractions else 1.0
        
#         contraction_check = contraction_count >= 3 and last_contraction < self.p.contraction_threshold
#         volume_check = volumes[-1] < np.mean(volumes[-50:])
        
#         self.lines.check_vcp[0] = int(contraction_check and volume_check)

class VCP(bt.Indicator):
    lines = ('vcp_signal',)
    params = dict(
        vol_lookback_short=5,
        vol_lookback_long=20,
        volume_lookback_short=5,
        volume_lookback_long=20,
        breakout_lookback=20,
        vol_shrink_thresh=0.8,
        volume_shrink_thresh=0.7,
    )

    def __init__(self):
        # alias
        close = self.data.close
        volume = self.data.volume
        
        # 표준편차 기반 변동성 수축
        self.vol_now = bt.ind.StdDev(close, period=self.p.vol_lookback_short)
        self.vol_prev = bt.ind.StdDev(close(-self.p.vol_lookback_short), period=self.p.vol_lookback_long - self.p.vol_lookback_short)
        
        # 거래량 감소
        self.vol_avg_now = bt.indicators.SimpleMovingAverage(volume, period=self.p.volume_lookback_short)
        self.vol_avg_prev = bt.indicators.SimpleMovingAverage(volume(-self.p.volume_lookback_short), period=self.p.volume_lookback_long - self.p.volume_lookback_short)
        
        # 최근 고점
        self.highest = bt.ind.Highest(close(-1), period=self.p.breakout_lookback)

    def next(self):
        vol_shrunk = self.vol_now[0] < self.vol_prev[0] * self.p.vol_shrink_thresh
        volume_shrunk = self.vol_avg_now[0] < self.vol_avg_prev[0] * self.p.volume_shrink_thresh
        breakout = self.data.close[0] > self.highest[0]

        self.lines.vcp_signal[0] = int(vol_shrunk and volume_shrunk and breakout)
        
        
class Breakout(bt.Indicator):
    lines = ('breakout_signal',)
    params = (('volume_multiplier', 1.5),)
    
    def __init__(self):
        self.addminperiod(22)
        
    def next(self):
        if len(self.data) < 22:
            self.lines.breakout_signal[0] = 0
            return

        # 최근 20일(종료 하루 전)의 최고 종가
        recent_high = max(self.data.close.get(size=21)[:-1])
        current_close = self.data.close[0]

        # 최근 5일 평균 거래량 (현재 제외)
        recent_vols = self.data.volume.get(size=6)[:-1]
        avg_vol = np.mean(recent_vols)
        current_vol = self.data.volume[0]

        breakout = current_close > recent_high
        volume_surge = current_vol > avg_vol * self.p.volume_multiplier

        self.lines.breakout_signal[0] = int(breakout and volume_surge)
        # self.lines.breakout_signal[0] = int(breakout)
        
        
class VwapIntradayIndicator(bt.Indicator):
    """
    Volume Weighted Average Price (VWAP) indicator for intraday trading.
    """

    lines = ("vwap_intraday",)
    params = {"timezone": "America/New_York"}
    plotinfo = {"subplot": False}
    plotlines = {"vwap_intraday": {"color": "blue"}}

    def __init__(self) -> None:
        self.hlc = (self.data.high + self.data.low + self.data.close) / 3.0

        self.current_date: Optional[datetime.date] = None
        self.previous_date_index: int = -1

    def next(self) -> None:
        current_date = (
            pytz.utc.localize(self.data.datetime.datetime()).astimezone(pytz.timezone(self.p.timezone)).date()
        )
        len_self: int = len(self)

        if self.current_date != current_date:
            self.current_date = current_date
            self.previous_date_index = len_self - 1

        volumes = self.data.volume.get(size=len_self - self.previous_date_index)
        hlc = self.hlc.get(size=len_self - self.previous_date_index)

        numerator = sum(hlc[i] * volumes[i] for i in range(len(volumes)))
        
        vwap_value = numerator / sum(volumes) if sum(volumes) else self.lines.vwap_intraday[-1]
        self.lines.vwap_intraday[0] = vwap_value

class VwapIntradayIndicator2(bt.Indicator):
    lines = ('vwap_intraday',)
    plotinfo = dict(subplot=False)

    def __init__(self):
        self.addminperiod(1)
        self.hlc = (self.data.high + self.data.low + self.data.close) / 3.0
        self.volume_sum = 0.0
        self.vwap_sum = 0.0
        self.current_date = None

    def next(self):
        dt = self.data.datetime.datetime(0).date()
        if self.current_date != dt:
            self.current_date = dt
            self.volume_sum = 0.0
            self.vwap_sum = 0.0
        v = self.data.volume[0]
        hlc = self.hlc[0]
        self.vwap_sum += hlc * v
        self.volume_sum += v
        self.lines.vwap_intraday[0] = self.vwap_sum / self.volume_sum if self.volume_sum else self.data.close[0]
        
        
class BollingerBands(bt.Indicator):
    lines = ("top", "bot", "mid", "width", "percent_b")
    params = dict(period=20, dev=2)

    def __init__(self):
        self.addminperiod(self.p.period)
        self.lines.mid = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.period)
        self.lines.top = self.lines.mid + self.p.dev * bt.indicators.StandardDeviation(self.data.close, period=self.p.period)
        self.lines.bot = self.lines.mid - self.p.dev * bt.indicators.StandardDeviation(self.data.close, period=self.p.period)
        self.lines.width = self.lines.top - self.lines.bot
        self.lines.percent_b = (self.data.close - self.lines.bot) / (self.lines.top - self.lines.bot)