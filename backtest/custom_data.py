import backtrader as bt


class CustomPandasData(bt.feeds.PandasData):
    lines = ('market_close',)
    params = (
        ('datetime', None),         
        ('open', -1),
        ('high', -1),
        ('low', -1),
        ('close', -1),
        ('volume', -1),
        ('openinterest', None),
        ('market_close', -1),       
    )
    
    