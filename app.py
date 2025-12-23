# app.py
"""
DCA Backtest Tool - Main Streamlit Application
定期定額策略回測工具
"""

import streamlit as st
from datetime import date, datetime
from typing import List, Dict, Any
import pandas as pd
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.data_loader import DataLoader
from core.backtest_engine import BacktestEngine, BacktestResult
from core.visualizer import Visualizer
from core.statistics import StatisticalAnalyzer
from core.robustness import RobustnessAnalyzer
from core.sensitivity import SensitivityAnalyzer
from strategies import (
    DCAPureStrategy,
    DCADipBuyingStrategy,
    DCATrendFilterStrategy,
    DCAVolatilityStrategy,
    DCAProfitTakingStrategy,
)
from utils.report_generator import ReportGenerator
import plotly.graph_objects as go
import plotly.express as px

# ================== Page Configuration ==================

st.set_page_config(
    page_title="DCA 策略回測工具",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: "Noto Sans TC", "Microsoft JhengHei", sans-serif;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .metric-card-positive {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    }
    
    .metric-card-negative {
        background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
    }
    
    .metric-label {
        font-size: 0.85rem;
        opacity: 0.9;
        margin-bottom: 0.3rem;
    }
    
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 8px;
        padding: 8px 16px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #2196F3;
        color: white;
    }
</style>
""", unsafe_allow_html=True)


# ================== Helper Functions ==================

def render_metric_card(label: str, value: str, card_type: str = "default"):
    """Render a styled metric card."""
    css_class = "metric-card"
    if card_type == "positive":
        css_class += " metric-card-positive"
    elif card_type == "negative":
        css_class += " metric-card-negative"
    
    st.markdown(f"""
    <div class="{css_class}">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)


def get_available_strategies():
    """Get all available strategy classes."""
    return {
        'V0: 純定期定額': DCAPureStrategy,
        'V1: 跌深加碼': DCADipBuyingStrategy,
        'V2: 趨勢過濾': DCATrendFilterStrategy,
        'V3: 波動率調整': DCAVolatilityStrategy,
        'V5: 定期減碼': DCAProfitTakingStrategy,
    }


def get_market_options():
    """Get market selection options."""
    return {
        'SPY - S&P 500 (美股)': 'SPY',
        'QQQ - Nasdaq 100 (美股)': 'QQQ',
        'DIA - Dow Jones (美股)': 'DIA',
        'IWM - Russell 2000 (美股)': 'IWM',
        '0050.TW - 元大台灣50': '0050.TW',
        '0056.TW - 元大高股息': '0056.TW',
        '^TWII - 台灣加權指數': '^TWII',
        '^N225 - 日經225 (日本)': '^N225',
        '^FTSE - 富時100 (英國)': '^FTSE',
        '^GDAXI - DAX (德國)': '^GDAXI',
    }


# ================== Sidebar Configuration ==================

