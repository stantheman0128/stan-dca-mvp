# core/__init__.py
"""Core functionality modules."""

from .data_loader import DataLoader
from .backtest_engine import BacktestEngine, BacktestResult
from .metrics import MetricsCalculator

__all__ = [
    'DataLoader',
    'BacktestEngine',
    'BacktestResult',
    'MetricsCalculator',
]
