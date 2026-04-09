from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from ..domain import MarketData, PortfolioWeights


@dataclass(frozen=True)
class BacktestResult:
    period_returns: dict[str, float]
    equity_curve: dict[str, float]
    cumulative_return: float
    turnover: dict[str, float]
    metrics: dict[str, float]


@dataclass(frozen=True)
class BacktestEngine:
    initial_capital: float = 1.0
    annualization_factor: int = 252
    transaction_cost_rate: float = 0.0
    slippage_rate: float = 0.0

    def run(self, market_data: MarketData, portfolio_weights: PortfolioWeights) -> BacktestResult:
        dates = market_data.dates()
        period_returns: dict[str, float] = {}
        equity_curve: dict[str, float] = {}
        turnover: dict[str, float] = {}
        equity = self.initial_capital
        current_weights: dict[str, float] = {}
        for idx in range(len(dates) - 1):
            current_date = dates[idx]
            next_date = dates[idx + 1]
            target_weights = portfolio_weights.weights.get(current_date)
            if target_weights is not None:
                current_weights = target_weights
                turnover[current_date] = self._calculate_turnover(current_weights, portfolio_weights.weights, current_date)
            if not current_weights:
                continue
            current_prices = market_data.prices[current_date]
            next_prices = market_data.prices[next_date]
            portfolio_return = 0.0
            for asset, weight in current_weights.items():
                if asset not in current_prices or asset not in next_prices:
                    continue
                asset_return = (next_prices[asset] / current_prices[asset]) - 1.0
                portfolio_return += weight * asset_return
            if current_date in turnover:
                trading_drag = turnover[current_date] * (self.transaction_cost_rate + self.slippage_rate)
                portfolio_return -= trading_drag
            equity *= 1.0 + portfolio_return
            period_returns[next_date] = portfolio_return
            equity_curve[next_date] = equity
        cumulative = (equity / self.initial_capital) - 1.0 if self.initial_capital else 0.0
        metrics = self._calculate_metrics(period_returns, equity_curve, turnover)
        return BacktestResult(
            period_returns=period_returns,
            equity_curve=equity_curve,
            cumulative_return=cumulative,
            turnover=turnover,
            metrics=metrics,
        )

    def _calculate_turnover(
        self,
        target_weights: dict[str, float],
        all_weights: dict[str, dict[str, float]],
        current_date: str,
    ) -> float:
        rebalance_dates = sorted(all_weights.keys())
        current_index = rebalance_dates.index(current_date)
        previous_weights = all_weights[rebalance_dates[current_index - 1]] if current_index > 0 else {}
        if not previous_weights and target_weights:
            return 1.0
        assets = set(previous_weights) | set(target_weights)
        return 0.5 * sum(abs(target_weights.get(asset, 0.0) - previous_weights.get(asset, 0.0)) for asset in assets)

    def _calculate_metrics(
        self,
        period_returns: dict[str, float],
        equity_curve: dict[str, float],
        turnover: dict[str, float],
    ) -> dict[str, float]:
        returns = list(period_returns.values())
        if not returns:
            return {
                "annualized_return": 0.0,
                "annualized_volatility": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
                "turnover_rate": 0.0,
            }
        periods = len(returns)
        ending_equity = list(equity_curve.values())[-1]
        annualized_return = (ending_equity / self.initial_capital) ** (self.annualization_factor / periods) - 1.0
        mean_return = sum(returns) / periods
        variance = sum((value - mean_return) ** 2 for value in returns) / periods
        volatility = sqrt(variance) * sqrt(self.annualization_factor)
        sharpe = (mean_return / sqrt(variance) * sqrt(self.annualization_factor)) if variance > 0 else 0.0
        max_drawdown = self._max_drawdown(equity_curve)
        win_rate = sum(1 for value in returns if value > 0) / periods
        turnover_rate = sum(turnover.values()) / len(turnover) if turnover else 0.0
        return {
            "annualized_return": annualized_return,
            "annualized_volatility": volatility,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "turnover_rate": turnover_rate,
        }

    def _max_drawdown(self, equity_curve: dict[str, float]) -> float:
        peak = self.initial_capital
        max_drawdown = 0.0
        for equity in equity_curve.values():
            if equity > peak:
                peak = equity
            drawdown = (equity / peak) - 1.0
            if drawdown < max_drawdown:
                max_drawdown = drawdown
        return max_drawdown
