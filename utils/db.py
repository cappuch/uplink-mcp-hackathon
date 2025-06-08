import sqlite3
import json
from .write_queue import write_record_queued

DB_FILE = 'data.db'
TABLE_NAME = 'records'

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute(f'''
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                url TEXT UNIQUE,
                content TEXT,
                embedding TEXT,
                source TEXT,
                bias TEXT
            )
        ''')
        conn.commit()

def write_record(title, url, content, embedding, source, bias):
    """
    Write a record to the database using the write queue.
    This ensures only one writer processes database writes at a time.
    """
    task = write_record_queued(title, url, content, embedding, source, bias, wait=True, timeout=30.0)
    
    if task.error:
        raise task.error
    
    return task.result

def read_records():
    """
    Read all records from the database.
    Returns a list of dicts.
    """
    with get_connection() as conn:
        cursor = conn.execute(f'SELECT title, url, content, embedding, source, bias FROM {TABLE_NAME}')
        records = []
        for row in cursor:
            title, url, content, embedding_str, source, bias = row
            try:
                embedding = json.loads(embedding_str)
            except Exception:
                embedding = []
            records.append({
                'title': title,
                'url': url,
                'content': content,
                'embedding': embedding,
                'source': source,
                'bias': bias
            })
        return records

def find_record_by_url(url):
    """
    Find a record by URL.
    Returns the record or None if not found.
    """
    with get_connection() as conn:
        cursor = conn.execute(f'''
            SELECT title, url, content, embedding, source, bias FROM {TABLE_NAME} WHERE url=?
        ''', (url,))
        row = cursor.fetchone()
        if row:
            title, url, content, embedding_str, source, bias = row
            try:
                embedding = json.loads(embedding_str)
            except Exception:
                embedding = []
            return {
                'title': title,
                'url': url,
                'content': content,
                'embedding': embedding,
                'source': source,
                'bias': bias
            }
    return None

count_total_records = 0
def count_total_records():
    """
    Count total number of records in the database.
    """
    with get_connection() as conn:
        cursor = conn.execute(f'SELECT COUNT(*) FROM {TABLE_NAME}')
        return cursor.fetchone()[0]

def count_short_content_records(min_length=50):
    """
    Count records with content shorter than min_length.
    """
    with get_connection() as conn:
        cursor = conn.execute(f'''
            SELECT COUNT(*) FROM {TABLE_NAME} 
            WHERE LENGTH(content) < ?
        ''', (min_length,))
        return cursor.fetchone()[0]

def get_write_queue_stats():
    """Get write queue statistics."""
    from .write_queue import get_queue_stats
    return get_queue_stats()

init_db()