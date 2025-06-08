from fastapi import FastAPI, HTTPException, Query, Depends, Header
from typing import Dict, Any, Optional
from search_server.google_search import google_search
from search_server.news_search import news_search
from search_server.cache import search_cache
from search_server.globals import get_request_count
import os
import requests
from utils.news_content_strip import extract_main_content
from utils.models import extract

app = FastAPI(title="uplink", version="1.0.0")

API_KEY = os.getenv("API_KEY", "hackathon-2025")

def verify_api_key(x_api_key: str = Header(None)):
    """Simple API key verification"""
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401, 
            detail="Invalid API key. Include 'X-API-Key' header with valid key."
        )
    return True

@app.get("/")
def root():
    """Health check endpoint."""
    return {"message": "uplink is alive and well -- mikus"}

@app.get("/scrape")
def scrape_endpoint(
    url: str = Query(..., description="URL to scrape"),
    authenticated: bool = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Scrape a web page, extract main content, and summarize.
    Args:
        url: URL to scrape
    Returns:
        Extracted and summarized main content
    """
    try:
        if not url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="Invalid URL format. Must start with http:// or https://")
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200 or any(x in resp.text.lower() for x in ["cloudflare", "rate limit", "captcha"]):
            raise HTTPException(status_code=429, detail="Blocked by site or rate limited.")
        main_content = extract_main_content(resp.text)
        summary = extract(main_content)
        return {"url": url, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
def search_endpoint(
    q: str = Query(..., description="Search query"),
    num: int = Query(5, ge=1, le=5, description="Number of results (1-5)"),
    start: int = Query(1, ge=1, description="Starting index for results"),
    site: Optional[str] = Query(None, description="Restrict search to specific site"),
    date_restrict: Optional[str] = Query(None, description="Date restriction (e.g., 'd1', 'w1', 'm1')"),
    authenticated: bool = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Search endpoint.
    
    Args:
        q: Search query
        num: Number of results to return (1-5)
        start: Starting index for results
        site: Restrict search to specific site (optional)
        date_restrict: Date restriction (optional)
        
    Returns:
        Search results with metadata
    """
    try:
        results = google_search(
            query=q,
            num_results=num,
            start=start,
            site_search=site,
            date_restrict=date_restrict
        )
        
        return {
            "query": q,
            "results": results,
            "count": len(results),
            "start": start
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/news")
def search_news_endpoint(
    q: str = Query(..., description="News search query"),
    num: int = Query(10, ge=1, le=10, description="Number of results (1-10)"),
    authenticated: bool = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    News search plz
    Args:
        q: Search query
        num: Number of results to return (1-10)
    Returns:
        Search results with metadata
    """
    try:
        results = news_search(query=q, top_k=num)
        
        return {
            "query": q,
            "results": results,
            "count": len(results) if results else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cache/stats")
def cache_stats(authenticated: bool = Depends(verify_api_key)) -> Dict[str, Any]:
    """cache stats"""
    try:
        cache_dir = search_cache.cache_dir
        cache_files = list(cache_dir.glob("*.json"))
        
        return {
            "cache_directory": str(cache_dir),
            "cached_queries": len(cache_files),
            "ttl_seconds": search_cache.ttl_seconds
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
def status():
    """status endpoint that literally just returns operational and the total number of requests made to the server"""
    try:
        return {
            "status": "operational",
            "total_requests": get_request_count(),
        }
        
    except Exception as e:
        print(f"Error retrieving status: {e}")
        return {
            "status": "error",
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
