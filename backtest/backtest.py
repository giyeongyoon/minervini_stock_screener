import backtrader as bt
import backtrader.analyzers as btanalyzers
import pandas as pd
import os
import glob
from loguru import logger
from strategy import MinerviniVCPStrategy
from custom_data import CustomPandasData


def run_backtest(data_dir='data', market_code='KS11'):
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(1000000.0)
    cerebro.addstrategy(MinerviniVCPStrategy)

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
        
        data_feed = CustomPandasData(dataname=df_bt, name=code)
        cerebro.adddata(data_feed)

    logger.info('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.addanalyzer(btanalyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(btanalyzers.Returns, _name='returns')
    back = cerebro.run()
    logger.info('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
    logger.info('Returns: %.2f' % back[0].analyzers.returns.get_analysis()['rnorm100'])
    logger.info('Sharpe Ratio: %.2f' % back[0].analyzers.sharpe.get_analysis()['sharperatio'])
    
    signal_flags = getattr(back[0], 'signal_flag')
    signal_codes = []
    for i, s in enumerate(signal_flags):
        if s == True:
            signal_codes.append(back[0].datas[i]._name)
            
    for code in signal_codes:      
        df = pd.read_parquet(f'{data_dir}/{code}.parquet')

        df_bt = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df_bt.columns = ['open', 'high', 'low', 'close', 'volume']
        df_bt['market_close'] = market_series.loc[df_bt.index].values
        df_bt['datetime'] = df.index
        df_bt.set_index('datetime', inplace=True)

        plot_data = CustomPandasData(dataname=df_bt, name=code)

        plot_cerebro = bt.Cerebro()
        plot_cerebro.broker.setcash(1000000.0)
        plot_cerebro.addstrategy(MinerviniVCPStrategy)
        plot_cerebro.adddata(plot_data)
        plot_cerebro.run()
        plot_cerebro.plot()
    

if __name__ == "__main__":
    run_backtest()
