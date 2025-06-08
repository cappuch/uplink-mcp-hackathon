from utils.search import search
from typing import List, Dict, Any
from fastapi import HTTPException

def news_search(query: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Search for articles matching the query.
    
    Args:
        query (str): The search query
        top_k (int): Number of top results to return
    
    Returns:
        List[Dict[str, Any]]: List of articles matching the query
    """
    try:
        if top_k > 5:
            raise HTTPException(status_code=400, detail="top_k must be less than or equal to 5")

        if not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        results = search(query, top_k)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail="An error occurred on our end. Please try again later.")