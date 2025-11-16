import yfinance as yf
from backtest import Backtest
from rsi_strategy import RSIStrategy

for ticker in ["RGEF","CUBI","IFS"]:
    data = yf.Ticker(ticker).history(interval="5m",period="1mo")
    data.columns = data.columns.get_level_values(0)
    print(data.columns)

    backtest = Backtest(data, RSIStrategy())
    backtest.run()
