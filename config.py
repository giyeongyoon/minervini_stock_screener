# minervini/config.py
import os
from dotenv import load_dotenv

load_dotenv()

is_paper_trading = False
api_key = os.getenv("API_KEY")
api_secret_key = os.getenv("API_SECRET_KEY")

host = "https://mockapi.kiwoom.com" if is_paper_trading else "https://api.kiwoom.com"
socket_url = "wss://mockapi.kiwoom.com:10000/api/dostk/websocket" if is_paper_trading else "wss://api.kiwoom.com:10000/api/dostk/websocket"