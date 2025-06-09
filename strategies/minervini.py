# minervini/main.py
import asyncio 
import pandas as pd

from config import socket_url
from features.rs_calculator import add_mansfield_rs
from core.websocket_client import WebSocketClient
from features.industry import add_industry_names_parallel
from features.vcp import add_vcp
from loguru import logger

async def run_minervini():
	logger.info("Start filtering")
	# WebSocketClient 전역 변수 선언
	websocket_client = WebSocketClient(socket_url)

	# WebSocket 클라이언트를 백그라운드에서 실행합니다.
	receive_task = asyncio.create_task(websocket_client.run())

	# 실시간 항목 등록
	await asyncio.sleep(1)
	await websocket_client.send_message({ 
		'trnm': 'CNSRLST', # TR명
	})

	# 수신 작업이 종료될 때까지 대기
	await asyncio.sleep(1)
	await websocket_client.disconnect()
	await receive_task
	
	df = pd.DataFrame(websocket_client.condition_results)
	df = await add_industry_names_parallel(df)	
	df = add_mansfield_rs(df)
	df = add_vcp(df)
	# df = add_fundamental(df)

	return df