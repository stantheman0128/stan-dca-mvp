# strategies/base_strategy.py
"""Base strategy class for all DCA strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

import pandas as pd
import numpy as np


@dataclass
class InvestmentDecision:
    """Represents the investment decision for a single period."""
    investment_multiplier: float = 1.0  # Multiplier applied to base amount
    sell_percentage: float = 0.0  # Percentage of holdings to sell (0-1)
    reason: str = ""  # Explanation for the decision


class BaseStrategy(ABC):
    """
    Abstract base class for all DCA strategies.
    
    All strategies must implement:
    - name: Strategy display name
    - description: Strategy description
    - default_params: Default parameter values
    - calculate_investment: Investment decision logic
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize strategy with optional custom parameters.
        
        Args:
            params: Custom parameters to override defaults
        """
        self.params = {**self.default_params}
        if params:
            self.params.update(params)
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy display name."""
        pass
    
    @property
    @abstractmethod
    def short_name(self) -> str:
        """Short name for charts/tables (e.g., 'V0', 'V1')."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Strategy description."""
        pass
    
    @property
    @abstractmethod
    def default_params(self) -> Dict[str, Any]:
        """Default parameter values."""
        pass
    
    @abstractmethod
    def calculate_investment(
        self,
        current_price: float,
        current_date: pd.Timestamp,
        historical_data: pd.DataFrame,
        portfolio_state: Dict[str, float]
    ) -> InvestmentDecision:
        """
        Calculate the investment decision for the current period.
        
        Args:
            current_price: Current period's price
            current_date: Current period's date
            historical_data: Historical price data up to current date
            portfolio_state: Current portfolio state with keys:
                - total_shares: Total shares held
                - total_cost: Total amount invested
                - current_value: Current portfolio value
                - cumulative_return: Cumulative return percentage
                
        Returns:
            InvestmentDecision with multiplier and optional sell instruction
        """
        pass
    
    def get_param(self, key: str) -> Any:
        """Get a parameter value."""
        return self.params.get(key)
    
    def set_param(self, key: str, value: Any) -> None:
        """Set a parameter value."""
        self.params[key] = value
    
    def get_param_info(self) -> List[Dict[str, Any]]:
        """
        Get information about strategy parameters for UI display.
        
        Returns:
            List of parameter info dicts with keys:
            - name: Parameter name
            - label: Display label
            - type: Parameter type (int, float, str)
            - default: Default value
            - min: Minimum value (optional)
            - max: Maximum value (optional)
            - step: Step size (optional)
            - description: Parameter description
        """
        return []
    
    def validate_params(self) -> List[str]:
        """
        Validate current parameters.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        return []
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(params={self.params})"
