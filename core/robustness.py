# core/robustness.py
"""Robustness testing module for strategy validation."""

import concurrent.futures
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
import random

import pandas as pd
import numpy as np

from .backtest_engine import BacktestEngine, BacktestResult
from strategies.base_strategy import BaseStrategy


class RobustnessAnalyzer:
    """
    Performs robustness tests to validate strategy performance
    across different time periods and market conditions.
    """
    
    # Default fixed test start points
    DEFAULT_TEST_DATES = [
        "2005-12-23",  # Full 20 years
        "2008-01-01",  # Before financial crisis
        "2009-03-01",  # Post crisis bottom
        "2015-01-01",  # Mid-term
        "2020-01-01",  # Before pandemic
        "2020-04-01",  # Post pandemic crash
    ]
    
    def __init__(self, engine: Optional[BacktestEngine] = None):
        """
        Initialize robustness analyzer.
        
        Args:
            engine: BacktestEngine instance (creates new if not provided)
        """
        self.engine = engine or BacktestEngine()
    
    def test_fixed_start_points(
        self,
        strategy: BaseStrategy,
        market_data: pd.DataFrame,
        test_dates: Optional[List[str]] = None,
        end_date: Optional[str] = None,
        frequency: str = 'M',
        base_investment: float = 1000,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> pd.DataFrame:
        """
        Run backtests from multiple fixed starting points.
        
        Args:
            strategy: Strategy to test
            market_data: Full historical price data
            test_dates: List of start dates to test (YYYY-MM-DD)
            end_date: End date for all tests
            frequency: Investment frequency
            base_investment: Base investment amount
            progress_callback: Optional callback(current, total) for progress updates
            
        Returns:
            DataFrame with results for each start date
        """
        if test_dates is None:
            test_dates = self.DEFAULT_TEST_DATES
        
        if end_date is None:
            end_date = market_data.index.max().strftime('%Y-%m-%d')
        
        results = []
        total = len(test_dates)
        
        for i, start_date in enumerate(test_dates):
            try:
                result = self.engine.run_backtest(
                    strategy=strategy,
                    market_data=market_data,
                    start_date=start_date,
                    end_date=end_date,
                    frequency=frequency,
                    base_investment=base_investment
                )
                
                results.append({
                    'start_date': start_date,
                    'end_date': end_date,
                    'months': result.metrics.investment_months,
                    'total_return': result.metrics.total_return,
                    'cagr': result.metrics.cagr,
                    'max_drawdown': result.metrics.max_drawdown,
                    'sharpe_ratio': result.metrics.sharpe_ratio,
                    'final_value': result.metrics.final_value,
                })
            except Exception as e:
                results.append({
                    'start_date': start_date,
                    'end_date': end_date,
                    'months': 0,
                    'total_return': None,
                    'cagr': None,
                    'max_drawdown': None,
                    'sharpe_ratio': None,
                    'final_value': None,
                    'error': str(e)
                })
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        df = pd.DataFrame(results)
        return df
    
    def monte_carlo_simulation(
        self,
        strategy: BaseStrategy,
        market_data: pd.DataFrame,
        num_simulations: int = 300,
        min_duration_years: float = 3,
        max_duration_years: float = 20,
        frequency: str = 'M',
        base_investment: float = 1000,
        num_workers: int = 4,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation with random start dates.
        
        Args:
            strategy: Strategy to test
            market_data: Full historical price data
            num_simulations: Number of random simulations
            min_duration_years: Minimum investment period
            max_duration_years: Maximum investment period
            frequency: Investment frequency
            base_investment: Base investment amount
            num_workers: Number of parallel workers
            progress_callback: Optional callback(current, total) for progress updates
            
        Returns:
            Dictionary with simulation results and statistics
        """
        # Determine valid date range
        data_start = market_data.index.min()
        data_end = market_data.index.max()
        
        min_duration = timedelta(days=int(min_duration_years * 365))
        max_duration = timedelta(days=int(max_duration_years * 365))
        
        # Latest possible start date
        latest_start = data_end - min_duration
        
        # Generate random start dates and durations
        simulations = []
        for _ in range(num_simulations):
            # Random start date
            days_range = (latest_start - data_start).days
            if days_range <= 0:
                continue
            
            random_days = random.randint(0, days_range)
            start_date = data_start + timedelta(days=random_days)
            
            # Random duration
            max_possible_duration = min((data_end - start_date).days, max_duration.days)
            if max_possible_duration < min_duration.days:
                continue
            
            duration_days = random.randint(min_duration.days, max_possible_duration)
            end_date = start_date + timedelta(days=duration_days)
            
            simulations.append({
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
            })
        
        # Run simulations
        results = []
        completed = [0]  # Use list for mutable in closure
        
        def run_single_simulation(sim):
            try:
                result = self.engine.run_backtest(
                    strategy=strategy,
                    market_data=market_data,
                    start_date=sim['start_date'],
                    end_date=sim['end_date'],
                    frequency=frequency,
                    base_investment=base_investment
                )
                return {
                    'start_date': sim['start_date'],
                    'end_date': sim['end_date'],
                    'duration_years': result.metrics.investment_years,
                    'total_return': result.metrics.total_return,
                    'cagr': result.metrics.cagr,
                    'max_drawdown': result.metrics.max_drawdown,
                    'sharpe_ratio': result.metrics.sharpe_ratio,
                }
            except:
                return None
        
        # Use thread pool for parallel execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {executor.submit(run_single_simulation, sim): sim 
                      for sim in simulations}
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
                
                completed[0] += 1
                if progress_callback:
                    progress_callback(completed[0], len(simulations))
        
        # Calculate statistics
        if not results:
            return {'error': 'No successful simulations'}
        
        df = pd.DataFrame(results)
        
        stats = {
            'num_simulations': len(results),
            'returns': {
                'mean': df['total_return'].mean(),
                'median': df['total_return'].median(),
                'std': df['total_return'].std(),
                'min': df['total_return'].min(),
                'max': df['total_return'].max(),
                'percentile_5': df['total_return'].quantile(0.05),
                'percentile_95': df['total_return'].quantile(0.95),
            },
            'cagr': {
                'mean': df['cagr'].mean(),
                'median': df['cagr'].median(),
                'std': df['cagr'].std(),
            },
            'win_rate': (df['total_return'] > 0).mean() * 100,
            'sharpe': {
                'mean': df['sharpe_ratio'].mean(),
                'median': df['sharpe_ratio'].median(),
            },
            'max_drawdown': {
                'mean': df['max_drawdown'].mean(),
                'worst': df['max_drawdown'].max(),
            },
            'raw_results': df,
        }
        
        return stats
    
    def rolling_window_analysis(
        self,
        strategy: BaseStrategy,
        market_data: pd.DataFrame,
        window_years: float = 3,
        step_months: int = 1,
        frequency: str = 'M',
        base_investment: float = 1000,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> pd.DataFrame:
        """
        Analyze strategy performance using rolling time windows.
        
        Args:
            strategy: Strategy to test
            market_data: Full historical price data
            window_years: Window size in years
            step_months: Step size in months
            frequency: Investment frequency
            base_investment: Base investment amount
            progress_callback: Optional callback for progress updates
            
        Returns:
            DataFrame with results for each window
        """
        window_days = int(window_years * 365)
        step_days = step_months * 30
        
        data_start = market_data.index.min()
        data_end = market_data.index.max()
        
        results = []
        
        current_start = data_start
        windows = []
        
        while current_start + timedelta(days=window_days) <= data_end:
            window_end = current_start + timedelta(days=window_days)
            windows.append({
                'start': current_start.strftime('%Y-%m-%d'),
                'end': window_end.strftime('%Y-%m-%d'),
            })
            current_start += timedelta(days=step_days)
        
        total = len(windows)
        
        for i, window in enumerate(windows):
            try:
                result = self.engine.run_backtest(
                    strategy=strategy,
                    market_data=market_data,
                    start_date=window['start'],
                    end_date=window['end'],
                    frequency=frequency,
                    base_investment=base_investment
                )
                
                results.append({
                    'window_start': window['start'],
                    'window_end': window['end'],
                    'total_return': result.metrics.total_return,
                    'cagr': result.metrics.cagr,
                    'max_drawdown': result.metrics.max_drawdown,
                    'sharpe_ratio': result.metrics.sharpe_ratio,
                })
            except:
                pass
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        return pd.DataFrame(results)
    
    def cross_market_test(
        self,
        strategy: BaseStrategy,
        market_data_dict: Dict[str, pd.DataFrame],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        frequency: str = 'M',
        base_investment: float = 1000,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> pd.DataFrame:
        """
        Test strategy across multiple markets.
        
        Args:
            strategy: Strategy to test
            market_data_dict: Dict mapping market symbol to price DataFrame
            start_date: Start date for tests
            end_date: End date for tests
            frequency: Investment frequency
            base_investment: Base investment amount
            progress_callback: Optional callback for progress updates
            
        Returns:
            DataFrame with results for each market
        """
        results = []
        total = len(market_data_dict)
        
        for i, (symbol, data) in enumerate(market_data_dict.items()):
            try:
                result = self.engine.run_backtest(
                    strategy=strategy,
                    market_data=data,
                    start_date=start_date,
                    end_date=end_date,
                    frequency=frequency,
                    base_investment=base_investment,
                    symbol=symbol
                )
                
                results.append({
                    'market': symbol,
                    'total_return': result.metrics.total_return,
                    'cagr': result.metrics.cagr,
                    'max_drawdown': result.metrics.max_drawdown,
                    'sharpe_ratio': result.metrics.sharpe_ratio,
                    'sortino_ratio': result.metrics.sortino_ratio,
                    'total_trades': result.metrics.total_trades,
                })
            except Exception as e:
                results.append({
                    'market': symbol,
                    'error': str(e)
                })
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        return pd.DataFrame(results)
