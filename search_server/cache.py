import json
import time
import hashlib
from typing import Dict, Any, Optional
from pathlib import Path
import os

class SearchCache:
    def __init__(self, cache_dir: str = "search_cache", ttl_seconds: int = 60 * 60 * 24):
        """
        Initialize the search cache.
        
        Args:
            cache_dir: Directory to store cache files
            ttl_seconds: Time to live for cache entries in seconds (default: 1 day)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl_seconds = ttl_seconds
    
    def _get_cache_key(self, query: str, **kwargs) -> str:
        """Generate a cache key based on the query and parameters."""
        cache_data = {"query": query, **kwargs}
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _get_cache_file_path(self, cache_key: str) -> Path:
        """Get the full path to a cache file."""
        return self.cache_dir / f"{cache_key}.json"
    
    def get(self, query: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached search results.
        
        Args:
            query: Search query
            **kwargs: Additional parameters to include in cache key
            
        Returns:
            Cached results if found and not expired, None otherwise
        """
        cache_key = self._get_cache_key(query, **kwargs)
        cache_file = self._get_cache_file_path(cache_key)
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            if time.time() - cached_data.get('timestamp', 0) > self.ttl_seconds:
                cache_file.unlink(missing_ok=True)
                return None
            
            return cached_data.get('results')
        
        except (json.JSONDecodeError, KeyError, OSError) as e:
            print(f"Error reading cache file {cache_file}: {e}")
            cache_file.unlink(missing_ok=True)
            return None
    
    def set(self, query: str, results: Dict[str, Any], **kwargs) -> None:
        """
        Store search results in cache.
        
        Args:
            query: Search query
            results: Search results to cache
            **kwargs: Additional parameters to include in cache key
        """
        cache_key = self._get_cache_key(query, **kwargs)
        cache_file = self._get_cache_file_path(cache_key)
        
        cache_data = {
            'timestamp': time.time(),
            'query': query,
            'results': results,
            'params': kwargs
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"Error writing to cache file {cache_file}: {e}")
    
    def clear_expired(self) -> int:
        """
        Remove expired cache entries.
        
        Returns:
            Number of expired entries removed
        """
        removed_count = 0
        current_time = time.time()
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                if current_time - cached_data.get('timestamp', 0) > self.ttl_seconds:
                    cache_file.unlink()
                    removed_count += 1
            
            except (json.JSONDecodeError, KeyError, OSError):
                # Remove corrupted files
                cache_file.unlink(missing_ok=True)
                removed_count += 1
        
        return removed_count
    
    def clear_all(self) -> int:
        """
        Clear all cache entries.
        
        Returns:
            Number of entries removed
        """
        removed_count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                removed_count += 1
            except OSError:
                pass
        
        return removed_count

search_cache = SearchCache()