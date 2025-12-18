"""URL validation utilities with caching support."""

import time
import requests
from core.constants import URL_VALIDATION_TIMEOUT_HEAD, CACHE_TIMEOUT


class URLValidator:
    """URL validator with built-in caching to avoid redundant network requests."""
    
    def __init__(self):
        """Initialize validator with empty cache."""
        self._cache = {}
    
    def _is_cached(self, url: str) -> tuple[bool, bool | None]:
        """Check if URL validation result is cached and still valid.
        
        Args:
            url: URL to check
            
        Returns:
            tuple: (is_cached: bool, is_valid: bool or None)
        """
        if url in self._cache:
            is_valid, timestamp = self._cache[url]
            if time.time() - timestamp < CACHE_TIMEOUT:
                return (True, is_valid)
        return (False, None)
    
    def _cache_result(self, url: str, is_valid: bool) -> None:
        """Store URL validation result in cache.
        
        Args:
            url: URL to cache
            is_valid: Validation result
        """
        self._cache[url] = (is_valid, time.time())
    
    def validate(self, url: str, use_cache: bool = True) -> bool:
        """Validate URL by checking HTTP response.
        
        Uses HEAD request first, falls back to GET if needed.
        Results are cached to avoid redundant requests.
        
        Args:
            url: URL to validate
            use_cache: If True, use cached results (default: True)
            
        Returns:
            bool: True if URL is valid (2xx or 3xx status), False otherwise
        """
        if use_cache:
            is_cached, is_valid = self._is_cached(url)
            if is_cached:
                return is_valid
        
        try:
            resp = requests.head(url, timeout=URL_VALIDATION_TIMEOUT_HEAD, allow_redirects=True)
            if 200 <= resp.status_code < 400:
                result = True
            else:
                resp = requests.get(url, stream=True, timeout=URL_VALIDATION_TIMEOUT_HEAD, allow_redirects=True)
                result = 200 <= resp.status_code < 400
            
            self._cache_result(url, result)
            return result
        except Exception:
            self._cache_result(url, False)
            return False
    
    def clear_cache(self) -> None:
        """Clear all cached validation results."""
        self._cache.clear()
    
    def get_cache_size(self) -> int:
        """Get number of cached URLs.
        
        Returns:
            int: Number of URLs in cache
        """
        return len(self._cache)
