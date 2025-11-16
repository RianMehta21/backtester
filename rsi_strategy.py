from strategy import Strategy
import pandas as pd

class RSIStrategy(Strategy):
    def __init__(self, period=14, overbought=70, oversold=30):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold

    def calculate_rsi(self, close_series: pd.Series) -> pd.Series:
        delta = close_series.diff()

        gain = delta.where(delta > 0, 0).rolling(window=self.period).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=self.period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        out = data.copy()
        out['RSI'] = self.calculate_rsi(out['Close'])

        out['Signal'] = 'HOLD'
        out.loc[out['RSI'] > self.overbought, 'Signal'] = 'SELL'
        out.loc[out['RSI'] < self.oversold, 'Signal'] = 'BUY'

        return out