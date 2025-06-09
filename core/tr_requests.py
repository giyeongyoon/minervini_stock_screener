# minervini/core/utils.py
import requests
from config import api_key, api_secret_key, host
from loguru import logger
import functools
import time


def log_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f'예외 발생: {e}')
    return wrapper


class KiwoomTR:
    def __init__(self):
        self.token = self.login()

    @staticmethod
    def login():
        endpoint = '/oauth2/token'
        url =  host + endpoint

        headers = {
            'Content-Type': 'application/json;charset=UTF-8'
        }

        params = {
            'grant_type': 'client_credentials',
            'appkey': api_key,
            'secretkey': api_secret_key
        }

        response = requests.post(url, headers=headers, json=params)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            error_message = f"HTTP Error: {e}\nResponse Body: {response.text}"
            raise requests.HTTPError(error_message) from e
        token = response.json()['token']
        logger.info("토큰 발급 성공")
        return token
    
    @log_exceptions
    def fn_ka10099(self, data, cont_yn='N', next_key=''):
        endpoint = '/api/dostk/stkinfo'
        url = host + endpoint

        headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'authorization': f'Bearer {self.token}', # 접근토큰
            'cont-yn': cont_yn, # 연속조회여부
            'next-key': next_key, # 연속조회키
            'api-id': 'ka10099', # TR명
        }

        response = requests.post(url, headers=headers, json=data)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            error_message = f"HTTP Error: {e}\nResponse Body: {response.text}"
            raise requests.HTTPError(error_message) from e
        return response.json()['list']
    
    @log_exceptions
    def fn_ka10100(self, data, cont_yn='N', next_key=''):
        endpoint = '/api/dostk/stkinfo'
        url = host + endpoint
        
        headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'authorization': f'Bearer {self.token}', # 접근토큰
            'cont-yn': cont_yn, # 연속조회여부
            'next-key': next_key, # 연속조회키
            'api-id': 'ka10100', # TR명
        }
        
        response = requests.post(url, headers=headers, json=data)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            error_message = f"HTTP Error: {e}\nResponse Body: {response.text}"
            raise requests.HTTPError(error_message) from e
        
        has_next = response.headers.get('cont-yn') == 'Y'
        next_key = response.headers.get('next-key', '')
        up_name = response.json()['upName']
        return up_name, has_next, next_key

if __name__ == '__main__':
    kiwoomtr = KiwoomTR()
    
    stocks_list = ["005930", "034020", "064350"]
    up_names = []
    next_key = ''
    has_next = False
    
    for stock in stocks_list:
        time.sleep(1)
        params = {
            "stk_cd" : f'{stock}'
        }
        up_name, has_next, next_key = kiwoomtr.fn_ka10100(
            data=params,
            cont_yn='Y' if has_next else 'N',
            next_key=next_key
        )
        up_names.append(up_name)
    
    print(up_names)
