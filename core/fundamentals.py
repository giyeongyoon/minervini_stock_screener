# minervini/core/fundamentals.py
from multiprocessing import Pool, cpu_count
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time, random
from bs4 import BeautifulSoup
import pandas as pd
from loguru import logger

def get_code33_worker(stock):
    options = Options()
    options.add_argument("--headless")
    
    chromedriver_path = r"C:\Users\YOON\Desktop\YGY\파이썬\kiwoom_rest\strategies\minervini\chromedriver\chromedriver.exe"

    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get(f"https://m.stock.naver.com/domestic/stock/{stock}/finance/quarter")
        time.sleep(random.uniform(4, 6))

        soup = BeautifulSoup(driver.page_source, "html.parser")
        tables = soup.select("table")
        
        if len(tables) < 2:
            return None  # 구조가 다르면 스킵

        table_html = str(tables[1])
        table_df_list = pd.read_html(table_html)
        table_df = table_df_list[0]

        table_df.set_index("기간", inplace=True)
        table_df.index.name = ""
        table_df = table_df.rename(columns=lambda x: x.replace("최근3개월 전망치 평균", ""))
        table_df = table_df.T

        table_df = table_df.replace("-", pd.NA)
        table_df = table_df.apply(pd.to_numeric, errors="coerce")
        table_df["매출증가율"] = table_df["매출액"].pct_change()
        table_df["순이익증가율"] = table_df["순이익률"].pct_change()
        table_df["EPS증가율"] = table_df["EPS"].pct_change()

        code33 = table_df[["EPS증가율", "매출증가율", "순이익증가율"]].iloc[-4:-1, :]
        row = [stock] + list(code33.values.T.flatten())
        return row
    except Exception as e:
        logger.exception(f"[ERROR] {stock}: {e}")
        return None
    finally:
        driver.quit()
        
def add_fundamental(df):
    logger.info("펀더멘탈 병렬 크롤링 중...")

    stock_list = list(df["종목코드"])

    with Pool(processes=cpu_count()) as pool:
        results = pool.map(get_code33_worker, stock_list)

    df_rows = []
    for stock, row in zip(stock_list, results):
        if row is None:
            logger.warning(f"[WARN] {stock} 펀더멘탈 없음")
            continue
        if len(row) != 10:
            logger.warning(f"[WARN] {stock} 데이터 길이 불일치")
            continue
        df_rows.append(row)

    df_merge = pd.DataFrame(df_rows, columns=[
        "종목코드",
        "Q1 EPS증가율", "Q2 EPS증가율", "Q3 EPS증가율",
        "Q1 매출증가율", "Q2 매출증가율", "Q3 매출증가율",
        "Q1 순이익증가율", "Q2 순이익증가율", "Q3 순이익증가율"
    ])

    new_df = pd.merge(left=df, right=df_merge, how="outer", on="종목코드")
    return new_df