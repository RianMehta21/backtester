from math import sqrt
from strategy import Strategy
from matplotlib import pyplot as plt
import pandas as pd

class Backtest():
    def __init__(self,data,strategy:Strategy,money=1000,commission=0.001,cash_pct=0.03):
        self.data = data
        self.strategy = strategy
        self.initial_money = money
        self.cash = money
        self.positions = []
        self.trade_history = []
        self.equity_curve=[]
        self.commission = commission
        self.cash_pct = cash_pct

    def run(self):
        signals = self.strategy.generate_signals(self.data)
        for index, series in signals.iterrows():
            signal = series["Signal"]
            self._handle_signal(signal, index, series)
            self._update_portfolio_value(series)

        return self._finalize_results(signals)
    

    def _handle_signal(self, signal, time, row):
        if signal == "HOLD":
            return
        elif signal == "BUY" and self.cash > 0:
            amount = self.initial_money*self.cash_pct if self.cash >= self.initial_money*self.cash_pct else self.cash
            self.positions.append({"type": "LONG", "price": row["Close"], "quantity": (amount)/(row["Close"] * (1 + self.commission)), "time": time})
            self.cash -= amount

        elif signal == "SELL" and self.positions:
            self._handle_sell(row, time)

    def _handle_sell(self,row, time):   
        sell_pos = self.positions.pop(0)
        self._record_trade(sell_pos["time"], time, sell_pos["price"], row["Close"], sell_pos["quantity"])
        self.cash = self.cash + sell_pos["quantity"]*row["Close"] * (1 - self.commission)
        
    def _update_portfolio_value(self, row):
        self.equity_curve.append(self.cash + sum([position["quantity"]*row["Close"] for position in self.positions]))

    def _record_trade(self, entry_time, exit_time, entry_price, exit_price, quantity):
        profit = (exit_price - entry_price) * quantity
        profit_pct = ((exit_price - entry_price) / entry_price) * 100
        self.trade_history.append({"entry_time": entry_time,"exit_time": exit_time,"entry_price": entry_price,"exit_price": exit_price, "quantity": quantity, "profit": profit, "profit_pct": profit_pct})

    def calculate_metrics(self):
        total_return = ((self.cash + sum([position["quantity"]*self.data.iloc[-1]["Close"] for position in self.positions])) - self.initial_money) / self.initial_money * 100
        buy_hold_return = (self.data.iloc[-1]["Close"] - self.data.iloc[0]["Close"]) / self.data.iloc[0]["Close"] * 100

        equity_series = pd.Series(self.equity_curve)
        returns = equity_series.pct_change().dropna()
        if len(returns)>0 and returns.std()!=0:
            sharpe = (returns.mean() / returns.std()) * sqrt(252)
        else:
            sharpe = 0

        cummalative_max = equity_series.cummax()
        drawdown = (equity_series-cummalative_max)/cummalative_max * 100
        max_drawdown = drawdown.min()

        if len(self.trade_history) != 0:
            winning_trades = [trade for trade in self.trade_history if trade["profit"]>0]
            losing_trades =[trade for trade in self.trade_history if trade["profit"]<=0]
            winrate = len(winning_trades)/len(self.trade_history) * 100
            average_win = sum([trade["profit"] for trade in winning_trades])/len(winning_trades) if winning_trades else 0
            average_loss = sum(trade["profit"] for trade in losing_trades)/len(losing_trades) if losing_trades else 0

            profit_factor = sum([trade["profit"] for trade in winning_trades])/abs(sum(trade["profit"] for trade in losing_trades)) if losing_trades else float('inf')
        else:
            winrate = 0
            average_win = 0
            average_loss = 0
            profit_factor = 0

        return {
            'total_return': total_return,
            'buy_hold_return': buy_hold_return,
            'max_drawdown': max_drawdown,
            'sharpe': sharpe,
            'winrate': winrate,
            'average_win': average_win,
            'average_loss': average_loss,
            'profit_factor': profit_factor,
            'num_trades': len(self.trade_history)
        }

    def _finalize_results(self,signals):
        metrics = self.calculate_metrics()

        print("=" * 50)
        print("BACKTEST RESULTS")
        print("=" * 50)
        print("Initial Capital: ${:.2f}".format(self.initial_money))
        print("Final Equity: ${:.2f}".format(self.cash + sum([position["quantity"]*self.data.iloc[-1]["Close"] for position in self.positions])))
        for key, value in metrics.items():
            print(f"{key}: {value}")
        print("=" * 50)

        self._plot_results(metrics,signals)

    def _plot_results(self,metrics,signals):
        fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(8, 6))
        ax1 = axes[0,0]

        ax1.plot(self.data.index, self.data["Close"])
        buy_signals = signals[signals['Signal'] == 'BUY']
        sell_signals = signals[signals['Signal'] == 'SELL']

        ax1.scatter(buy_signals.index, buy_signals["Close"], color = "green", marker = "^", label = "buy")
        ax1.scatter(sell_signals.index, sell_signals["Close"], color = "red", marker = "v", label = "sell")

        ax1.set_title('Price with Buy/Sell Signals')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Price')
        ax1.legend()

        ax2 = axes[0,1]
        buy_hold = self.data["Close"]*(self.initial_money/(self.data.iloc[0]["Close"] * (1 + self.commission)))
        ax2.plot(self.data.index, self.equity_curve, label = "Strategy")
        ax2.plot(self.data.index,buy_hold, linestyle = "--", label="Buy and Hold")
        ax2.set_title('Equity Curve Comparison')
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Portfolio Value ($)')
        ax2.legend()
        
        ax3 = axes[1,0]
        equity_series = pd.Series(self.equity_curve, index=self.data.index)
        cummalative_max = equity_series.cummax()
        drawdown = (equity_series-cummalative_max)/cummalative_max * 100
        ax3.plot(drawdown.index, drawdown, color='red', linewidth=1)
        ax3.set_title(f'Drawdown (Max: {metrics["max_drawdown"]:.2f}%)')
        ax3.set_xlabel('Date')
        ax3.set_ylabel('Drawdown (%)')

        ax4 = axes[1, 1]
        if self.trade_history:
            profits = [t['profit'] for t in self.trade_history]
            colors = ['green' if p > 0 else 'red' for p in profits]
            ax4.bar(range(len(profits)), profits, color=colors, alpha=0.6)
            ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            ax4.set_title('Individual Trade P&L')
            ax4.set_xlabel('Trade Number')
            ax4.set_ylabel('Profit/Loss ($)')

        plt.tight_layout()
        plt.show()