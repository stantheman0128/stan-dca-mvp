# core/data_loader.py
"""Data download and caching module for market data."""

import os
import pickle
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

import pandas as pd
import yfinance as yf
import yaml


class DataLoader:
    """Handles market data download, caching, and retrieval."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize DataLoader with configuration.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.cache_dir = Path(self.config.get('cache', {}).get('directory', 'data/cache'))
        self.cache_enabled = self.config.get('cache', {}).get('enabled', True)
        self.max_age_days = self.config.get('cache', {}).get('max_age_days', 1)
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            # Return default configuration if file not found
            return {
                'cache': {
                    'enabled': True,
                    'directory': 'data/cache',
                    'max_age_days': 1
                }
            }
    
    def get_supported_markets(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all supported markets from configuration.
        
        Returns:
            Dictionary of market symbols and their info
        """
        markets = {}
        market_groups = self.config.get('markets', {})
        for group_name, group_markets in market_groups.items():
            for symbol, info in group_markets.items():
                markets[symbol] = {
                    'name': info.get('name', symbol),
                    'currency': info.get('currency', 'USD'),
                    'group': group_name
                }
        return markets
    
    def _get_cache_path(self, symbol: str) -> Path:
        """Get cache file path for a symbol."""
        # Replace special characters for valid filename
        safe_symbol = symbol.replace('^', '_').replace('.', '_')
        return self.cache_dir / f"{safe_symbol}_data.pkl"
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file is still valid (not expired)."""
        if not cache_path.exists():
            return False
        
        # Check file modification time
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age = datetime.now() - mtime
        return age < timedelta(days=self.max_age_days)
    
    def _load_from_cache(self, symbol: str) -> Optional[pd.DataFrame]:
        """Load data from cache if available and valid."""
        if not self.cache_enabled:
            return None
        
        cache_path = self._get_cache_path(symbol)
        if not self._is_cache_valid(cache_path):
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                cached = pickle.load(f)
                return cached.get('data')
        except Exception:
            return None
    
    def _save_to_cache(self, symbol: str, data: pd.DataFrame) -> None:
        """Save data to cache."""
        if not self.cache_enabled:
            return
        
        cache_path = self._get_cache_path(symbol)
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump({
                    'symbol': symbol,
                    'data': data,
                    'timestamp': datetime.now().isoformat()
                }, f)
        except Exception:
            pass  # Silently fail cache write
    
    def download_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        use_cache: bool = True,
        max_retries: int = 3
    ) -> Optional[pd.DataFrame]:
        """
        Download market data for a symbol.
        
        Args:
            symbol: Market symbol (e.g., 'SPY', '0050.TW')
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            use_cache: Whether to use cached data if available
            max_retries: Maximum number of download retry attempts
            
        Returns:
            DataFrame with OHLCV data, or None if download fails
            
        Raises:
            ValueError: If no data is available for the symbol
        """
        # Use defaults from config if not specified
        if start_date is None:
            start_date = self.config.get('defaults', {}).get('start_date', '2005-12-23')
        if end_date is None:
            end_date = self.config.get('defaults', {}).get('end_date', date.today().isoformat())
        
        # Try loading from cache first
        if use_cache:
            cached_data = self._load_from_cache(symbol)
            if cached_data is not None:
                # Filter to requested date range
                cached_data.index = pd.to_datetime(cached_data.index)
                mask = (cached_data.index >= start_date) & (cached_data.index <= end_date)
                filtered = cached_data.loc[mask]
                if not filtered.empty:
                    return filtered
        
        # Download from yfinance with retry logic
        last_error = None
        for attempt in range(max_retries):
            try:
                data = yf.download(
                    symbol,
                    start=start_date,
                    end=end_date,
                    progress=False,
                    auto_adjust=True
                )
                
                if data.empty:
                    raise ValueError(f"No data available for {symbol}")
                
                # Handle MultiIndex columns (yfinance 0.2.40+)
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                
                # Validate data
                required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                missing = [col for col in required_columns if col not in data.columns]
                if missing:
                    raise ValueError(f"Missing columns: {missing}")
                
                # Handle missing values
                data = data.ffill()  # Forward fill
                
                # Save to cache (save full range, not just requested)
                self._save_to_cache(symbol, data)
                
                return data
                
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    continue  # Retry
        
        # All retries failed
        return None
    
    def get_data_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get information about available data for a symbol.
        
        Args:
            symbol: Market symbol
            
        Returns:
            Dictionary with data info (date range, record count, etc.)
        """
        data = self.download_data(symbol)
        if data is None or data.empty:
            return {'available': False}
        
        return {
            'available': True,
            'symbol': symbol,
            'start_date': data.index.min().strftime('%Y-%m-%d'),
            'end_date': data.index.max().strftime('%Y-%m-%d'),
            'records': len(data),
            'columns': list(data.columns)
        }
    
    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """
        Clear cached data.
        
        Args:
            symbol: Specific symbol to clear, or None to clear all
        """
        if symbol:
            cache_path = self._get_cache_path(symbol)
            if cache_path.exists():
                cache_path.unlink()
        else:
            for cache_file in self.cache_dir.glob("*_data.pkl"):
                cache_file.unlink()
    
    def refresh_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Force refresh data from source (bypassing cache).
        
        Args:
            symbol: Market symbol
            
        Returns:
            Fresh DataFrame from yfinance
        """
        return self.download_data(symbol, use_cache=False)
