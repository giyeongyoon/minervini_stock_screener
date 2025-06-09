import pandas as pd
import pandas_ta as ta

def check_trend_template(df: pd.DataFrame) -> bool:
    # 필요한 컬럼이 있는지 확인
    if not all(col in df.columns for col in ['Close']):
        raise ValueError("DataFrame must contain 'Close' column")

    df = df.copy()
    df['SMA_50'] = ta.sma(df['Close'], length=50)
    df['SMA_150'] = ta.sma(df['Close'], length=150)
    df['SMA_200'] = ta.sma(df['Close'], length=200)

    # 최근 200일 이상 데이터 필요
    if len(df) < 200:
        return False

    latest = df.iloc[-1]

    # 1. 주가 > 150일선, 200일선
    cond1 = latest['Close'] > latest['SMA_150'] and latest['Close'] > latest['SMA_200']

    # 2. 150일선 > 200일선
    cond2 = latest['SMA_150'] > latest['SMA_200']

    # 3. 50일선 > 150일선, 200일선
    cond3 = latest['SMA_50'] > latest['SMA_150'] and latest['SMA_50'] > latest['SMA_200']

    # 4. 주가 > 50일선
    cond4 = latest['Close'] > latest['SMA_50']

    # 5. 주가 > 52주 중간값
    past_52_weeks = df['Close'].iloc[-260:]  # 52주 = 260 거래일 기준
    mid_price = (past_52_weeks.max() + past_52_weeks.min()) / 2
    cond5 = latest['Close'] > mid_price

    # 6. 200일선이 1개월 이상 상승 중
    sma_200_trend = df['SMA_200'].iloc[-20:]  # 최근 20일
    cond6 = sma_200_trend.is_monotonic_increasing

    # 전체 조건 평가
    return all([cond1, cond2, cond3, cond4, cond5, cond6])
