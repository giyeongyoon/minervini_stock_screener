import backtrader as bt
import backtrader.analyzers as btanalyzers
from loguru import logger
import pandas as pd
from strategy import (
    MinerviniVCPStrategy, 
    VWAPIntradayStrategy, 
    VWAPIntradayWithFilters, 
    VWAPIntradayStrategy2        
)
from brokers import get_ohlc_minervini_data, get_ohlc_pandas_data, filter_pre_market


def run_backtest(strategy, init_cash=1000000, commission=0.0005, plot=False):
    
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(init_cash)
    cerebro.broker.setcommission(commission=commission)
    
    data_dict = {}
    
    if strategy == 'minervini':
        cerebro.addstrategy(MinerviniVCPStrategy)
        data = get_ohlc_minervini_data()
        cerebro.adddata(data)
    elif strategy in ['vwap', 'vwapbb']:
        strategy_cls = VWAPIntradayStrategy if strategy == 'vwap' else VWAPIntradayWithFilters
        cerebro.addstrategy(strategy_cls)
        data = get_ohlc_pandas_data("MES=F", "1h", "1y")
        cerebro.adddata(data)
    elif strategy == 'vwap_multi':
        cerebro.addstrategy(VWAPIntradayStrategy2)
        
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_400_companies'
        df = pd.read_html(url)[0]
        tickers = df['Symbol'].tolist()
        tickers = [ticker.replace('.', '-') for ticker in tickers]
        
        logger.info("장전 관심종목 검색 시작")
        for tic in tickers:
            try:
                df, passed_dates = filter_pre_market(tic)
            except:
                continue
            
            if not passed_dates:
                continue
            
            df_feed = df[pd.Series(df.index.normalize().date, index=df.index).isin(passed_dates)].copy()
            if df_feed.empty:
                continue
            
            logger.info(f"필터통과: {tic}")
            df_bt = df_feed[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
            df_bt.columns = ['open', 'high', 'low', 'close', 'volume']
            data = bt.feeds.PandasData(dataname=df_bt, name=tic)
            cerebro.adddata(data)
            data_dict[tic] = df_bt
        
    else:
        raise ValueError(f"Unkown strategy type: {strategy}")
    
    cerebro.addanalyzer(btanalyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(btanalyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    logger.info("백테스트 시작")
    logger.info('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    back = cerebro.run()
        
    logger.info('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
    logger.info('Total Returns: %.2f' % back[0].analyzers.returns.get_analysis()['rtot'])
    try:
        logger.info('Sharpe Ratio: %.2f' % back[0].analyzers.sharpe.get_analysis()['sharperatio'])
    except:
        logger.info('Sharpe Ratio is None')
    logger.info('Max Drawdown: %2f' % back[0].analyzers.drawdown.get_analysis()['max']['drawdown'])
    
    trades = back[0].analyzers.trades.get_analysis()
    logger.info(f"Total Trades: {trades.total.get('total', 0)}")
    logger.info(f"Winning Trades: {trades.won.get('total', 0)}")
    logger.info(f"Losing Trades: {trades.lost.get('total', 0)}")
    
    if plot and strategy in ['vwap', 'vwapbb']:
        cerebro.plot(style='candlestick')  
    else:
        logger.warning(f"{strategy} is not supported for plotting") 
    
    return back, data_dict
    
def vwap_multi_plot(back, data_dict, init_cash=1000, commission=0.0005):
    values = []
    signal_flags = getattr(back[0], 'signal_flag')
    signal_codes = []
    for i, s in enumerate(signal_flags):
        if s:
            signal_codes.append(back[0].datas[i]._name)
            
    for code in signal_codes:      
        df_bt = data_dict.get(code)
        if df_bt is None or df_bt.empty:
            continue
        
        logger.info(f"필터통과: {code}")
        data = bt.feeds.PandasData(dataname=df_bt, name=code)
        
        plot_cerebro = bt.Cerebro()
        plot_cerebro.broker.setcash(init_cash)
        plot_cerebro.broker.setcommission(commission=commission)
        plot_cerebro.addstrategy(VWAPIntradayStrategy2)
        plot_cerebro.adddata(data)
        
        logger.info("백테스트 시작")
        logger.info('Starting Portfolio Value: %.2f' % plot_cerebro.broker.getvalue())
        plot_cerebro.run()
        logger.info('Final Portfolio Value: %.2f' % plot_cerebro.broker.getvalue())
        values.append(plot_cerebro.broker.getvalue())
        plot_cerebro.plot(style='candlestick', volume=True)
        
    logger.info(f"Total Returns: {(sum(values) - init_cash * len(values)) / init_cash * len(values)}:.2f")
    logger.info(f"Final Value: {init_cash + (sum(values) - init_cash * len(values))}:.2f")
        

if __name__ == "__main__":
    back, data_dict = run_backtest(strategy='vwap_multi', init_cash=1000)
    vwap_multi_plot(back, data_dict)
    