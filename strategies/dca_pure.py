# strategies/dca_pure.py
"""V0: Pure DCA Strategy - Fixed periodic investment."""

from typing import Dict, Any, List
import pandas as pd

from .base_strategy import BaseStrategy, InvestmentDecision


class DCAPureStrategy(BaseStrategy):
    """
    V0: Pure Dollar-Cost Averaging Strategy
    
    The most basic DCA strategy that invests a fixed amount
    at regular intervals regardless of market conditions.
    This serves as the baseline for comparing all other strategies.
    """
    
    @property
    def name(self) -> str:
        return "純定期定額 (Pure DCA)"
    
    @property
    def short_name(self) -> str:
        return "V0"
    
    @property
    def description(self) -> str:
        return "每期固定投入相同金額，不考慮市場狀況。作為所有優化策略的對比基準。"
    
    @property
    def default_params(self) -> Dict[str, Any]:
        return {}  # No additional parameters needed
    
    def calculate_investment(
        self,
        current_price: float,
        current_date: pd.Timestamp,
        historical_data: pd.DataFrame,
        portfolio_state: Dict[str, float]
    ) -> InvestmentDecision:
        """
        Pure DCA always invests with 1.0 multiplier.
        
        Args:
            current_price: Current period's price
            current_date: Current period's date
            historical_data: Historical price data
            portfolio_state: Current portfolio state
            
        Returns:
            InvestmentDecision with multiplier 1.0
        """
        return InvestmentDecision(
            investment_multiplier=1.0,
            sell_percentage=0.0,
            reason="Fixed periodic investment"
        )
    
    def get_param_info(self) -> List[Dict[str, Any]]:
        """Pure DCA has no adjustable parameters."""
        return []
