import os
import time
import random
import requests
from typing import List, Dict, Any, Optional, Tuple
from fastapi import HTTPException
from dotenv import load_dotenv
from .cache import search_cache
from search_server.globals import increment_request_count

load_dotenv()

class GoogleSearchAPI:
    def __init__(self):
        """Initialize Google Search API with multiple API keys and CSE IDs."""
        self.api_keys = self._load_env_list("GOOGLE_API_KEYS")
        self.cse_ids = self._load_env_list("GOOGLE_CSE_IDS")
        
        if not self.api_keys or not self.cse_ids:
            raise ValueError(
                "Please set GOOGLE_API_KEYS and GOOGLE_CSE_IDS environment variables. "
                "Multiple values should be comma-separated."
            )
        
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.current_api_index = 0
        self.current_cse_index = 0
        self.last_request_time = 0
        self.min_request_interval = 0.1
    
    def _load_env_list(self, env_var: str) -> List[str]:
        """Load a comma-separated list from environment variable."""
        value = os.getenv(env_var, "")
        return [item.strip() for item in value.split(",") if item.strip()]
    
    def _get_next_credentials(self) -> Tuple[str, str]:
        """Get the next API key and CSE ID pair, rotating through available options."""
        api_key = self.api_keys[self.current_api_index]
        cse_id = self.cse_ids[self.current_cse_index]
        
        self.current_cse_index = (self.current_cse_index + 1) % len(self.cse_ids)
        if self.current_cse_index == 0:
            self.current_api_index = (self.current_api_index + 1) % len(self.api_keys)
        
        return api_key, cse_id
    
    def _rate_limit_delay(self):
        """Add delay to prevent rate limiting."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            delay = self.min_request_interval - time_since_last
            time.sleep(delay)
        
        self.last_request_time = time.time()
    
    def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to Google Custom Search API with error handling."""
        max_retries = len(self.api_keys) * len(self.cse_ids)
        
        for attempt in range(max_retries):
            api_key, cse_id = self._get_next_credentials()
            
            request_params = {
                **params,
                'key': api_key,
                'cx': cse_id
            }
            
            self._rate_limit_delay()
            
            try:
                response = requests.get(self.base_url, params=request_params, timeout=10)
                
                if response.status_code == 200:
                    increment_request_count()
                    return response.json()
                
                elif response.status_code == 429:
                    print(f"Rate limit exceeded for API key {api_key[:10]}... (attempt {attempt + 1})")
                    time.sleep(min(2 ** attempt, 60))
                    continue
                
                elif response.status_code == 403:  # quota exceeded or invalid key
                    print(f"Quota exceeded or invalid API key {api_key[:10]}... (attempt {attempt + 1})")
                    continue
                
                else:
                    print(f"API request failed with status {response.status_code}: {response.text}")
                    continue
            
            except requests.exceptions.RequestException as e:
                print(f"Request failed for API key {api_key[:10]}...: {e}")
                continue
        
        raise HTTPException(
            status_code=503,
            detail="Google Search API temporarily unavailable. All API keys exhausted or rate limited."
        )

    def search(
        self,
        query: str,
        num_results: int = 10,
        start: int = 1,
        site_search: Optional[str] = None,
        date_restrict: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search Google with caching support.
        
        Args:
            query: Search query
            num_results: Number of results to return (max 10 per request)
            start: Starting index for results
            site_search: Restrict search to specific site
            date_restrict: Date restriction (e.g., 'd1' for past day, 'w1' for past week)
            **kwargs: Additional search parameters
            
        Returns:
            Search results dictionary
        """
        cache_params = {
            'num_results': num_results,
            'start': start,
            'site_search': site_search,
            'date_restrict': date_restrict,
            **kwargs
        }
        
        cached_results = search_cache.get(query, **cache_params)
        if cached_results:
            print(f"Cache hit for query: '{query}'")
            return cached_results
        
        search_params = {
            'q': query,
            'num': min(num_results, 10),
            'start': start
        }
        
        if site_search:
            search_params['siteSearch'] = site_search
        
        if date_restrict:
            search_params['dateRestrict'] = date_restrict
        
        search_params.update(kwargs)
        
        print(f"Making API request for query: '{query}'")
        results = self._make_request(search_params)
        
        processed_results = self._process_results(results)
        search_cache.set(query, processed_results, **cache_params)
        
        return processed_results
    
    def _process_results(self, raw_results: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw Google API results into a cleaner format."""
        items = raw_results.get('items', [])
        
        processed_items = []
        for item in items:
            processed_item = {
                'title': item.get('title', ''),
                'link': item.get('link', ''),
                'snippet': item.get('snippet', ''),
                'display_link': item.get('displayLink', ''),
                'formatted_url': item.get('formattedUrl', ''),
            }
            
            if 'cacheId' in item:
                processed_item['cache_id'] = item['cacheId']
            
            if 'pagemap' in item:
                processed_item['pagemap'] = item['pagemap']
            
            processed_items.append(processed_item)
        
        return {
            'items': processed_items,
            'search_information': raw_results.get('searchInformation', {}),
            'total_results': raw_results.get('searchInformation', {}).get('totalResults', '0'),
            'search_time': raw_results.get('searchInformation', {}).get('searchTime', 0),
            'queries': raw_results.get('queries', {}),
        }

google_search_api = GoogleSearchAPI()

def google_search(
    query: str,
    num_results: int = 5,
    start: int = 1,
    site_search: Optional[str] = None,
    date_restrict: Optional[str] = None,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Convenience function for Google Search with caching.
    
    Args:
        query: Search query
        num_results: Number of results to return
        start: Starting index for results
        site_search: Restrict search to specific site
        date_restrict: Date restriction
        **kwargs: Additional search parameters
        
    Returns:
        List of search result items
    """
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    if num_results < 1 or num_results > 5:
        raise HTTPException(status_code=400, detail="num_results must be between 1 and 5")

    try:
        results = google_search_api.search(
            query=query,
            num_results=num_results,
            start=start,
            site_search=site_search,
            date_restrict=date_restrict,
            **kwargs
        )
        return results.get('items', [])
    
    except Exception as e:
        print(f"Google search error: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred on our end. Please try again later.")