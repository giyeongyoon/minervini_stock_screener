import FinanceDataReader as fdr
from datetime import datetime
from pandas.tseries.offsets import BDay
from ta.volatility import BollingerBands
from scipy.signal import find_peaks
from scipy.stats import linregress
import numpy as np
from loguru import logger


def detect_vcp(df,
           bb_window=20, bb_std=2, bb_threshold=10,
           vol_ma_window=50,
           contraction_segments=3, segment_length=10,
           max_contraction_ratio=1.1):
    prices = df['Close'].values

    peaks, _ = find_peaks(prices, distance=7)
    troughs, _ = find_peaks(-prices, distance=7)

    swing_points = sorted(list(peaks) + list(troughs))
    swing_points.sort()

    contractions = []
    contraction_check = False
    for i in range(2, len(swing_points)):
        start = swing_points[i-2]
        end = swing_points[i]
        high = df['High'][start:end].max()
        low = df['Low'][start:end].min()
        width = end - start
        height = (high - low)/high
        contractions.append((width, height))
    
    contraction_count = sum([contractions[i][1] > contractions[i+1][1] for i in range(len(contractions) - 1)])
    last_contraction = contractions[-1][1]
    if contraction_count >= 3 and last_contraction <= 0.1:
        contraction_check = True
        
    indicator_bb = BollingerBands(close=df['Close'])
    df['bb_width'] = indicator_bb.bollinger_wband()
    y = df['bb_width'].iloc[-30:].values
    x = np.arange(len(y))
    slope, _, _, _, _ = linregress(x, y)
    bb_squeeze = (slope < 0)
    
    df['vol_ma50'] = df['Volume'].rolling(vol_ma_window).mean()
    df['low_volume'] = df['Volume'] < df['vol_ma50']
    low_vol = df['low_volume'].iloc[-1]

    df['vcp_ready'] = low_vol & contraction_check
    
    return df, bb_squeeze, low_vol, contraction_check
    

def add_vcp(df):
    logger.info("Detect VCP(Volatility Contraction Pattern)")
    end = datetime.today()
    start = end - BDay(100)
    
    codes = df['종목코드'].tolist()
    bb_dict = {}
    low_vol_dict = {}
    is_contracting_dict = {}
    vcp_ready_dict = {}
    for code in codes:
        stock_df = fdr.DataReader(code, start, end)
        stock_df_vcp, bb, low_vol, is_contracting = detect_vcp(stock_df)
        bb_dict[code] = bb
        low_vol_dict[code] = low_vol
        is_contracting_dict[code] = is_contracting
        vcp_ready_dict[code] = stock_df_vcp['vcp_ready'].iloc[-1]
    
    df['bb'] = df['종목코드'].map(bb_dict)
    df['low_volume'] = df['종목코드'].map(low_vol_dict)
    df['is_contracting'] = df['종목코드'].map(is_contracting_dict)
    df['vcp_ready'] = df['종목코드'].map(vcp_ready_dict)
    return df    
