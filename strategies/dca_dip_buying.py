# strategies/dca_dip_buying.py
"""V1: Dip Buying Strategy - Increase investment when price drops significantly."""

from typing import Dict, Any, List
import pandas as pd
import numpy as np

from .base_strategy import BaseStrategy, InvestmentDecision


class DCADipBuyingStrategy(BaseStrategy):
    """
    V1: Dip Buying Strategy
    
    Increases investment amount when the current price drops significantly
    from recent highs. Uses a tiered system with multiple thresholds
    and corresponding multipliers.
    
    Logic:
    - Track the highest price in the lookback period
    - Calculate current drawdown from that high
    - Apply multiplier based on drawdown level
    """
    
    @property
    def name(self) -> str:
        return "跌深加碼 (Dip Buying)"
    
    @property
    def short_name(self) -> str:
        return "V1"
    
    @property
    def description(self) -> str:
        return "當價格相對近期高點大幅下跌時，增加投入金額。跌幅越大，加碼越多。"
    
    @property
    def default_params(self) -> Dict[str, Any]:
        return {
            'lookback_period': 252,      # Trading days (1 year)
            'dip_threshold_1': 0.10,     # 10% drop
            'multiplier_1': 1.5,         # 1.5x investment
            'dip_threshold_2': 0.20,     # 20% drop
            'multiplier_2': 2.0,         # 2.0x investment
        }
    
    def calculate_investment(
        self,
        current_price: float,
        current_date: pd.Timestamp,
        historical_data: pd.DataFrame,
        portfolio_state: Dict[str, float]
    ) -> InvestmentDecision:
        """
        Calculate investment multiplier based on drawdown from recent high.
        
        Args:
            current_price: Current period's price
            current_date: Current period's date
            historical_data: Historical price data (with 'Close' column)
            portfolio_state: Current portfolio state
            
        Returns:
            InvestmentDecision with multiplier based on dip level
        """
        lookback = self.params['lookback_period']
        threshold_1 = self.params['dip_threshold_1']
        threshold_2 = self.params['dip_threshold_2']
        multiplier_1 = self.params['multiplier_1']
        multiplier_2 = self.params['multiplier_2']
        
        # Get historical prices up to current date
        if 'Close' in historical_data.columns:
            prices = historical_data['Close']
        else:
            prices = historical_data.iloc[:, 0]  # Use first column
        
        # Filter to dates before or equal to current date
        mask = prices.index <= current_date
        relevant_prices = prices[mask]
        
        # Get lookback window
        if len(relevant_prices) < 2:
            return InvestmentDecision(
                investment_multiplier=1.0,
                reason="Insufficient historical data"
            )
        
        lookback_prices = relevant_prices.tail(lookback)
        
        # Calculate recent high and drawdown
        recent_high = lookback_prices.max()
        
        if recent_high <= 0:
            return InvestmentDecision(
                investment_multiplier=1.0,
                reason="Invalid price data"
            )
        
        drawdown = (recent_high - current_price) / recent_high
        
        # Determine multiplier based on drawdown level
        if drawdown >= threshold_2:
            return InvestmentDecision(
                investment_multiplier=multiplier_2,
                reason=f"跌幅 {drawdown:.1%} ≥ {threshold_2:.0%}，加碼 {multiplier_2}x"
            )
        elif drawdown >= threshold_1:
            return InvestmentDecision(
                investment_multiplier=multiplier_1,
                reason=f"跌幅 {drawdown:.1%} ≥ {threshold_1:.0%}，加碼 {multiplier_1}x"
            )
        else:
            return InvestmentDecision(
                investment_multiplier=1.0,
                reason=f"跌幅 {drawdown:.1%} < {threshold_1:.0%}，正常投入"
            )
    
    def get_param_info(self) -> List[Dict[str, Any]]:
        """Return parameter information for UI display."""
        return [
            {
                'name': 'lookback_period',
                'label': '回顧期間（交易日）',
                'type': 'int',
                'default': 252,
                'min': 20,
                'max': 504,
                'step': 21,
                'description': '計算近期高點的回顧天數（252天≈1年）'
            },
            {
                'name': 'dip_threshold_1',
                'label': '第一級跌幅閾值',
                'type': 'float',
                'default': 0.10,
                'min': 0.05,
                'max': 0.30,
                'step': 0.01,
                'description': '觸發第一級加碼的跌幅百分比'
            },
            {
                'name': 'multiplier_1',
                'label': '第一級加碼倍數',
                'type': 'float',
                'default': 1.5,
                'min': 1.0,
                'max': 3.0,
                'step': 0.1,
                'description': '達到第一級跌幅時的投入倍數'
            },
            {
                'name': 'dip_threshold_2',
                'label': '第二級跌幅閾值',
                'type': 'float',
                'default': 0.20,
                'min': 0.10,
                'max': 0.50,
                'step': 0.01,
                'description': '觸發第二級加碼的跌幅百分比'
            },
            {
                'name': 'multiplier_2',
                'label': '第二級加碼倍數',
                'type': 'float',
                'default': 2.0,
                'min': 1.5,
                'max': 5.0,
                'step': 0.1,
                'description': '達到第二級跌幅時的投入倍數'
            },
        ]
    
    def validate_params(self) -> List[str]:
        """Validate parameters."""
        errors = []
        
        if self.params['dip_threshold_2'] <= self.params['dip_threshold_1']:
            errors.append("第二級跌幅閾值必須大於第一級")
        
        if self.params['multiplier_2'] <= self.params['multiplier_1']:
            errors.append("第二級加碼倍數應大於第一級")
        
        return errors
