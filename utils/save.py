import FinanceDataReader as fdr
import os
import time

# 저장 폴더
DIR = 'data'
os.makedirs(DIR, exist_ok=True)

# 날짜 범위
START_DATE = '2020-01-01'
END_DATE = '2025-01-01'

def fetch_stock_data(ticker):
    try:
        df = fdr.DataReader(ticker, start=START_DATE, end=END_DATE)
        if df.empty:
            print(f"{ticker} 데이터 없음")
            return False
        df['종목코드'] = ticker  # 종목코드 추가

        # Parquet 저장: 종목코드별로 폴더 나눠 저장
        df.to_parquet(
            os.path.join(DIR, f"{ticker}.parquet"),
            engine='pyarrow',
            index=True  # 날짜 인덱스 유지
        )

        print(f"저장 완료: {ticker}")
        return True
    except Exception as e:
        print(f"{ticker} 처리 중 오류 발생: {e}")
        return False

def main():
    kospi = fdr.StockListing('KOSPI')
    fail_list = []

    for idx, row in kospi.iterrows():
        ticker = row['Code']
        success = fetch_stock_data(ticker)
        if not success:
            fail_list.append(ticker)
        time.sleep(0.5)  # API 과부하 방지
        
    success = fetch_stock_data('KS11')
    if not success:
        fail_list.append('KS11')
        
    print("=== 실패 종목 리스트 ===")
    print(fail_list)

if __name__ == "__main__":
    main()