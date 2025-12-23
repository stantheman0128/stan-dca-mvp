# core/visualizer.py
"""Visualization module for backtest results using Plotly."""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

from .backtest_engine import BacktestResult


class Visualizer:
    """
    Creates interactive Plotly charts for backtest analysis.
    
    All methods return Plotly Figure objects that can be displayed
    in Streamlit or saved as HTML/images.
    """
    
    # Color palette for strategies
    COLORS = [
        '#2196F3',  # Blue
        '#4CAF50',  # Green
        '#FF9800',  # Orange
        '#E91E63',  # Pink
        '#9C27B0',  # Purple
        '#00BCD4',  # Cyan
    ]
    
    # Financial events for annotations
    FINANCIAL_EVENTS = {
        '2008-09-15': '雷曼兄弟倒閉',
        '2008-10-10': '金融海嘯谷底', 
        '2011-08-05': '美債降級',
        '2015-08-24': '中國股災',
        '2016-06-23': '英國脫歐',
        '2020-03-23': '疫情恐慌谷底',
        '2022-02-24': '俄烏戰爭',
        '2022-06-16': 'Fed激進升息',
    }
    
    @classmethod
    def plot_equity_curves(
        cls,
        results: List[BacktestResult],
        show_cost: bool = True,
        show_events: bool = True,
        height: int = 500
    ) -> go.Figure:
        """
        Plot equity curves for multiple strategies.
        
        Args:
            results: List of BacktestResult objects
            show_cost: Whether to show cumulative cost line
            show_events: Whether to show financial event annotations
            height: Chart height in pixels
            
        Returns:
            Plotly Figure object
        """
        fig = go.Figure()
        
        for i, result in enumerate(results):
            color = cls.COLORS[i % len(cls.COLORS)]
            df = result.transactions
            
            # Strategy equity curve
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['current_value'],
                name=result.strategy_name,
                line=dict(color=color, width=2),
                hovertemplate=(
                    '<b>%{x|%Y-%m-%d}</b><br>' +
                    '市值: %{y:,.0f}<br>' +
                    '<extra></extra>'
                )
            ))
        
        # Add cumulative cost (from first result as reference)
        if show_cost and results:
            df = results[0].transactions
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['total_cost'],
                name='累積投入',
                line=dict(color='gray', width=2, dash='dash'),
                hovertemplate='累積投入: %{y:,.0f}<extra></extra>'
            ))
        
        # Add financial event annotations
        if show_events and results:
            start_date = results[0].transactions['date'].min()
            end_date = results[0].transactions['date'].max()
            y_max = max(r.transactions['current_value'].max() for r in results)
            
            for date_str, event_name in cls.FINANCIAL_EVENTS.items():
                event_date = pd.to_datetime(date_str)
                if start_date <= event_date <= end_date:
                    # Convert to string for Plotly compatibility
                    fig.add_shape(
                        type="line",
                        x0=date_str, x1=date_str,
                        y0=0, y1=1,
                        yref="paper",
                        line=dict(color='rgba(128,128,128,0.3)', width=1, dash='dot'),
                    )
                    fig.add_annotation(
                        x=date_str,
                        y=1,
                        yref="paper",
                        text=event_name,
                        showarrow=False,
                        font=dict(size=9),
                        textangle=-45,
                        yanchor='bottom'
                    )
        
        fig.update_layout(
            title='權益曲線對比',
            xaxis_title='日期',
            yaxis_title='市值',
            height=height,
            hovermode='x unified',
            legend=dict(yanchor='top', y=0.99, xanchor='left', x=0.01),
            xaxis=dict(rangeslider=dict(visible=True), type='date'),
        )
        
        return fig
    
    @classmethod
    def plot_returns(
        cls,
        results: List[BacktestResult],
        height: int = 400
    ) -> go.Figure:
        """
        Plot cumulative return percentage curves.
        
        Args:
            results: List of BacktestResult objects
            height: Chart height in pixels
            
        Returns:
            Plotly Figure object
        """
        fig = go.Figure()
        
        for i, result in enumerate(results):
            color = cls.COLORS[i % len(cls.COLORS)]
            df = result.transactions
            
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['return_pct'],
                name=result.strategy_name,
                line=dict(color=color, width=2),
                fill='tozeroy',
                hovertemplate='報酬率: %{y:.2f}%<extra></extra>'
            ))
        
        # Add zero line
        fig.add_hline(y=0, line=dict(color='black', width=1))
        
        fig.update_layout(
            title='累積報酬率曲線',
            xaxis_title='日期',
            yaxis_title='報酬率 (%)',
            height=height,
            hovermode='x unified',
            legend=dict(yanchor='top', y=0.99, xanchor='left', x=0.01),
        )
        
        return fig
    
    @classmethod
    def plot_drawdown(
        cls,
        results: List[BacktestResult],
        height: int = 350
    ) -> go.Figure:
        """
        Plot drawdown curves for each strategy.
        
        Args:
            results: List of BacktestResult objects  
            height: Chart height in pixels
            
        Returns:
            Plotly Figure object
        """
        fig = go.Figure()
        
        for i, result in enumerate(results):
            color = cls.COLORS[i % len(cls.COLORS)]
            df = result.transactions.copy()
            
            # Calculate drawdown
            df['peak'] = df['current_value'].expanding().max()
            df['drawdown'] = (df['current_value'] - df['peak']) / df['peak'] * 100
            
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['drawdown'],
                name=result.strategy_name,
                line=dict(color=color, width=2),
                fill='tozeroy',
                fillcolor=f'rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.2)',
                hovertemplate='回撤: %{y:.2f}%<extra></extra>'
            ))
        
        fig.update_layout(
            title='回撤曲線',
            xaxis_title='日期',
            yaxis_title='回撤 (%)',
            height=height,
            hovermode='x unified',
            legend=dict(yanchor='top', y=0.99, xanchor='left', x=0.01),
            yaxis=dict(range=[None, 5]),  # Show 0 at top
        )
        
        return fig
    
    @classmethod
    def plot_metrics_comparison(
        cls,
        results: List[BacktestResult],
        height: int = 400
    ) -> go.Figure:
        """
        Create horizontal bar chart comparing key metrics.
        
        Args:
            results: List of BacktestResult objects
            height: Chart height in pixels
            
        Returns:
            Plotly Figure object
        """
        if not results:
            return go.Figure()
        
        metrics_to_show = [
            ('total_return', '總報酬率 (%)'),
            ('cagr', '年化報酬率 (%)'),
            ('sharpe_ratio', '夏普比率'),
            ('max_drawdown', '最大回撤 (%)'),
        ]
        
        # Prepare data
        strategy_names = [r.strategy_name for r in results]
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=[m[1] for m in metrics_to_show],
            horizontal_spacing=0.15,
            vertical_spacing=0.2
        )
        
        for idx, (metric_key, metric_name) in enumerate(metrics_to_show):
            row = idx // 2 + 1
            col = idx % 2 + 1
            
            values = [getattr(r.metrics, metric_key) for r in results]
            colors = cls.COLORS[:len(results)]
            
            # For drawdown, make it positive for display but keep negative connotation
            display_values = values
            if metric_key == 'max_drawdown':
                display_values = [-v for v in values]  # Show as negative
            
            fig.add_trace(
                go.Bar(
                    x=display_values,
                    y=strategy_names,
                    orientation='h',
                    marker_color=colors,
                    text=[f'{v:.2f}' for v in values],
                    textposition='outside',
                    showlegend=False,
                ),
                row=row, col=col
            )
        
        fig.update_layout(
            title='績效指標對比',
            height=height,
            showlegend=False,
        )
        
        return fig
    
    @classmethod
    def plot_risk_return_scatter(
        cls,
        results: List[BacktestResult],
        height: int = 450
    ) -> go.Figure:
        """
        Create risk-return scatter plot.
        X-axis: Volatility (risk)
        Y-axis: CAGR (return)
        Size: Sharpe ratio
        
        Args:
            results: List of BacktestResult objects
            height: Chart height in pixels
            
        Returns:
            Plotly Figure object
        """
        if not results:
            return go.Figure()
        
        data = []
        for r in results:
            # Handle NaN values gracefully
            sharpe = r.metrics.sharpe_ratio
            if pd.isna(sharpe):
                sharpe = 0.0
            
            volatility = r.metrics.volatility
            if pd.isna(volatility):
                volatility = 0.0
                
            cagr = r.metrics.cagr
            if pd.isna(cagr):
                cagr = 0.0
            
            data.append({
                'Strategy': r.strategy_name,
                'Volatility': volatility,
                'CAGR': cagr,
                'Sharpe': max(sharpe, 0.1) if sharpe >= 0 else 0.1,  # Min size
                'Sharpe_display': sharpe,
            })
        
        df = pd.DataFrame(data)
        
        # Skip if all values are zero/invalid
        if df['Volatility'].sum() == 0:
            fig = go.Figure()
            fig.add_annotation(
                text="數據不足，無法繪製風險-報酬圖",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        fig = px.scatter(
            df,
            x='Volatility',
            y='CAGR',
            size='Sharpe',
            color='Strategy',
            text='Strategy',
            color_discrete_sequence=cls.COLORS,
            size_max=40,
        )
        
        fig.update_traces(
            textposition='top center',
            hovertemplate=(
                '<b>%{text}</b><br>' +
                '波動率: %{x:.2f}%<br>' +
                '年化報酬: %{y:.2f}%<br>' +
                '<extra></extra>'
            )
        )
        
        # Add quadrant guide (ideal is upper-left: low risk, high return)
        if len(df) > 0:
            mid_vol = df['Volatility'].median()
            mid_ret = df['CAGR'].median()
            
            fig.add_hline(y=mid_ret, line=dict(color='gray', dash='dash', width=1))
            fig.add_vline(x=mid_vol, line=dict(color='gray', dash='dash', width=1))
            
            # Label quadrants
            fig.add_annotation(
                x=df['Volatility'].min(),
                y=df['CAGR'].max(),
                text='★ 理想區域',
                showarrow=False,
                font=dict(size=10, color='green'),
                xanchor='left',
                yanchor='top'
            )
        
        fig.update_layout(
            title='風險-報酬散點圖',
            xaxis_title='年化波動率 (%)',
            yaxis_title='年化報酬率 (%)',
            height=height,
            showlegend=True,
            legend=dict(yanchor='bottom', y=0.01, xanchor='right', x=0.99),
        )
        
        return fig
    
    @classmethod
    def plot_annual_returns_heatmap(
        cls,
        results: List[BacktestResult],
        height: int = 350
    ) -> go.Figure:
        """
        Create heatmap of annual returns by strategy.
        
        Args:
            results: List of BacktestResult objects
            height: Chart height in pixels
            
        Returns:
            Plotly Figure object
        """
        if not results:
            return go.Figure()
        
        # Collect annual returns from all strategies
        all_years = set()
        for r in results:
            all_years.update(r.metrics.annual_returns.keys())
        
        if not all_years:
            return go.Figure()
        
        years = sorted(all_years)
        strategy_names = [r.strategy_name for r in results]
        
        # Build matrix
        z = []
        for r in results:
            row = [r.metrics.annual_returns.get(y, None) for y in years]
            z.append(row)
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=z,
            x=[str(y) for y in years],
            y=strategy_names,
            colorscale='RdYlGn',
            zmid=0,
            text=[[f'{v:.1f}%' if v else '' for v in row] for row in z],
            texttemplate='%{text}',
            textfont=dict(size=10),
            hovertemplate='%{y}<br>%{x}: %{z:.2f}%<extra></extra>'
        ))
        
        fig.update_layout(
            title='年度報酬率熱力圖',
            xaxis_title='年度',
            yaxis_title='策略',
            height=height,
        )
        
        return fig
    
    @classmethod
    def plot_monthly_investment_chart(
        cls,
        result: BacktestResult,
        height: int = 350
    ) -> go.Figure:
        """
        Plot monthly investment amounts showing multiplier effects.
        
        Args:
            result: Single BacktestResult object
            height: Chart height in pixels
            
        Returns:
            Plotly Figure object
        """
        df = result.transactions.copy()
        
        # Color based on multiplier
        colors = ['green' if m > 1 else 'blue' for m in df['multiplier']]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=df['date'],
            y=df['investment'],
            marker_color=colors,
            name='投入金額',
            hovertemplate=(
                '日期: %{x|%Y-%m-%d}<br>' +
                '投入: %{y:,.0f}<br>' +
                '<extra></extra>'
            )
        ))
        
        # Add base investment reference line
        fig.add_hline(
            y=result.base_investment,
            line=dict(color='gray', dash='dash'),
            annotation_text=f'基準投入 ({result.base_investment:,.0f})',
            annotation_position='right'
        )
        
        fig.update_layout(
            title=f'{result.strategy_name} - 每期投入金額',
            xaxis_title='日期',
            yaxis_title='投入金額',
            height=height,
        )
        
        return fig