def render_sidebar():
    """Render sidebar with configuration options."""
    st.sidebar.title("📊 回測設定")
    
    # Market Selection
    st.sidebar.subheader("🌍 市場選擇")
    markets = get_market_options()
    selected_market = st.sidebar.selectbox(
        "選擇標的",
        options=list(markets.keys()),
        index=0
    )
    symbol = markets[selected_market]
    
    # Currency detection
    currency = "TWD" if "TW" in symbol or "TWII" in symbol else "USD"
    
    # Date Range
    st.sidebar.subheader("📅 時間範圍")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input(
            "開始日期",
            value=date(2015, 1, 1),
            min_value=date(2005, 1, 1),
            max_value=date.today()
        )
    with col2:
        end_date = st.date_input(
            "結束日期",
            value=date.today(),
            min_value=date(2005, 1, 1),
            max_value=date.today()
        )
    
    # Investment Parameters
    st.sidebar.subheader("💰 投資參數")
    frequency = st.sidebar.selectbox(
        "投入頻率",
        options=['每月 (M)', '每週 (W)', '每季 (Q)'],
        index=0
    )
    freq_map = {'每月 (M)': 'M', '每週 (W)': 'W', '每季 (Q)': 'Q'}
    freq = freq_map[frequency]
    
    investment = st.sidebar.number_input(
        f"每期投入金額 ({currency})",
        min_value=100,
        max_value=100000,
        value=10000 if currency == "TWD" else 1000,
        step=100
    )
    
    # Strategy Selection
    st.sidebar.subheader("📈 策略選擇")
    available_strategies = get_available_strategies()
    selected_strategy_names = st.sidebar.multiselect(
        "選擇要測試的策略",
        options=list(available_strategies.keys()),
        default=['V0: 純定期定額', 'V1: 跌深加碼']
    )
    
    # Strategy Parameters (expandable)
    strategy_params = {}
    if selected_strategy_names:
        with st.sidebar.expander("⚙️ 策略參數調整", expanded=False):
            for name in selected_strategy_names:
                strategy_class = available_strategies[name]
                strategy = strategy_class()
                param_info = strategy.get_param_info()
                
                if param_info:
                    st.markdown(f"**{name}**")
                    strategy_params[name] = {}
                    
                    for param in param_info:
                        key = f"{name}_{param['name']}"
                        
                        if param['type'] == 'int':
                            value = st.slider(
                                param['label'],
                                min_value=param.get('min', 1),
                                max_value=param.get('max', 1000),
                                value=param['default'],
                                step=param.get('step', 1),
                                key=key
                            )
                        elif param['type'] == 'float':
                            value = st.slider(
                                param['label'],
                                min_value=float(param.get('min', 0)),
                                max_value=float(param.get('max', 10)),
                                value=float(param['default']),
                                step=float(param.get('step', 0.1)),
                                key=key
                            )
                        elif param['type'] == 'select':
                            value = st.selectbox(
                                param['label'],
                                options=param['options'],
                                index=param['options'].index(param['default']),
                                key=key
                            )
                        else:
                            value = param['default']
                        
                        strategy_params[name][param['name']] = value
                    
                    st.markdown("---")
    
    return {
        'symbol': symbol,
        'selected_market': selected_market,
        'currency': currency,
        'start_date': start_date,
        'end_date': end_date,
        'frequency': freq,
        'investment': investment,
        'selected_strategies': selected_strategy_names,
        'strategy_params': strategy_params,
    }


# ================== Main Content ==================

def run_backtests(config: Dict[str, Any]) -> List[BacktestResult]:
    """Run backtests for selected strategies."""
    results = []
    available_strategies = get_available_strategies()
    
    # Initialize components
    data_loader = DataLoader()
    engine = BacktestEngine()
    
    # Download data
    with st.spinner(f"正在下載 {config['symbol']} 數據..."):
        data = data_loader.download_data(
            config['symbol'],
            start_date=str(config['start_date']),
            end_date=str(config['end_date'])
        )
    
    if data is None or data.empty:
        st.error("❌ 數據下載失敗，請檢查網路連線或更換標的")
        return []
    
    st.success(f"✅ 成功下載 {len(data)} 筆數據")
    
    # Run backtest for each strategy
    progress_bar = st.progress(0)
    n_strategies = len(config['selected_strategies'])
    
    for i, strategy_name in enumerate(config['selected_strategies']):
        strategy_class = available_strategies[strategy_name]
        
        # Get custom params if any
        custom_params = config['strategy_params'].get(strategy_name, {})
        strategy = strategy_class(params=custom_params if custom_params else None)
        
        try:
            result = engine.run_backtest(
                strategy=strategy,
                market_data=data,
                frequency=config['frequency'],
                base_investment=config['investment'],
                symbol=config['symbol']
            )
            results.append(result)
        except Exception as e:
            st.warning(f"⚠️ {strategy_name} 回測失敗: {str(e)}")
        
        progress_bar.progress((i + 1) / n_strategies)
    
    return results


