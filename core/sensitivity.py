# core/sensitivity.py
"""Parameter sensitivity analysis module."""

from typing import List, Dict, Any, Optional, Callable, Tuple
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .backtest_engine import BacktestEngine, BacktestResult
from strategies.base_strategy import BaseStrategy


class SensitivityAnalyzer:
    """
    Analyzes how strategy performance changes with parameter variations.
    """
    
    def __init__(self, engine: Optional[BacktestEngine] = None):
        """
        Initialize sensitivity analyzer.
        
        Args:
            engine: BacktestEngine instance
        """
        self.engine = engine or BacktestEngine()
    
    def single_param_sweep(
        self,
        strategy_class: type,
        param_name: str,
        param_values: List[Any],
        market_data: pd.DataFrame,
        base_params: Optional[Dict[str, Any]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        frequency: str = 'M',
        base_investment: float = 1000,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> pd.DataFrame:
        """
        Test strategy with varying values for a single parameter.
        
        Args:
            strategy_class: Strategy class to instantiate
            param_name: Name of parameter to vary
            param_values: List of values to test
            market_data: Price data DataFrame
            base_params: Base parameters (param_name will be overridden)
            start_date: Start date for backtests
            end_date: End date for backtests
            frequency: Investment frequency
            base_investment: Base investment amount
            progress_callback: Optional callback for progress updates
            
        Returns:
            DataFrame with results for each parameter value
        """
        results = []
        total = len(param_values)
        
        for i, value in enumerate(param_values):
            # Create params with this value
            params = dict(base_params) if base_params else {}
            params[param_name] = value
            
            # Create strategy instance
            strategy = strategy_class(params=params)
            
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
                    param_name: value,
                    'total_return': result.metrics.total_return,
                    'cagr': result.metrics.cagr,
                    'max_drawdown': result.metrics.max_drawdown,
                    'sharpe_ratio': result.metrics.sharpe_ratio,
                    'sortino_ratio': result.metrics.sortino_ratio,
                })
            except Exception as e:
                results.append({
                    param_name: value,
                    'error': str(e)
                })
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        return pd.DataFrame(results)
    
    def dual_param_grid_search(
        self,
        strategy_class: type,
        param1_name: str,
        param1_values: List[Any],
        param2_name: str,
        param2_values: List[Any],
        market_data: pd.DataFrame,
        base_params: Optional[Dict[str, Any]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        frequency: str = 'M',
        base_investment: float = 1000,
        metric: str = 'sharpe_ratio',
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Grid search over two parameters simultaneously.
        
        Args:
            strategy_class: Strategy class to instantiate
            param1_name: Name of first parameter
            param1_values: Values for first parameter
            param2_name: Name of second parameter
            param2_values: Values for second parameter
            market_data: Price data DataFrame
            base_params: Base parameters
            start_date: Start date
            end_date: End date
            frequency: Investment frequency
            base_investment: Base investment amount
            metric: Metric to optimize ('sharpe_ratio', 'total_return', 'cagr')
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (results DataFrame, metric matrix for heatmap)
        """
        results = []
        total = len(param1_values) * len(param2_values)
        completed = 0
        
        # Initialize matrix for heatmap
        metric_matrix = np.zeros((len(param2_values), len(param1_values)))
        
        for i, v1 in enumerate(param1_values):
            for j, v2 in enumerate(param2_values):
                params = dict(base_params) if base_params else {}
                params[param1_name] = v1
                params[param2_name] = v2
                
                strategy = strategy_class(params=params)
                
                try:
                    result = self.engine.run_backtest(
                        strategy=strategy,
                        market_data=market_data,
                        start_date=start_date,
                        end_date=end_date,
                        frequency=frequency,
                        base_investment=base_investment
                    )
                    
                    metric_value = getattr(result.metrics, metric, 0)
                    if pd.isna(metric_value):
                        metric_value = 0
                    
                    results.append({
                        param1_name: v1,
                        param2_name: v2,
                        'total_return': result.metrics.total_return,
                        'cagr': result.metrics.cagr,
                        'max_drawdown': result.metrics.max_drawdown,
                        'sharpe_ratio': result.metrics.sharpe_ratio,
                    })
                    
                    metric_matrix[j, i] = metric_value
                    
                except:
                    metric_matrix[j, i] = np.nan
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
        
        return pd.DataFrame(results), metric_matrix
    
    @staticmethod
    def plot_single_param_sensitivity(
        results: pd.DataFrame,
        param_name: str,
        metrics: List[str] = None,
        height: int = 400
    ) -> go.Figure:
        """
        Create visualization for single parameter sensitivity.
        
        Args:
            results: Results from single_param_sweep
            param_name: Name of the varied parameter
            metrics: List of metrics to show (default: return, sharpe, drawdown)
            height: Chart height
            
        Returns:
            Plotly Figure
        """
        if metrics is None:
            metrics = ['total_return', 'sharpe_ratio', 'max_drawdown']
        
        fig = make_subplots(
            rows=1, cols=len(metrics),
            subplot_titles=[m.replace('_', ' ').title() for m in metrics]
        )
        
        colors = ['#2196F3', '#4CAF50', '#E91E63']
        
        for i, metric in enumerate(metrics):
            if metric in results.columns:
                fig.add_trace(
                    go.Scatter(
                        x=results[param_name],
                        y=results[metric],
                        mode='lines+markers',
                        name=metric.replace('_', ' ').title(),
                        line=dict(color=colors[i % len(colors)]),
                        marker=dict(size=8),
                    ),
                    row=1, col=i+1
                )
        
        # Find and mark optimal values
        if 'sharpe_ratio' in results.columns:
            best_idx = results['sharpe_ratio'].idxmax()
            if pd.notna(best_idx):
                best_value = results.loc[best_idx, param_name]
                for i in range(len(metrics)):
                    fig.add_vline(
                        x=best_value,
                        line=dict(color='red', dash='dash'),
                        row=1, col=i+1,
                        annotation_text=f'Best: {best_value}'
                    )
        
        fig.update_layout(
            title=f'參數敏感度分析: {param_name}',
            height=height,
            showlegend=False,
        )
        
        return fig
    
    @staticmethod
    def plot_dual_param_heatmap(
        metric_matrix: np.ndarray,
        param1_name: str,
        param1_values: List[Any],
        param2_name: str,
        param2_values: List[Any],
        metric_name: str = 'Sharpe Ratio',
        height: int = 500
    ) -> go.Figure:
        """
        Create heatmap for dual parameter grid search.
        
        Args:
            metric_matrix: 2D array of metric values
            param1_name: Name of first parameter (x-axis)
            param1_values: Values for first parameter
            param2_name: Name of second parameter (y-axis)
            param2_values: Values for second parameter
            metric_name: Name of the metric for display
            height: Chart height
            
        Returns:
            Plotly Figure
        """
        # Find best value
        best_idx = np.unravel_index(np.nanargmax(metric_matrix), metric_matrix.shape)
        best_p1 = param1_values[best_idx[1]]
        best_p2 = param2_values[best_idx[0]]
        best_val = metric_matrix[best_idx]
        
        fig = go.Figure(data=go.Heatmap(
            z=metric_matrix,
            x=[str(v) for v in param1_values],
            y=[str(v) for v in param2_values],
            colorscale='RdYlGn',
            text=[[f'{v:.2f}' if not np.isnan(v) else '' for v in row] for row in metric_matrix],
            texttemplate='%{text}',
            textfont=dict(size=10),
            hovertemplate=f'{param1_name}: %{{x}}<br>{param2_name}: %{{y}}<br>{metric_name}: %{{z:.2f}}<extra></extra>'
        ))
        
        # Add marker for best combination
        fig.add_annotation(
            x=str(best_p1),
            y=str(best_p2),
            text='★',
            showarrow=False,
            font=dict(size=20, color='black'),
        )
        
        fig.update_layout(
            title=f'參數組合熱力圖 ({metric_name})<br>最佳: {param1_name}={best_p1}, {param2_name}={best_p2} → {best_val:.2f}',
            xaxis_title=param1_name,
            yaxis_title=param2_name,
            height=height,
        )
        
        return fig
