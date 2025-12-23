# strategies/dca_profit_taking.py
"""V5: Profit Taking Strategy - Take profits when cumulative return exceeds threshold."""

from typing import Dict, Any, List
import pandas as pd

from .base_strategy import BaseStrategy, InvestmentDecision


class DCAProfitTakingStrategy(BaseStrategy):
    """
    V5: Profit Taking Strategy
    
    Combines regular DCA investing with periodic profit taking.
    When cumulative return exceeds a threshold, sells a portion
    of holdings to lock in profits.
    
    Logic:
    - Regular DCA investment each period
    - Track cumulative return
    - When return >= threshold: sell X% of holdings
    - Continue regular DCA
    """
    
    @property
    def name(self) -> str:
        return "定期減碼 (Profit Taking)"
    
    @property
    def short_name(self) -> str:
        return "V5"
    
    @property
    def description(self) -> str:
        return "累積報酬達到目標時部分獲利了結，鎖定利潤後繼續定期投入。"
    
    @property
    def default_params(self) -> Dict[str, Any]:
        return {
            'profit_threshold': 0.30,    # 30% cumulative return
            'sell_percentage': 0.30,      # Sell 30% of holdings
            'cooldown_periods': 6,        # Wait 6 periods before next sell
        }
    
    def __init__(self, params=None):
        super().__init__(params)
        self._last_sell_date = None
        self._periods_since_sell = float('inf')
    
    def calculate_investment(
        self,
        current_price: float,
        current_date: pd.Timestamp,
        historical_data: pd.DataFrame,
        portfolio_state: Dict[str, float]
    ) -> InvestmentDecision:
        """
        Calculate investment decision with profit taking logic.
        
        Args:
            current_price: Current period's price
            current_date: Current period's date
            historical_data: Historical price data
            portfolio_state: Current portfolio state
            
        Returns:
            InvestmentDecision with optional sell instruction
        """
        threshold = self.params['profit_threshold']
        sell_pct = self.params['sell_percentage']
        cooldown = self.params['cooldown_periods']
        
        # Get current cumulative return
        cum_return = portfolio_state.get('cumulative_return', 0) / 100  # Convert from %
        
        # Track cooldown
        if self._last_sell_date is not None:
            self._periods_since_sell += 1
        else:
            self._periods_since_sell = float('inf')
        
        # Check if should take profit
        should_sell = (
            cum_return >= threshold and
            self._periods_since_sell >= cooldown and
            portfolio_state.get('total_shares', 0) > 0
        )
        
        if should_sell:
            self._last_sell_date = current_date
            self._periods_since_sell = 0
            
            return InvestmentDecision(
                investment_multiplier=1.0,  # Still invest normal amount
                sell_percentage=sell_pct,
                reason=f"累積報酬 {cum_return:.1%} ≥ {threshold:.0%}，賣出 {sell_pct:.0%} 獲利了結"
            )
        else:
            reason = "正常投入"
            if cum_return >= threshold and self._periods_since_sell < cooldown:
                reason = f"冷卻期中 ({self._periods_since_sell}/{cooldown})，正常投入"
            
            return InvestmentDecision(
                investment_multiplier=1.0,
                sell_percentage=0.0,
                reason=reason
            )
    
    def reset(self):
        """Reset strategy state for new backtest."""
        self._last_sell_date = None
        self._periods_since_sell = float('inf')
    
    def get_param_info(self) -> List[Dict[str, Any]]:
        """Return parameter information for UI display."""
        return [
            {
                'name': 'profit_threshold',
                'label': '獲利了結閾值',
                'type': 'float',
                'default': 0.30,
                'min': 0.10,
                'max': 1.0,
                'step': 0.05,
                'description': '累積報酬率達此比例時觸發賣出'
            },
            {
                'name': 'sell_percentage',
                'label': '賣出比例',
                'type': 'float',
                'default': 0.30,
                'min': 0.10,
                'max': 0.50,
                'step': 0.05,
                'description': '每次獲利了結時賣出的持股比例'
            },
            {
                'name': 'cooldown_periods',
                'label': '冷卻期（期數）',
                'type': 'int',
                'default': 6,
                'min': 1,
                'max': 24,
                'step': 1,
                'description': '兩次賣出之間的最小間隔期數'
            },
        ]
