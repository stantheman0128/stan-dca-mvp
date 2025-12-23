# tests/test_basic.py
"""Basic tests to verify core functionality."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import date


def test_strategies_import():
    """Test that all strategies can be imported."""
    from strategies import (
        DCAPureStrategy,
        DCADipBuyingStrategy,
        DCATrendFilterStrategy,
        DCAVolatilityStrategy,
        DCAProfitTakingStrategy,
    )
    
    # Create instances
    v0 = DCAPureStrategy()
    v1 = DCADipBuyingStrategy()
    v2 = DCATrendFilterStrategy()
    v3 = DCAVolatilityStrategy()
    v5 = DCAProfitTakingStrategy()
    
    # Check names
    assert v0.short_name == "V0"
    assert v1.short_name == "V1"
    assert v2.short_name == "V2"
    assert v3.short_name == "V3"
    assert v5.short_name == "V5"
    
    print("✅ All strategies imported successfully")


def test_pure_dca_strategy():
    """Test V0 Pure DCA returns multiplier 1.0."""
    from strategies import DCAPureStrategy
    from strategies.base_strategy import InvestmentDecision
    
    strategy = DCAPureStrategy()
    
    # Create mock data
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    prices = pd.Series(np.linspace(100, 120, 100), index=dates)
    df = pd.DataFrame({'Close': prices})
    
    decision = strategy.calculate_investment(
        current_price=110.0,
        current_date=dates[50],
        historical_data=df,
        portfolio_state={'total_shares': 10, 'total_cost': 1000, 'current_value': 1100, 'cumulative_return': 10}
    )
    
    assert decision.investment_multiplier == 1.0
    assert decision.sell_percentage == 0.0
    
    print("✅ Pure DCA strategy works correctly")


def test_dip_buying_strategy():
    """Test V1 Dip Buying increases multiplier on dip."""
    from strategies import DCADipBuyingStrategy
    
    strategy = DCADipBuyingStrategy()
    
    # Create data with a 15% dip
    dates = pd.date_range('2020-01-01', periods=300, freq='D')
    prices = pd.Series([100] * 250 + [85] * 50, index=dates)  # 15% drop
    df = pd.DataFrame({'Close': prices})
    
    decision = strategy.calculate_investment(
        current_price=85.0,
        current_date=dates[260],
        historical_data=df,
        portfolio_state={'total_shares': 10, 'total_cost': 1000, 'current_value': 850, 'cumulative_return': -15}
    )
    
    # Should trigger first level (10%) multiplier
    assert decision.investment_multiplier == 1.5
    
    print("✅ Dip Buying strategy works correctly")


def test_metrics_calculation():
    """Test basic metrics calculation."""
    from core.metrics import MetricsCalculator
    
    calc = MetricsCalculator()
    
    # Test total return
    total_ret = calc.calculate_total_return(10000, 12000)
    assert abs(total_ret - 20.0) < 0.01
    
    # Test CAGR
    cagr = calc.calculate_cagr(10000, 12000, 2)
    assert cagr > 0  # Should be positive
    
    print("✅ Metrics calculation works correctly")


def test_backtest_engine():
    """Test backtest engine with mock data."""
    from core.backtest_engine import BacktestEngine
    from strategies import DCAPureStrategy
    
    # Create mock price data
    dates = pd.date_range('2020-01-01', periods=500, freq='D')
    np.random.seed(42)
    prices = 100 * np.cumprod(1 + np.random.randn(500) * 0.01)
    df = pd.DataFrame({'Close': prices}, index=dates)
    
    engine = BacktestEngine()
    strategy = DCAPureStrategy()
    
    result = engine.run_backtest(
        strategy=strategy,
        market_data=df,
        frequency='M',
        base_investment=1000,
        symbol='TEST'
    )
    
    # Check result structure
    assert result.symbol == 'TEST'
    assert result.strategy_name == strategy.name
    assert len(result.transactions) > 0
    assert result.metrics.total_trades > 0
    
    print("✅ Backtest engine works correctly")
    print(f"   Total trades: {result.metrics.total_trades}")
    print(f"   Total return: {result.metrics.total_return:.2f}%")
    print(f"   Sharpe ratio: {result.metrics.sharpe_ratio:.2f}")


def test_visualizer():
    """Test visualizer can create figures."""
    from core.visualizer import Visualizer
    from core.backtest_engine import BacktestEngine
    from strategies import DCAPureStrategy, DCADipBuyingStrategy
    
    # Create mock data
    dates = pd.date_range('2020-01-01', periods=500, freq='D')
    np.random.seed(42)
    prices = 100 * np.cumprod(1 + np.random.randn(500) * 0.01)
    df = pd.DataFrame({'Close': prices}, index=dates)
    
    engine = BacktestEngine()
    
    results = []
    for strategy in [DCAPureStrategy(), DCADipBuyingStrategy()]:
        result = engine.run_backtest(strategy, df, frequency='M', base_investment=1000)
        results.append(result)
    
    # Create all chart types
    fig1 = Visualizer.plot_equity_curves(results)
    fig2 = Visualizer.plot_returns(results)
    fig3 = Visualizer.plot_drawdown(results)
    fig4 = Visualizer.plot_metrics_comparison(results)
    fig5 = Visualizer.plot_risk_return_scatter(results)
    
    assert fig1 is not None
    assert fig2 is not None
    assert fig3 is not None
    assert fig4 is not None
    assert fig5 is not None
    
    print("✅ All visualizations created successfully")


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*50)
    print("Running DCA Backtest Tool Tests")
    print("="*50 + "\n")
    
    test_strategies_import()
    test_pure_dca_strategy()
    test_dip_buying_strategy()
    test_metrics_calculation()
    test_backtest_engine()
    test_visualizer()
    
    print("\n" + "="*50)
    print("✅ All tests passed!")
    print("="*50 + "\n")


if __name__ == "__main__":
    run_all_tests()
