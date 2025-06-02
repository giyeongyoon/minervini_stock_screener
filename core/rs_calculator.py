# minervini/core/rs_calculator.py
import FinanceDataReader as fdr
from ta.trend import SMAIndicator
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

def add_mansfield_rs(df, market_code='KS11', ma_length=52):
    logger.info("Mansfield Relative Strength 계산")
    end = datetime.today()
    start = end - timedelta(weeks=(ma_length + 10))
    
    codes = df['종목코드'].tolist()
    
    df_list = [fdr.DataReader(code, start, end)[['Close']].resample('W').last() for code in codes]
    stock_df = pd.concat(df_list, axis=1)
    stock_df.columns = [code for code in codes]
    market_df = fdr.DataReader(market_code, start, end)[["Close"]].resample("W").last()
    market_df.rename(columns={'Close': '지수'}, inplace=True)
    combined = stock_df.join(market_df, how='inner')
    
    mansfield_dict = {}
    for code in stock_df.columns:
        rs = (combined[code] / combined['지수']) * 100
        zero_line = SMAIndicator(rs, window=ma_length).sma_indicator()
        mansfield = ((rs / zero_line) - 1) * 100
        mansfield_dict[code] = mansfield.iloc[-1] if not mansfield.isna().all() else None
        
    df['Mansfield_RS'] = df['종목코드'].map(mansfield_dict)
    return df


if __name__ == '__main__':
    add_mansfield_rs(['000150', '005930', '000660'])