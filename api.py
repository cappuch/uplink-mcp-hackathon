from utils.search import search
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/news/search")
def search_endpoint(query: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Search for articles matching the query.
    
    Args:
        query (str): The search query
        top_k (int): Number of top results to return
    
    Returns:
        List[Dict[str, Any]]: List of articles matching the query
    """
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    results = search(query, top_k)
    return results

# start server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)