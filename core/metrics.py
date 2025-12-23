# core/metrics.py
"""Performance metrics calculation module."""

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np


@dataclass
class PerformanceMetrics:
    """Container for all calculated performance metrics."""
    
    # Return metrics
    total_return: float = 0.0           # Total return percentage
    total_return_amount: float = 0.0    # Absolute return amount
    cagr: float = 0.0                   # Compound Annual Growth Rate
    annual_returns: Dict[int, float] = None  # Year -> return percentage
    
    # Risk metrics
    max_drawdown: float = 0.0           # Maximum drawdown percentage
    max_drawdown_duration: int = 0      # Days in max drawdown
    volatility: float = 0.0             # Annualized volatility
    downside_volatility: float = 0.0    # Downside deviation
    var_99: float = 0.0                 # 99% Value at Risk
    
    # Risk-adjusted metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Trade statistics
    total_trades: int = 0
    average_cost: float = 0.0           # Average cost per share
    total_invested: float = 0.0
    final_value: float = 0.0
    total_shares: float = 0.0
    investment_months: int = 0
    investment_years: float = 0.0
    win_rate: float = 0.0               # % of positive return periods
    
    def __post_init__(self):
        if self.annual_returns is None:
            self.annual_returns = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for display/export."""
        return {
            '總報酬率': f"{self.total_return:.2f}%",
            '總報酬金額': self.total_return_amount,
            '年化報酬率 (CAGR)': f"{self.cagr:.2f}%",
            '最大回撤': f"{self.max_drawdown:.2f}%",
            '年化波動率': f"{self.volatility:.2f}%",
            '夏普比率': f"{self.sharpe_ratio:.2f}",
            '索提諾比率': f"{self.sortino_ratio:.2f}",
            '卡爾馬比率': f"{self.calmar_ratio:.2f}",
            '總投入': self.total_invested,
            '最終市值': self.final_value,
            '投資期間': f"{self.investment_months} 個月",
            '交易次數': self.total_trades,
            '勝率': f"{self.win_rate:.1f}%",
            'VaR 99%': f"{self.var_99:.2f}%",
        }


class MetricsCalculator:
    """
    Calculate performance metrics for backtest results.
    
    All methods are static or class methods for easy use without instantiation.
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize calculator with risk-free rate.
        
        Args:
            risk_free_rate: Annual risk-free rate (default 2%)
        """
        self.risk_free_rate = risk_free_rate
    
    def calculate_all_metrics(
        self,
        transactions: pd.DataFrame,
        equity_curve: pd.DataFrame,
        daily_prices: Optional[pd.DataFrame] = None
    ) -> PerformanceMetrics:
        """
        Calculate all performance metrics.
        
        Args:
            transactions: Transaction history DataFrame with columns:
                [date, price, investment, shares_bought, total_shares, 
                 total_cost, current_value, return_pct]
            equity_curve: Daily equity curve DataFrame with columns:
                [date, value, cost, return_pct]
            daily_prices: Optional daily price data for volatility calculations
            
        Returns:
            PerformanceMetrics object with all calculations
        """
        metrics = PerformanceMetrics()
        
        if transactions.empty or equity_curve.empty:
            return metrics
        
        # Basic info
        metrics.total_trades = len(transactions)
        metrics.total_invested = transactions['total_cost'].iloc[-1]
        metrics.final_value = transactions['current_value'].iloc[-1]
        metrics.total_shares = transactions['total_shares'].iloc[-1]
        
        # Return metrics
        metrics.total_return = self.calculate_total_return(
            metrics.total_invested, metrics.final_value
        )
        metrics.total_return_amount = metrics.final_value - metrics.total_invested
        
        # Time period
        start_date = transactions['date'].iloc[0]
        end_date = transactions['date'].iloc[-1]
        metrics.investment_months = len(transactions)
        metrics.investment_years = (end_date - start_date).days / 365.25
        
        # CAGR
        metrics.cagr = self.calculate_cagr(
            metrics.total_invested, metrics.final_value, metrics.investment_years
        )
        
        # Annual returns
        metrics.annual_returns = self.calculate_annual_returns(transactions)
        
        # Average cost
        if metrics.total_shares > 0:
            metrics.average_cost = metrics.total_invested / metrics.total_shares
        
        # Risk metrics from equity curve
        # Calculate period returns from equity values
        if 'value' in equity_curve.columns:
            values = equity_curve['value']
        else:
            values = equity_curve['current_value'] if 'current_value' in equity_curve.columns else transactions['current_value']
        
        # Calculate period-to-period returns
        returns = values.pct_change().dropna()
        
        # Remove infinite values
        returns = returns.replace([np.inf, -np.inf], np.nan).dropna()
        
        metrics.max_drawdown, metrics.max_drawdown_duration = self.calculate_max_drawdown(values)
        
        if len(returns) > 1:
            metrics.volatility = self.calculate_volatility(returns)
            metrics.downside_volatility = self.calculate_downside_volatility(returns)
            metrics.var_99 = self.calculate_var(returns, 0.01)
            
            # Risk-adjusted metrics
            metrics.sharpe_ratio = self.calculate_sharpe_ratio(
                metrics.cagr, metrics.volatility
            )
            metrics.sortino_ratio = self.calculate_sortino_ratio(
                metrics.cagr, metrics.downside_volatility
            )
            metrics.calmar_ratio = self.calculate_calmar_ratio(
                metrics.cagr, metrics.max_drawdown
            )
        
        # Win rate
        metrics.win_rate = self.calculate_win_rate(transactions)
        
        return metrics
    
    @staticmethod
    def calculate_total_return(total_cost: float, final_value: float) -> float:
        """
        Calculate total return percentage.
        
        Formula: (final_value - total_cost) / total_cost * 100
        """
        if total_cost <= 0:
            return 0.0
        return (final_value - total_cost) / total_cost * 100
    
    @staticmethod
    def calculate_cagr(
        total_cost: float, 
        final_value: float, 
        years: float
    ) -> float:
        """
        Calculate Compound Annual Growth Rate.
        
        Formula: [(final_value / total_cost) ^ (1/years)] - 1
        
        Note: For DCA, this is an approximation since investments
        are made at different times.
        """
        if total_cost <= 0 or years <= 0 or final_value <= 0:
            return 0.0
        
        return ((final_value / total_cost) ** (1 / years) - 1) * 100
    
    @staticmethod
    def calculate_annual_returns(transactions: pd.DataFrame) -> Dict[int, float]:
        """
        Calculate return for each calendar year.
        
        Returns:
            Dictionary mapping year to return percentage
        """
        if transactions.empty:
            return {}
        
        transactions = transactions.copy()
        transactions['year'] = pd.to_datetime(transactions['date']).dt.year
        
        annual_returns = {}
        years = sorted(transactions['year'].unique())
        
        for year in years:
            year_data = transactions[transactions['year'] == year]
            if len(year_data) > 0:
                # Year-end value vs year-start cost
                year_end = year_data.iloc[-1]
                year_start = year_data.iloc[0]
                
                # Calculate return for the year
                start_value = year_start['current_value'] - year_start['investment']
                if start_value > 0:
                    year_return = (year_end['current_value'] - start_value - 
                                   year_data['investment'].sum()) / start_value * 100
                else:
                    year_return = year_end['return_pct']
                
                annual_returns[year] = year_return
        
        return annual_returns
    
    @staticmethod
    def calculate_max_drawdown(values: pd.Series) -> Tuple[float, int]:
        """
        Calculate maximum drawdown and its duration.
        
        Returns:
            Tuple of (max_drawdown_percentage, duration_in_days)
        """
        if values.empty or len(values) < 2:
            return 0.0, 0
        
        # Calculate running maximum
        running_max = values.expanding().max()
        
        # Calculate drawdown series
        drawdowns = (values - running_max) / running_max * 100
        
        # Max drawdown
        max_dd = drawdowns.min()
        
        # Duration (simplified - time from peak to trough)
        peak_idx = values.idxmax()
        if isinstance(values.index, pd.DatetimeIndex):
            post_peak = values[values.index >= peak_idx]
            trough_idx = post_peak.idxmin()
            duration = (trough_idx - peak_idx).days
        else:
            duration = 0
        
        return abs(max_dd), duration
    
    @staticmethod
    def calculate_volatility(returns: pd.Series, periods_per_year: int = 12) -> float:
        """
        Calculate annualized volatility.
        
        Args:
            returns: Period returns series
            periods_per_year: Number of periods per year (12 for monthly)
        """
        if returns.empty or len(returns) < 2:
            return 0.0
        
        return returns.std() * np.sqrt(periods_per_year) * 100
    
    @staticmethod
    def calculate_downside_volatility(
        returns: pd.Series, 
        periods_per_year: int = 12,
        threshold: float = 0.0
    ) -> float:
        """
        Calculate downside deviation (only negative returns).
        
        Args:
            returns: Period returns series
            periods_per_year: Number of periods per year
            threshold: Minimum acceptable return (default 0)
        """
        if returns.empty:
            return 0.0
        
        # Only consider returns below threshold
        downside_returns = returns[returns < threshold]
        
        if len(downside_returns) < 2:
            return 0.0
        
        return downside_returns.std() * np.sqrt(periods_per_year) * 100
    
    @staticmethod
    def calculate_var(returns: pd.Series, percentile: float = 0.01) -> float:
        """
        Calculate Value at Risk.
        
        Args:
            returns: Period returns series
            percentile: VaR percentile (0.01 for 99% VaR)
        """
        if returns.empty:
            return 0.0
        
        return np.percentile(returns, percentile * 100) * 100
    
    def calculate_sharpe_ratio(self, cagr: float, volatility: float) -> float:
        """
        Calculate Sharpe Ratio.
        
        Formula: (annual_return - risk_free_rate) / volatility
        """
        if volatility <= 0:
            return 0.0
        
        risk_free_pct = self.risk_free_rate * 100
        return (cagr - risk_free_pct) / volatility
    
    def calculate_sortino_ratio(self, cagr: float, downside_vol: float) -> float:
        """
        Calculate Sortino Ratio.
        
        Formula: (annual_return - risk_free_rate) / downside_volatility
        """
        if downside_vol <= 0:
            return 0.0
        
        risk_free_pct = self.risk_free_rate * 100
        return (cagr - risk_free_pct) / downside_vol
    
    @staticmethod
    def calculate_calmar_ratio(cagr: float, max_drawdown: float) -> float:
        """
        Calculate Calmar Ratio.
        
        Formula: annual_return / max_drawdown
        """
        if max_drawdown <= 0:
            return 0.0
        
        return cagr / max_drawdown
    
    @staticmethod
    def calculate_win_rate(transactions: pd.DataFrame) -> float:
        """
        Calculate win rate (percentage of positive return periods).
        """
        if transactions.empty or 'return_pct' not in transactions.columns:
            return 0.0
        
        positive_periods = (transactions['return_pct'] > 0).sum()
        total_periods = len(transactions)
        
        if total_periods == 0:
            return 0.0
        
        return (positive_periods / total_periods) * 100
