# core/backtest_engine.py
"""Backtest engine for DCA strategy simulation."""

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Any, Optional, List, Union

import pandas as pd
import numpy as np

from strategies.base_strategy import BaseStrategy, InvestmentDecision
from .metrics import MetricsCalculator, PerformanceMetrics


@dataclass
class BacktestResult:
    """Container for complete backtest results."""
    
    # Configuration
    symbol: str = ""
    strategy_name: str = ""
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    start_date: str = ""
    end_date: str = ""
    frequency: str = "M"
    base_investment: float = 1000.0
    
    # Results
    transactions: pd.DataFrame = field(default_factory=pd.DataFrame)
    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)
    metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    
    # Decision log
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'symbol': self.symbol,
            'strategy_name': self.strategy_name,
            'strategy_params': self.strategy_params,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'frequency': self.frequency,
            'base_investment': self.base_investment,
            'transactions': self.transactions.to_dict('records'),
            'equity_curve': self.equity_curve.to_dict('records'),
            'metrics': self.metrics.to_dict(),
            'decisions': self.decisions,
        }


class BacktestEngine:
    """
    Engine for running DCA strategy backtests.
    
    Simulates periodic investment according to a strategy,
    tracks all transactions, and calculates performance metrics.
    """
    
    # Frequency mapping to pandas resample rule
    FREQUENCY_MAP = {
        'W': 'W-MON',  # Weekly (Monday)
        'M': 'MS',      # Monthly (Month Start)
        'Q': 'QS',      # Quarterly (Quarter Start)
    }
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize backtest engine.
        
        Args:
            risk_free_rate: Annual risk-free rate for metrics calculation
        """
        self.metrics_calculator = MetricsCalculator(risk_free_rate)
    
    def run_backtest(
        self,
        strategy: BaseStrategy,
        market_data: pd.DataFrame,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        frequency: str = 'M',
        base_investment: float = 1000.0,
        symbol: str = ""
    ) -> BacktestResult:
        """
        Run a complete backtest simulation.
        
        Args:
            strategy: Strategy instance to use
            market_data: DataFrame with price data (must have 'Close' column)
            start_date: Start date for backtest (YYYY-MM-DD)
            end_date: End date for backtest (YYYY-MM-DD)
            frequency: Investment frequency ('W', 'M', 'Q')
            base_investment: Base investment amount per period
            symbol: Market symbol for reference
            
        Returns:
            BacktestResult with complete simulation results
        """
        # Validate inputs
        if market_data.empty:
            raise ValueError("Market data is empty")
        
        if 'Close' not in market_data.columns:
            raise ValueError("Market data must have 'Close' column")
        
        # Prepare data
        data = market_data.copy()
        data.index = pd.to_datetime(data.index)
        data = data.sort_index()
        
        # Filter date range
        if start_date:
            data = data[data.index >= start_date]
        if end_date:
            data = data[data.index <= end_date]
        
        if data.empty:
            raise ValueError("No data in specified date range")
        
        # Resample to investment frequency (get first trading day of each period)
        resample_rule = self.FREQUENCY_MAP.get(frequency, 'MS')
        investment_dates = data['Close'].resample(resample_rule).first().dropna()
        
        if len(investment_dates) < 2:
            raise ValueError("Insufficient data points for backtest")
        
        # Initialize tracking variables
        total_shares = 0.0
        total_cost = 0.0
        transactions = []
        decisions = []
        
        # Run simulation
        for invest_date, price in investment_dates.items():
            price = float(price)
            
            # Get historical data up to this point
            historical = data[data.index <= invest_date]
            
            # Calculate portfolio state
            current_value = total_shares * price
            cumulative_return = ((current_value - total_cost) / total_cost * 100 
                                if total_cost > 0 else 0.0)
            
            portfolio_state = {
                'total_shares': total_shares,
                'total_cost': total_cost,
                'current_value': current_value,
                'cumulative_return': cumulative_return,
            }
            
            # Get investment decision from strategy
            decision = strategy.calculate_investment(
                current_price=price,
                current_date=invest_date,
                historical_data=historical,
                portfolio_state=portfolio_state
            )
            
            # Calculate actual investment
            investment = base_investment * decision.investment_multiplier
            
            # Handle selling (if applicable)
            shares_sold = 0.0
            sell_proceeds = 0.0
            if decision.sell_percentage > 0 and total_shares > 0:
                shares_sold = total_shares * decision.sell_percentage
                sell_proceeds = shares_sold * price
                total_shares -= shares_sold
            
            # Buy shares
            shares_bought = investment / price
            total_shares += shares_bought
            total_cost += investment
            
            # Update current value
            current_value = total_shares * price
            return_pct = ((current_value - total_cost) / total_cost * 100 
                         if total_cost > 0 else 0.0)
            
            # Record transaction
            transactions.append({
                'date': invest_date,
                'price': price,
                'investment': investment,
                'multiplier': decision.investment_multiplier,
                'shares_bought': shares_bought,
                'shares_sold': shares_sold,
                'sell_proceeds': sell_proceeds,
                'total_shares': total_shares,
                'total_cost': total_cost,
                'current_value': current_value,
                'return_pct': return_pct,
            })
            
            # Record decision
            decisions.append({
                'date': invest_date.strftime('%Y-%m-%d'),
                'price': price,
                'decision': decision.reason,
                'multiplier': decision.investment_multiplier,
            })
        
        # Create DataFrames
        transactions_df = pd.DataFrame(transactions)
        
        # Create equity curve (use transaction data)
        equity_curve = transactions_df[['date', 'current_value', 'total_cost', 'return_pct']].copy()
        equity_curve.columns = ['date', 'value', 'cost', 'return_pct']
        
        # Calculate metrics
        metrics = self.metrics_calculator.calculate_all_metrics(
            transactions=transactions_df,
            equity_curve=equity_curve
        )
        
        # Build result
        result = BacktestResult(
            symbol=symbol,
            strategy_name=strategy.name,
            strategy_params=strategy.params.copy(),
            start_date=str(investment_dates.index[0].date()),
            end_date=str(investment_dates.index[-1].date()),
            frequency=frequency,
            base_investment=base_investment,
            transactions=transactions_df,
            equity_curve=equity_curve,
            metrics=metrics,
            decisions=decisions,
        )
        
        return result
    
    def run_batch_backtest(
        self,
        strategies: List[BaseStrategy],
        market_data: pd.DataFrame,
        **kwargs
    ) -> List[BacktestResult]:
        """
        Run backtest for multiple strategies.
        
        Args:
            strategies: List of strategy instances
            market_data: Price data DataFrame
            **kwargs: Additional arguments passed to run_backtest
            
        Returns:
            List of BacktestResult, one per strategy
        """
        results = []
        for strategy in strategies:
            try:
                result = self.run_backtest(strategy, market_data, **kwargs)
                results.append(result)
            except Exception as e:
                print(f"Error running {strategy.name}: {e}")
        
        return results
    
    def compare_strategies(
        self,
        results: List[BacktestResult]
    ) -> pd.DataFrame:
        """
        Create a comparison table for multiple backtest results.
        
        Args:
            results: List of BacktestResult objects
            
        Returns:
            DataFrame with strategies as columns and metrics as rows
        """
        if not results:
            return pd.DataFrame()
        
        comparison = {}
        for result in results:
            metrics = result.metrics
            comparison[result.strategy_name] = {
                '總報酬率 (%)': f"{metrics.total_return:.2f}",
                '年化報酬率 (%)': f"{metrics.cagr:.2f}",
                '最大回撤 (%)': f"{metrics.max_drawdown:.2f}",
                '年化波動率 (%)': f"{metrics.volatility:.2f}",
                '夏普比率': f"{metrics.sharpe_ratio:.2f}",
                '索提諾比率': f"{metrics.sortino_ratio:.2f}",
                '卡爾馬比率': f"{metrics.calmar_ratio:.2f}",
                '總投入': f"{metrics.total_invested:,.0f}",
                '最終市值': f"{metrics.final_value:,.0f}",
                '交易次數': metrics.total_trades,
                '勝率 (%)': f"{metrics.win_rate:.1f}",
            }
        
        return pd.DataFrame(comparison)
