# strategies/dca_trend_filter.py
"""V2: Trend Filter Strategy - Adjust investment based on moving average."""

from typing import Dict, Any, List
import pandas as pd
import numpy as np

from .base_strategy import BaseStrategy, InvestmentDecision


class DCATrendFilterStrategy(BaseStrategy):
    """
    V2: Trend Filter Strategy
    
    Adjusts investment amount based on the price's position relative
    to a long-term moving average. Invests more when price is below
    the MA (considered undervalued) and normal amount when above.
    
    Logic:
    - Calculate moving average (SMA or EMA)
    - If price < MA: increase investment (buy low)
    - If price >= MA: normal investment
    """
    
    @property
    def name(self) -> str:
        return "趨勢過濾 (Trend Filter)"
    
    @property
    def short_name(self) -> str:
        return "V2"
    
    @property
    def description(self) -> str:
        return "根據價格與長期移動平均線的關係調整投入。價格低於均線時加碼買入。"
    
    @property
    def default_params(self) -> Dict[str, Any]:
        return {
            'ma_period': 200,           # Moving average period
            'ma_type': 'SMA',           # 'SMA' or 'EMA'
            'above_multiplier': 1.0,    # When price > MA
            'below_multiplier': 1.5,    # When price < MA
        }
    
    def _calculate_ma(self, prices: pd.Series, period: int, ma_type: str) -> pd.Series:
        """
        Calculate moving average.
        
        Args:
            prices: Price series
            period: MA period
            ma_type: 'SMA' or 'EMA'
            
        Returns:
            Moving average series
        """
        if ma_type.upper() == 'EMA':
            return prices.ewm(span=period, adjust=False).mean()
        else:  # Default to SMA
            return prices.rolling(window=period, min_periods=1).mean()
    
    def calculate_investment(
        self,
        current_price: float,
        current_date: pd.Timestamp,
        historical_data: pd.DataFrame,
        portfolio_state: Dict[str, float]
    ) -> InvestmentDecision:
        """
        Calculate investment multiplier based on price vs MA.
        
        Args:
            current_price: Current period's price
            current_date: Current period's date
            historical_data: Historical price data (with 'Close' column)
            portfolio_state: Current portfolio state
            
        Returns:
            InvestmentDecision with multiplier based on trend
        """
        ma_period = self.params['ma_period']
        ma_type = self.params['ma_type']
        above_mult = self.params['above_multiplier']
        below_mult = self.params['below_multiplier']
        
        # Get historical prices
        if 'Close' in historical_data.columns:
            prices = historical_data['Close']
        else:
            prices = historical_data.iloc[:, 0]
        
        # Filter to dates before or equal to current date
        mask = prices.index <= current_date
        relevant_prices = prices[mask]
        
        # Check if we have enough data for MA
        if len(relevant_prices) < ma_period:
            return InvestmentDecision(
                investment_multiplier=1.0,
                reason=f"數據不足 ({len(relevant_prices)}/{ma_period} 天)，正常投入"
            )
        
        # Calculate moving average
        ma = self._calculate_ma(relevant_prices, ma_period, ma_type)
        current_ma = ma.iloc[-1]
        
        # Compare price to MA
        if current_price < current_ma:
            pct_below = (current_ma - current_price) / current_ma * 100
            return InvestmentDecision(
                investment_multiplier=below_mult,
                reason=f"價格低於 {ma_type}{ma_period} {pct_below:.1f}%，加碼 {below_mult}x"
            )
        else:
            pct_above = (current_price - current_ma) / current_ma * 100
            return InvestmentDecision(
                investment_multiplier=above_mult,
                reason=f"價格高於 {ma_type}{ma_period} {pct_above:.1f}%，正常投入"
            )
    
    def get_param_info(self) -> List[Dict[str, Any]]:
        """Return parameter information for UI display."""
        return [
            {
                'name': 'ma_period',
                'label': '均線週期',
                'type': 'int',
                'default': 200,
                'min': 20,
                'max': 400,
                'step': 10,
                'description': '移動平均線計算天數'
            },
            {
                'name': 'ma_type',
                'label': '均線類型',
                'type': 'select',
                'default': 'SMA',
                'options': ['SMA', 'EMA'],
                'description': 'SMA=簡單移動平均，EMA=指數移動平均'
            },
            {
                'name': 'above_multiplier',
                'label': '價格高於均線時倍數',
                'type': 'float',
                'default': 1.0,
                'min': 0.5,
                'max': 2.0,
                'step': 0.1,
                'description': '價格在均線上方時的投入倍數'
            },
            {
                'name': 'below_multiplier',
                'label': '價格低於均線時倍數',
                'type': 'float',
                'default': 1.5,
                'min': 1.0,
                'max': 3.0,
                'step': 0.1,
                'description': '價格在均線下方時的投入倍數'
            },
        ]
