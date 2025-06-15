import yfinance as yf
import backtrader as bt
from custom_data import CustomPandasData
import pandas as pd
import pandas_ta as ta
import os
import glob

TIMEFRAME_MAP = {
    "1m": (bt.TimeFrame.Minutes, 1),
    "2m": (bt.TimeFrame.Minutes, 2),
    "5m": (bt.TimeFrame.Minutes, 5),
    "15m": (bt.TimeFrame.Minutes, 15),
    "30m": (bt.TimeFrame.Minutes, 30),
    "60m": (bt.TimeFrame.Minutes, 60),
    "90m": (bt.TimeFrame.Minutes, 90),
    "1h": (bt.TimeFrame.Minutes, 60),
    "1d": (bt.TimeFrame.Days, 1),
    "5d": (bt.TimeFrame.Days, 5),
    "1wk": (bt.TimeFrame.Weeks, 1),
    "1mo": (bt.TimeFrame.Months, 1),
    "3mo": (bt.TimeFrame.Months, 3),
}


def get_ohlc_pandas_data(market: str, timeframe: str, period: str) -> bt.feeds.PandasData:
    """
    Fetch OHLC data from Yahoo Finance and convert it to a Backtrader data feed.

    Parameters:
    - market (str): Trading symbol (e.g., "^GSPC" for S&P 500)
    - timeframe (str): Data timeframe (e.g., "1d", "1h", "15m")
        Valid intervals: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo

    Returns:
    - bt.feeds.PandasData: Backtrader data feed
    """
    data_source = yf.Ticker(market)
    df = data_source.history(interval=timeframe, period=period)
    # df.index = df.index.tz_convert("UTC")
    bt_timeframe, compression = TIMEFRAME_MAP.get(timeframe, (bt.TimeFrame.Minutes, 1))
    # ignore pylint E1123:
    data = bt.feeds.PandasData(dataname=df, timeframe=bt_timeframe, compression=compression)  # pylint: disable=E1123

    return data

def get_ohlc_minervini_data(data_dir='data', market_code='KS11'):
    # 시장지수 데이터 준비 (종가 시리즈)
    market_df = pd.read_parquet(f'{data_dir}/{market_code}.parquet')
    market_series = market_df['Close'].resample('D').last().fillna(method='ffill')

    # 여러 종목 파일 불러오기
    files = glob.glob(f'{data_dir}/*.parquet')
    for file in files:
        code = os.path.basename(file).replace('.parquet', '')
        if code == market_code:
            continue

        df = pd.read_parquet(file)
        
        if len(df) < 260:
            continue

        # backtrader용 데이터셋 준비
        df_bt = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df_bt.columns = ['open', 'high', 'low', 'close', 'volume']
        df_bt['market_close'] = market_series.loc[df_bt.index].values
        df_bt['datetime'] = df.index
        df_bt.set_index('datetime', inplace=True)
        
        data = CustomPandasData(dataname=df_bt, name=code)
        return data
    
def filter_pre_market(ticker):
    data_source = yf.Ticker(ticker)
    df_5min = data_source.history(interval='5m', period='7d')
    df_daily = data_source.history(interval='1d', period='40d')
    df = df_5min.copy()
    
    df_5min['date'] = df_5min.index.date
    first_5m = df_5min.groupby('date').first()
    
    df_daily.index = df_daily.index.date
    df_daily['avg_volume'] = df_daily['Volume'].rolling(20).mean()
    df_daily['atr'] = df_daily.ta.atr(length=14)
    
    first_5m['prev_close'] = df_daily['Close'].shift(1).reindex(first_5m.index)
    first_5m['avg_volume'] = df_daily['avg_volume'].reindex(first_5m.index)
    first_5m['atr'] = df_daily['atr'].reindex(first_5m.index)
    first_5m['gap_pct'] = (first_5m['Open'] - first_5m['prev_close']) / first_5m['prev_close'] * 100
    
    cond = (
        (first_5m['gap_pct'] >= 2) &
        (first_5m['Volume'] >= 50000) &
        (first_5m['avg_volume'] >= 500000) &
        (first_5m['atr'] >= 0.5)
    )
    # print(first_5m[['gap_pct', 'Volume', 'avg_volume', 'atr']].describe())
    return df, first_5m[cond].index.tolist()