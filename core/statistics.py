# core/statistics.py
"""Statistical analysis module for strategy comparison."""

from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
from scipy import stats


class StatisticalAnalyzer:
    """
    Performs statistical tests to validate strategy differences.
    """
    
    @staticmethod
    def compare_strategies_ttest(
        returns_a: pd.Series,
        returns_b: pd.Series,
        alpha: float = 0.05
    ) -> Dict[str, Any]:
        """
        Compare two strategies using independent t-test.
        
        Tests whether the mean returns of two strategies are
        significantly different.
        
        Args:
            returns_a: Return series for strategy A
            returns_b: Return series for strategy B
            alpha: Significance level (default 0.05)
            
        Returns:
            Dictionary with test results:
            - t_statistic: t-test statistic
            - p_value: Two-tailed p-value
            - significant: Whether difference is significant
            - conclusion: Text explanation
            - mean_diff: Difference in means
        """
        # Clean data
        returns_a = returns_a.dropna()
        returns_b = returns_b.dropna()
        
        if len(returns_a) < 2 or len(returns_b) < 2:
            return {
                't_statistic': None,
                'p_value': None,
                'significant': False,
                'conclusion': '數據不足，無法進行統計檢驗',
                'mean_diff': None,
            }
        
        # Perform t-test
        t_stat, p_value = stats.ttest_ind(returns_a, returns_b)
        
        # Calculate mean difference
        mean_a = returns_a.mean()
        mean_b = returns_b.mean()
        mean_diff = mean_a - mean_b
        
        # Determine significance
        significant = p_value < alpha
        
        # Generate conclusion
        if significant:
            if mean_diff > 0:
                conclusion = f"策略 A 顯著優於策略 B (差異 {mean_diff:.2f}%, p = {p_value:.4f})"
            else:
                conclusion = f"策略 B 顯著優於策略 A (差異 {-mean_diff:.2f}%, p = {p_value:.4f})"
        else:
            conclusion = f"兩策略無顯著差異 (p = {p_value:.4f} > {alpha})"
        
        return {
            't_statistic': t_stat,
            'p_value': p_value,
            'significant': significant,
            'conclusion': conclusion,
            'mean_diff': mean_diff,
            'mean_a': mean_a,
            'mean_b': mean_b,
        }
    
    @staticmethod
    def confidence_interval(
        returns: pd.Series,
        confidence: float = 0.95
    ) -> Tuple[float, float]:
        """
        Calculate confidence interval for mean return.
        
        Args:
            returns: Return series
            confidence: Confidence level (default 0.95 for 95%)
            
        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        returns = returns.dropna()
        
        if len(returns) < 2:
            return (0.0, 0.0)
        
        n = len(returns)
        mean = returns.mean()
        std_err = returns.std() / np.sqrt(n)
        
        # Get t-critical value
        alpha = 1 - confidence
        t_critical = stats.t.ppf(1 - alpha/2, df=n-1)
        
        margin = t_critical * std_err
        
        return (mean - margin, mean + margin)
    
    @staticmethod
    def multi_strategy_comparison(
        returns_dict: Dict[str, pd.Series],
        alpha: float = 0.05
    ) -> pd.DataFrame:
        """
        Compare multiple strategies with Bonferroni correction.
        
        Args:
            returns_dict: Dictionary mapping strategy name to return series
            alpha: Base significance level
            
        Returns:
            DataFrame with pairwise comparison results
        """
        strategy_names = list(returns_dict.keys())
        n_strategies = len(strategy_names)
        
        if n_strategies < 2:
            return pd.DataFrame()
        
        # Bonferroni correction
        n_comparisons = n_strategies * (n_strategies - 1) // 2
        adjusted_alpha = alpha / n_comparisons
        
        results = []
        
        for i in range(n_strategies):
            for j in range(i + 1, n_strategies):
                name_a = strategy_names[i]
                name_b = strategy_names[j]
                
                comparison = StatisticalAnalyzer.compare_strategies_ttest(
                    returns_dict[name_a],
                    returns_dict[name_b],
                    alpha=adjusted_alpha
                )
                
                results.append({
                    '策略 A': name_a,
                    '策略 B': name_b,
                    't 統計量': comparison['t_statistic'],
                    'p 值': comparison['p_value'],
                    '顯著差異': '是' if comparison['significant'] else '否',
                    '平均差異 (%)': comparison['mean_diff'],
                })
        
        return pd.DataFrame(results)
    
    @staticmethod
    def calculate_statistics_summary(
        returns: pd.Series
    ) -> Dict[str, float]:
        """
        Calculate comprehensive statistics for a return series.
        
        Args:
            returns: Return series
            
        Returns:
            Dictionary with statistical measures
        """
        returns = returns.dropna()
        
        if len(returns) < 2:
            return {}
        
        return {
            'mean': returns.mean(),
            'median': returns.median(),
            'std': returns.std(),
            'min': returns.min(),
            'max': returns.max(),
            'skewness': returns.skew(),
            'kurtosis': returns.kurtosis(),
            'count': len(returns),
            'positive_pct': (returns > 0).mean() * 100,
        }
    
    @staticmethod
    def normality_test(returns: pd.Series) -> Dict[str, Any]:
        """
        Test if returns are normally distributed (Shapiro-Wilk test).
        
        Args:
            returns: Return series
            
        Returns:
            Dictionary with test results
        """
        returns = returns.dropna()
        
        if len(returns) < 3:
            return {
                'statistic': None,
                'p_value': None,
                'is_normal': None,
                'conclusion': '數據不足'
            }
        
        # Shapiro-Wilk test (max 5000 samples)
        sample = returns if len(returns) <= 5000 else returns.sample(5000)
        stat, p_value = stats.shapiro(sample)
        
        is_normal = p_value > 0.05
        
        return {
            'statistic': stat,
            'p_value': p_value,
            'is_normal': is_normal,
            'conclusion': '符合常態分佈' if is_normal else '不符合常態分佈'
        }