def display_results(results: List[BacktestResult], currency: str):
    """Display backtest results."""
    if not results:
        st.info("請選擇策略並點擊「開始回測」")
        return
    
    # Key Metrics Cards
    st.subheader("📊 關鍵指標")
    
    # Find best performers
    best_sharpe = max(results, key=lambda r: r.metrics.sharpe_ratio)
    best_return = max(results, key=lambda r: r.metrics.total_return)
    
    cols = st.columns(len(results))
    for i, (col, result) in enumerate(zip(cols, results)):
        m = result.metrics
        card_type = "positive" if m.total_return > 0 else "negative"
        
        with col:
            st.markdown(f"**{result.strategy_name}**")
            render_metric_card(
                "總報酬率",
                f"{'+' if m.total_return >= 0 else ''}{m.total_return:.1f}%",
                card_type
            )
            st.metric("年化報酬率", f"{m.cagr:.2f}%")
            st.metric("夏普比率", f"{m.sharpe_ratio:.2f}")
            st.metric("最大回撤", f"{m.max_drawdown:.1f}%")
            st.metric("總投入", f"{currency} {m.total_invested:,.0f}")
            st.metric("最終市值", f"{currency} {m.final_value:,.0f}")
    
    # Charts in tabs
    st.subheader("📈 視覺化分析")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "權益曲線", "報酬率", "回撤分析", "指標對比", "風險-報酬"
    ])
    
    with tab1:
        fig = Visualizer.plot_equity_curves(results, show_events=True)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        fig = Visualizer.plot_returns(results)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        fig = Visualizer.plot_drawdown(results)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        fig = Visualizer.plot_metrics_comparison(results)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab5:
        fig = Visualizer.plot_risk_return_scatter(results)
        st.plotly_chart(fig, use_container_width=True)
    
    # Comparison Table
    st.subheader("📋 詳細指標對比")
    engine = BacktestEngine()
    comparison_df = engine.compare_strategies(results)
    st.dataframe(comparison_df, use_container_width=True)
    
    # Statistical Tests
    if len(results) >= 2:
        st.subheader("🔬 統計檢驗")
        
        with st.expander("策略差異顯著性檢驗", expanded=False):
            returns_dict = {
                r.strategy_name: r.transactions['return_pct'].pct_change().dropna()
                for r in results
            }
            
            comparison_results = StatisticalAnalyzer.multi_strategy_comparison(returns_dict)
            st.dataframe(comparison_results, use_container_width=True)
    
    # Export Options
    st.subheader("📥 導出報告")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 導出 Excel", use_container_width=True):
            try:
                excel_data = ReportGenerator.export_to_excel(results, comparison_df)
                st.download_button(
                    label="下載 Excel 文件",
                    data=excel_data,
                    file_name=f"dca_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Excel 導出失敗: {str(e)}")
    
    with col2:
        if st.button("📄 導出 PDF", use_container_width=True):
            try:
                pdf_data = ReportGenerator.generate_pdf_report(results)
                st.download_button(
                    label="下載 PDF 報告",
                    data=pdf_data,
                    file_name=f"dca_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"PDF 導出失敗: {str(e)}")
    
    with col3:
        if st.button("📝 導出 CSV", use_container_width=True):
            csv_data = results[0].transactions.to_csv(index=False)
            st.download_button(
                label="下載交易記錄",
                data=csv_data,
                file_name=f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )


# ================== P2 Features ==================

def render_robustness_tests(config: Dict[str, Any]):
    """Render robustness testing section."""
    st.header("🔬 穩健性測試")
    
    available_strategies = get_available_strategies()
    
    # Strategy selection for robustness test
    strategy_name = st.selectbox(
        "選擇要測試的策略",
        options=list(available_strategies.keys()),
        key="robustness_strategy"
    )
    
    strategy_class = available_strategies[strategy_name]
    strategy = strategy_class()
    
    # Test type selection
    test_type = st.radio(
        "測試類型",
        options=["固定起始點測試", "Monte Carlo 模擬", "滾動窗口分析"],
        horizontal=True,
        key="robustness_test_type"
    )
    
    # Show relevant settings BEFORE the button
    if test_type == "Monte Carlo 模擬":
        num_sims = st.slider("模擬次數", 50, 500, 200, step=50, key="mc_num_sims")
        min_years = st.slider("最小投資年數", 1, 10, 3, key="mc_min_years")
        max_years = st.slider("最大投資年數", 5, 20, 15, key="mc_max_years")
    elif test_type == "滾動窗口分析":
        window_years = st.slider("窗口大小 (年)", 1, 10, 3, key="rolling_window_years")
    
    data_loader = DataLoader()
    
    if st.button("🔬 執行穩健性測試", type="primary", key="run_robustness"):
        with st.spinner("正在下載數據..."):
            data = data_loader.download_data(
                config['symbol'],
                start_date="2005-01-01",
                end_date=str(date.today())
            )
        
        if data is None or data.empty:
            st.error("數據下載失敗")
            return
        
        analyzer = RobustnessAnalyzer()
        
        if test_type == "固定起始點測試":
            st.info("使用預設的 6 個起始時間點進行測試...")
            progress = st.progress(0)
            
            def update_progress(current, total):
                progress.progress(current / total)
            
            results_df = analyzer.test_fixed_start_points(
                strategy=strategy,
                market_data=data,
                frequency=config['frequency'],
                base_investment=config['investment'],
                progress_callback=update_progress
            )
            
            st.subheader("📊 不同起始點測試結果")
            st.dataframe(results_df, use_container_width=True)
            
            # Chart
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=results_df['start_date'],
                y=results_df['total_return'],
                marker_color=['green' if r > 0 else 'red' for r in results_df['total_return']],
                text=[f"{r:.1f}%" for r in results_df['total_return']],
                textposition='outside'
            ))
            fig.update_layout(
                title="不同起始點的總報酬率",
                xaxis_title="起始日期",
                yaxis_title="總報酬率 (%)",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
            
        elif test_type == "Monte Carlo 模擬":
            # Use the slider values from session state
            num_sims_val = st.session_state.get('mc_num_sims', 200)
            min_years_val = st.session_state.get('mc_min_years', 3)
            max_years_val = st.session_state.get('mc_max_years', 15)
            
            st.info(f"執行 {num_sims_val} 次隨機起始點模擬...")
            progress = st.progress(0)
            
            def update_progress(current, total):
                progress.progress(current / total)
            
            stats = analyzer.monte_carlo_simulation(
                strategy=strategy,
                market_data=data,
                num_simulations=num_sims_val,
                min_duration_years=min_years_val,
                max_duration_years=max_years_val,
                frequency=config['frequency'],
                base_investment=config['investment'],
                num_workers=4,
                progress_callback=update_progress
            )
            
            if 'error' not in stats:
                st.subheader("📊 Monte Carlo 模擬結果")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("平均報酬率", f"{stats['returns']['mean']:.1f}%")
                with col2:
                    st.metric("中位數報酬", f"{stats['returns']['median']:.1f}%")
                with col3:
                    st.metric("勝率", f"{stats['win_rate']:.1f}%")
                with col4:
                    st.metric("平均最大回撤", f"{stats['max_drawdown']['mean']:.1f}%")
                
                st.write(f"**95% 信心區間**: {stats['returns']['percentile_5']:.1f}% ~ {stats['returns']['percentile_95']:.1f}%")
                
                # Distribution chart
                raw_df = stats['raw_results']
                fig = px.histogram(
                    raw_df, x='total_return',
                    nbins=30,
                    title="報酬率分佈",
                    labels={'total_return': '總報酬率 (%)'}
                )
                fig.add_vline(x=0, line_dash="dash", line_color="red")
                fig.add_vline(x=stats['returns']['mean'], line_dash="dash", line_color="green",
                             annotation_text=f"平均: {stats['returns']['mean']:.1f}%")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("模擬失敗")
                
        elif test_type == "滾動窗口分析":
            window_years_val = st.session_state.get('rolling_window_years', 3)
            
            st.info(f"使用 {window_years_val} 年滾動窗口分析...")
            progress = st.progress(0)
            
            def update_progress(current, total):
                progress.progress(current / total)
            
            results_df = analyzer.rolling_window_analysis(
                strategy=strategy,
                market_data=data,
                window_years=window_years_val,
                step_months=3,
                frequency=config['frequency'],
                base_investment=config['investment'],
                progress_callback=update_progress
            )
            
            st.subheader("📊 滾動窗口分析結果")
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=pd.to_datetime(results_df['window_start']),
                y=results_df['total_return'],
                mode='lines',
                name='總報酬率',
                fill='tozeroy'
            ))
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            fig.update_layout(
                title=f"{window_years_val} 年滾動窗口報酬率",
                xaxis_title="窗口起始日期",
                yaxis_title="報酬率 (%)",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.write(f"**統計摘要**: 平均報酬率 {results_df['total_return'].mean():.1f}%, "
                    f"標準差 {results_df['total_return'].std():.1f}%, "
                    f"最佳 {results_df['total_return'].max():.1f}%, "
                    f"最差 {results_df['total_return'].min():.1f}%")


def render_sensitivity_analysis(config: Dict[str, Any]):
    """Render parameter sensitivity analysis section."""
    st.header("📈 參數敏感度分析")
    
    available_strategies = get_available_strategies()
    
    # Only strategies with parameters
    param_strategies = {k: v for k, v in available_strategies.items() 
                       if v().get_param_info()}
    
    if not param_strategies:
        st.info("沒有可調整參數的策略")
        return
    
    strategy_name = st.selectbox(
        "選擇策略",
        options=list(param_strategies.keys()),
        key="sensitivity_strategy"
    )
    
    strategy_class = param_strategies[strategy_name]
    strategy = strategy_class()
    param_info = strategy.get_param_info()
    
    # Parameter selection
    param_options = [p['name'] for p in param_info]
    param_labels = {p['name']: p['label'] for p in param_info}
    
    selected_param = st.selectbox(
        "選擇要分析的參數",
        options=param_options,
        format_func=lambda x: param_labels[x]
    )
    
    # Get param details
    param_detail = next(p for p in param_info if p['name'] == selected_param)
    
    # Value range
    col1, col2, col3 = st.columns(3)
    with col1:
        min_val = st.number_input("最小值", value=float(param_detail.get('min', 0)))
    with col2:
        max_val = st.number_input("最大值", value=float(param_detail.get('max', 10)))
    with col3:
        steps = st.number_input("測試點數", value=10, min_value=3, max_value=20)
    
    if st.button("📈 執行敏感度分析", type="primary"):
        data_loader = DataLoader()
        
        with st.spinner("正在下載數據..."):
            data = data_loader.download_data(
                config['symbol'],
                start_date=str(config['start_date']),
                end_date=str(config['end_date'])
            )
        
        if data is None:
            st.error("數據下載失敗")
            return
        
        # Generate test values
        if param_detail['type'] == 'int':
            test_values = [int(v) for v in range(int(min_val), int(max_val) + 1, 
                                                 max(1, int((max_val - min_val) / steps)))]
        else:
            import numpy as np
            test_values = list(np.linspace(min_val, max_val, int(steps)))
        
        analyzer = SensitivityAnalyzer()
        progress = st.progress(0)
        
        def update_progress(current, total):
            progress.progress(current / total)
        
        results_df = analyzer.single_param_sweep(
            strategy_class=strategy_class,
            param_name=selected_param,
            param_values=test_values,
            market_data=data,
            frequency=config['frequency'],
            base_investment=config['investment'],
            progress_callback=update_progress
        )
        
        st.subheader("📊 敏感度分析結果")
        
        # Find optimal
        if 'sharpe_ratio' in results_df.columns:
            best_idx = results_df['sharpe_ratio'].idxmax()
            if pd.notna(best_idx):
                best_value = results_df.loc[best_idx, selected_param]
                st.success(f"✨ 最佳 {param_labels[selected_param]}: **{best_value}** (夏普比率最高)")
        
        # Charts
        fig = SensitivityAnalyzer.plot_single_param_sensitivity(
            results_df, selected_param,
            metrics=['total_return', 'sharpe_ratio', 'max_drawdown']
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(results_df, use_container_width=True)


# ================== Main App ==================

def main():
    """Main application entry point."""
    # Title
    st.title("📈 DCA 策略回測工具")
    st.caption("定期定額投資策略回測與分析平台")
    
    # Sidebar configuration
    config = render_sidebar()
    
    # Store config in session state for other tabs
    st.session_state['config'] = config
    
    # Main tabs
    tab_main, tab_robustness, tab_sensitivity = st.tabs([
        "🎯 基本回測", "🔬 穩健性測試", "📈 參數敏感度"
    ])
    
    with tab_main:
        # Info display
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"📍 標的: **{config['selected_market']}**")
        with col2:
            st.info(f"📅 期間: **{config['start_date']} ~ {config['end_date']}**")
        with col3:
            st.info(f"💰 每期投入: **{config['currency']} {config['investment']:,}**")
        
        # Run button
        st.markdown("---")
        
        if st.button("🚀 開始回測", type="primary", use_container_width=True):
            if not config['selected_strategies']:
                st.warning("⚠️ 請至少選擇一個策略")
            else:
                # Store results in session state
                results = run_backtests(config)
                st.session_state['results'] = results
                st.session_state['currency'] = config['currency']
        
        # Display results
        if 'results' in st.session_state and st.session_state['results']:
            display_results(
                st.session_state['results'],
                st.session_state.get('currency', 'USD')
            )
    
    with tab_robustness:
        render_robustness_tests(config)
    
    with tab_sensitivity:
        render_sensitivity_analysis(config)
    
    # Footer
    st.markdown("---")
    st.caption("⚠️ 此工具僅供研究參考，歷史績效不代表未來表現。數據來源：Yahoo Finance")


if __name__ == "__main__":
    main()

