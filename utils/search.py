import numpy as np
from typing import List, Dict, Any, Tuple
import json

from utils.db import get_connection, TABLE_NAME
from utils.models import embed_text

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float: # cosine = dot(a, b) / (||a|| * ||b||)
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        a, b: numpy arrays representing vectors
        
    Returns:
        float: cosine similarity score (-1 to 1)
    """
    # flatten arrays in case they are 2D (just in case)
    a = a.flatten()
    b = b.flatten()
    
    # dot product
    dot_product = np.dot(a, b)
    
    # norm
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    # clip
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    # cosine
    similarity = dot_product / (norm_a * norm_b)
    return float(similarity)

def search(query: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Search for articles similar to the query using cosine similarity.
    
    Args:
        query (str): The search query string
        top_k (int): Number of top results to return (default: 10)
    
    Returns:
        List[Dict[str, Any]]: List of records with similarity scores, sorted by relevance
    """
    # embed the query
    query_embedding = embed_text(query)
    query_embedding = np.array(query_embedding)
    
    # get all records with embeddings from database
    with get_connection() as conn:
        cursor = conn.execute(f'''
            SELECT id, title, url, content, embedding, source, bias 
            FROM {TABLE_NAME} 
            WHERE embedding IS NOT NULL AND embedding != ''
        ''')
        
        results = []
        for row in cursor:
            id, title, url, content, embedding_str, source, bias = row
            
            try:
                # parse embedding from json
                embedding = json.loads(embedding_str)
                embedding = np.array(embedding)
                
                # calculate cosine similarity
                similarity = cosine_similarity(query_embedding, embedding)
                
                # add to results
                results.append({
                    'id': id,
                    'title': title,
                    'url': url,
                    'content': content,
                    'source': source,
                    'bias': bias,
                    'similarity': similarity
                })
                
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                # skip records with invalid embeddings
                continue
    
    # sort by similarity (highest first) and return top_k
    results.sort(key=lambda x: x['similarity'], reverse=True)
    return results[:top_k]

def search_with_filters(
    query: str, 
    top_k: int = 10,
    sources: List[str] = None,
    bias_range: Tuple[int, int] = None,
    min_similarity: float = 0.0
) -> List[Dict[str, Any]]:
    """
    Advanced search with filters.
    
    Args:
        query (str): The search query string
        top_k (int): Number of top results to return
        sources (List[str]): Filter by specific sources (optional)
        bias_range (Tuple[int, int]): Filter by bias range, e.g., (-1, 1) for slightly left to slightly right
        min_similarity (float): Minimum similarity threshold (0.0 to 1.0)
    
    Returns:
        List[Dict[str, Any]]: Filtered and sorted results
    """
    results = search(query, top_k * 2)  # get more results to allow for filtering

    # apply filters
    filtered_results = []
    for result in results:
        # check similarity threshold
        if result['similarity'] < min_similarity:
            continue

        # check source filter
        if sources and result['source'] not in sources:
            continue

        # check bias filter
        if bias_range:
            try:
                bias_value = int(result['bias'])
                if not (bias_range[0] <= bias_value <= bias_range[1]):
                    continue
            except (ValueError, TypeError):
                continue
        
        filtered_results.append(result)
    
    return filtered_results[:top_k]

def batch_search(queries: List[str], top_k: int = 10) -> Dict[str, List[Dict[str, Any]]]:
    """
    Search multiple queries at once.
    
    Args:
        queries (List[str]): List of search query strings
        top_k (int): Number of top results per query
    
    Returns:
        Dict[str, List[Dict[str, Any]]]: Dictionary mapping each query to its results
    """
    results = {}
    for query in queries:
        results[query] = search(query, top_k)
    return results

def get_similar_articles(article_id: int, top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Find articles similar to a specific article by ID.
    
    Args:
        article_id (int): The ID of the reference article
        top_k (int): Number of similar articles to return
    
    Returns:
        List[Dict[str, Any]]: List of similar articles
    """
    # get the reference article's embedding
    with get_connection() as conn:
        cursor = conn.execute(f'''
            SELECT embedding, content FROM {TABLE_NAME} WHERE id = ?
        ''', (article_id,))
        row = cursor.fetchone()
        
        if not row:
            return []
        
        embedding_str, content = row
        
        try:
            reference_embedding = json.loads(embedding_str)
            reference_embedding = np.array(reference_embedding)
        except (json.JSONDecodeError, ValueError):
            return []

    # get all other articles and calculate similarity
    with get_connection() as conn:
        cursor = conn.execute(f'''
            SELECT id, title, url, content, embedding, source, bias 
            FROM {TABLE_NAME} 
            WHERE id != ? AND embedding IS NOT NULL AND embedding != ''
        ''', (article_id,))
        
        results = []
        for row in cursor:
            id, title, url, content, embedding_str, source, bias = row
            
            try:
                embedding = json.loads(embedding_str)
                embedding = np.array(embedding)
                
                similarity = cosine_similarity(reference_embedding, embedding)
                
                results.append({
                    'id': id,
                    'title': title,
                    'url': url,
                    'content': content,
                    'source': source,
                    'bias': bias,
                    'similarity': similarity
                })
                
            except (json.JSONDecodeError, ValueError, TypeError):
                continue

    # sort by similarity and return top_k
    results.sort(key=lambda x: x['similarity'], reverse=True)
    return results[:top_k]

def search_by_content_length(min_length: int = 0, max_length: int = None, top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Search articles by content length.
    
    Args:
        min_length (int): Minimum content length
        max_length (int): Maximum content length (None for no limit)
        top_k (int): Number of results to return
    
    Returns:
        List[Dict[str, Any]]: List of articles within length range
    """
    with get_connection() as conn:
        if max_length:
            cursor = conn.execute(f'''
                SELECT id, title, url, content, source, bias, LENGTH(content) as content_length
                FROM {TABLE_NAME} 
                WHERE LENGTH(content) >= ? AND LENGTH(content) <= ?
                ORDER BY LENGTH(content) DESC
                LIMIT ?
            ''', (min_length, max_length, top_k))
        else:
            cursor = conn.execute(f'''
                SELECT id, title, url, content, source, bias, LENGTH(content) as content_length
                FROM {TABLE_NAME} 
                WHERE LENGTH(content) >= ?
                ORDER BY LENGTH(content) DESC
                LIMIT ?
            ''', (min_length, top_k))
        
        results = []
        for row in cursor:
            id, title, url, content, source, bias, content_length = row
            results.append({
                'id': id,
                'title': title,
                'url': url,
                'content': content,
                'source': source,
                'bias': bias,
                'content_length': content_length
            })
        
        return results