import backtrader as bt
import numpy as np
from scipy.stats import linregress
from scipy.signal import find_peaks


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
        self.lines.check_trend[0] = int(all([cond1, cond2, cond3, cond4, cond5, cond6, cond7]))


class MansfieldRS(bt.Indicator):
    lines = ('mansfield_rs',)
    params = (('ma_length', 52),)
    
    def __init__(self):
        self.ratio = self.data.close / self.data.market_close * 100
        self.zero_line = bt.indicators.SMA(self.ratio, period=self.p.ma_length)
        self.addminperiod(self.p.ma_length)
        
    def next(self):
        self.lines.mansfield_rs[0] = (self.ratio[0] / self.zero_line[0] - 1) * 100
     

class VCP(bt.Indicator):
    lines = ('check_vcp',)
    params = (('contraction_threshold', 0.1),)
    
    def __init__(self):
        self.addminperiod(100)
        
    def next(self):
        closes = np.array(self.data.close.get(size=100))
        highs = np.array(self.data.high.get(size=100))
        lows = np.array(self.data.low.get(size=100))
        volumes = np.array(self.data.volume.get(size=100))
        
        if len(closes) < 100:
            self.lines.check_vcp[0] = 0
            return
        
        peaks, _ = find_peaks(closes, distance=7)
        troughs, _ = find_peaks(-closes, distance=7)
        swing_points = sorted(list(peaks) + list(troughs))
        
        if len(swing_points) < 3:
            self.lines.check_vcp[0] = 0
            return
        
        contractions = []
        for i in range(2, len(swing_points)):
            start = swing_points[i-2]
            end = swing_points[i]
            high = highs[start:end].max()
            low = lows[start:end].min()
            height = (high - low)/high
            contractions.append(height)
            
        contraction_count = sum([contractions[i] > contractions[i+1] for i in range(len(contractions) - 1)])
        last_contraction = contractions[-1] if contractions else 1.0
        
        contraction_check = contraction_count >= 3 and last_contraction < self.p.contraction_threshold
        volume_check = volumes[-1] < np.mean(volumes[-50:])
        
        self.lines.check_vcp[0] = int(contraction_check and volume_check)
        
        
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