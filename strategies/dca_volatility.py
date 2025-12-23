# strategies/dca_volatility.py
"""V3: Volatility Adjustment Strategy - Adjust investment based on market volatility."""

from typing import Dict, Any, List
import pandas as pd
import numpy as np

from .base_strategy import BaseStrategy, InvestmentDecision


class DCAVolatilityStrategy(BaseStrategy):
    """
    V3: Volatility Adjustment Strategy
    
    Adjusts investment amount based on market volatility levels.
    Increases investment during high volatility (market panic = opportunity)
    and decreases during low volatility periods.
    
    Logic:
    - Calculate rolling volatility (standard deviation of returns)
    - Compare to historical average volatility
    - High volatility: increase investment
    - Low volatility: decrease investment
    """
    
    @property
    def name(self) -> str:
        return "波動率調整 (Volatility Adjustment)"
    
    @property
    def short_name(self) -> str:
        return "V3"
    
    @property
    def description(self) -> str:
        return "根據市場波動率調整投入。高波動（恐慌）時加碼，低波動時減碼。"
    
    @property
    def default_params(self) -> Dict[str, Any]:
        return {
            'volatility_window': 20,       # Days for current volatility
            'lookback_period': 252,        # Days for historical average
            'high_vol_threshold': 1.5,     # Multiplier of average
            'low_vol_threshold': 0.8,      # Multiplier of average
            'high_vol_multiplier': 1.5,    # Investment multiplier
            'low_vol_multiplier': 0.8,     # Investment multiplier
        }
    
    def _calculate_volatility(self, prices: pd.Series, window: int) -> pd.Series:
        """
        Calculate rolling annualized volatility.
        
        Args:
            prices: Price series
            window: Rolling window size
            
        Returns:
            Rolling volatility series
        """
        # Calculate daily returns
        returns = prices.pct_change().dropna()
        
        # Calculate rolling std and annualize
        rolling_vol = returns.rolling(window=window).std() * np.sqrt(252)
        
        return rolling_vol
    
    def calculate_investment(
        self,
        current_price: float,
        current_date: pd.Timestamp,
        historical_data: pd.DataFrame,
        portfolio_state: Dict[str, float]
    ) -> InvestmentDecision:
        """
        Calculate investment multiplier based on volatility level.
        
        Args:
            current_price: Current period's price
            current_date: Current period's date
            historical_data: Historical price data
            portfolio_state: Current portfolio state
            
        Returns:
            InvestmentDecision with multiplier based on volatility
        """
        vol_window = self.params['volatility_window']
        lookback = self.params['lookback_period']
        high_thresh = self.params['high_vol_threshold']
        low_thresh = self.params['low_vol_threshold']
        high_mult = self.params['high_vol_multiplier']
        low_mult = self.params['low_vol_multiplier']
        
        # Get prices
        if 'Close' in historical_data.columns:
            prices = historical_data['Close']
        else:
            prices = historical_data.iloc[:, 0]
        
        # Filter to dates up to current
        mask = prices.index <= current_date
        relevant_prices = prices[mask]
        
        # Check minimum data requirement
        min_required = max(vol_window, lookback) + 1
        if len(relevant_prices) < min_required:
            return InvestmentDecision(
                investment_multiplier=1.0,
                reason=f"數據不足 ({len(relevant_prices)}/{min_required})，正常投入"
            )
        
        # Calculate volatility series
        volatility = self._calculate_volatility(relevant_prices, vol_window)
        
        # Get current and historical average volatility
        current_vol = volatility.iloc[-1]
        
        # Use lookback period for historical average
        lookback_vol = volatility.tail(lookback)
        avg_vol = lookback_vol.mean()
        
        if pd.isna(current_vol) or pd.isna(avg_vol) or avg_vol == 0:
            return InvestmentDecision(
                investment_multiplier=1.0,
                reason="波動率計算失敗，正常投入"
            )
        
        # Compare current to average
        vol_ratio = current_vol / avg_vol
        
        if vol_ratio >= high_thresh:
            return InvestmentDecision(
                investment_multiplier=high_mult,
                reason=f"高波動 ({current_vol:.1%} = {vol_ratio:.1f}x 平均)，加碼 {high_mult}x"
            )
        elif vol_ratio <= low_thresh:
            return InvestmentDecision(
                investment_multiplier=low_mult,
                reason=f"低波動 ({current_vol:.1%} = {vol_ratio:.1f}x 平均)，減碼 {low_mult}x"
            )
        else:
            return InvestmentDecision(
                investment_multiplier=1.0,
                reason=f"正常波動 ({current_vol:.1%} = {vol_ratio:.1f}x 平均)，正常投入"
            )
    
    def get_param_info(self) -> List[Dict[str, Any]]:
        """Return parameter information for UI display."""
        return [
            {
                'name': 'volatility_window',
                'label': '波動率計算窗口（交易日）',
                'type': 'int',
                'default': 20,
                'min': 5,
                'max': 60,
                'step': 5,
                'description': '計算當前波動率的天數'
            },
            {
                'name': 'lookback_period',
                'label': '歷史平均回顧期間',
                'type': 'int',
                'default': 252,
                'min': 60,
                'max': 504,
                'step': 21,
                'description': '計算歷史平均波動率的天數'
            },
            {
                'name': 'high_vol_threshold',
                'label': '高波動閾值（倍數）',
                'type': 'float',
                'default': 1.5,
                'min': 1.1,
                'max': 3.0,
                'step': 0.1,
                'description': '當前波動率超過平均的倍數'
            },
            {
                'name': 'low_vol_threshold',
                'label': '低波動閾值（倍數）',
                'type': 'float',
                'default': 0.8,
                'min': 0.3,
                'max': 0.95,
                'step': 0.05,
                'description': '當前波動率低於平均的倍數'
            },
            {
                'name': 'high_vol_multiplier',
                'label': '高波動加碼倍數',
                'type': 'float',
                'default': 1.5,
                'min': 1.0,
                'max': 3.0,
                'step': 0.1,
                'description': '高波動時的投入倍數'
            },
            {
                'name': 'low_vol_multiplier',
                'label': '低波動減碼倍數',
                'type': 'float',
                'default': 0.8,
                'min': 0.3,
                'max': 1.0,
                'step': 0.1,
                'description': '低波動時的投入倍數'
            },
        ]
