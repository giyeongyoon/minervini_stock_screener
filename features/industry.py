import asyncio
from loguru import logger
from core.tr_requests import KiwoomTR


async def fetch_industry_name(kiwoom_tr, stock_code, semaphore):
    async with semaphore:
        params = {'stk_cd': stock_code}
        loop = asyncio.get_event_loop()
        up_name, has_next, next_key = await loop.run_in_executor(
            None,
            lambda: kiwoom_tr.fn_ka10100(data=params)
        )
        await asyncio.sleep(1)  # 제한 속도 유지
        return up_name
    
async def add_industry_names_parallel(df):
	logger.info("업종명 조회")
	kiwoom_tr = KiwoomTR()
	semaphore = asyncio.Semaphore(15)  # 동시에 20개만 호출 허용

	tasks = [fetch_industry_name(kiwoom_tr, code, semaphore) for code in df['종목코드']]
	up_names = await asyncio.gather(*tasks)
	df['업종명'] = up_names
	return df