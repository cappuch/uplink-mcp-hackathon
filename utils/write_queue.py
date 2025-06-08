import queue
import threading
import time
import sqlite3
import json
from typing import Dict, Any, Callable
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_FILE = 'data.db'
TABLE_NAME = 'records'

class WriteTask:
    """Represents a database write task."""
    
    def __init__(self, operation: str, data: Dict[str, Any], callback: Callable = None):
        self.operation = operation
        self.data = data
        self.callback = callback
        self.result = None
        self.error = None
        self.completed = threading.Event()
    
    def set_result(self, result):
        """Set the result and mark as completed."""
        self.result = result
        self.completed.set()
        if self.callback:
            self.callback(result, None)
    
    def set_error(self, error):
        """Set the error and mark as completed."""
        self.error = error
        self.completed.set()
        if self.callback:
            self.callback(None, error)
    
    def wait(self, timeout=None):
        """Wait for the task to complete."""
        return self.completed.wait(timeout)

class DatabaseWriteQueue:
    """Queue manager for database write operations."""
    
    def __init__(self):
        self.write_queue = queue.Queue()
        self.worker_thread = None
        self.running = False
        self.stats = {
            'total_writes': 0,
            'successful_writes': 0,
            'failed_writes': 0,
            'queue_size': 0
        }
        self._lock = threading.Lock()
    
    def start(self):
        """Start the write worker thread."""
        if self.running:
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        logger.info("Database write queue started")
    
    def stop(self, timeout=10):
        """Stop the write worker thread."""
        if not self.running:
            return
        
        self.running = False
        
        self.write_queue.put(None)
        
        if self.worker_thread:
            self.worker_thread.join(timeout=timeout)
        
        logger.info("Database write queue stopped")
    
    def _worker(self):
        """Worker thread that processes write operations."""
        logger.info("Database write worker started")
        
        while self.running:
            try:
                task = self.write_queue.get(timeout=1.0)
                
                if task is None:
                    break
                
                self._process_task(task)
                self.write_queue.task_done()
                
                with self._lock:
                    self.stats['queue_size'] = self.write_queue.qsize()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Unexpected error in write worker: {e}")
        
        logger.info("Database write worker stopped")
    
    def _process_task(self, task: WriteTask):
        """Process a single write task."""
        try:
            with self._lock:
                self.stats['total_writes'] += 1
            
            if task.operation == 'write_record':
                self._write_record_direct(task.data)
                task.set_result({"message": "Record written successfully"})
                
                with self._lock:
                    self.stats['successful_writes'] += 1
            
            else:
                raise ValueError(f"Unknown operation: {task.operation}")
        
        except Exception as e:
            logger.error(f"Error processing write task: {e}")
            task.set_error(e)
            
            with self._lock:
                self.stats['failed_writes'] += 1
    
    def _write_record_direct(self, data: Dict[str, Any]):
        """Directly write a record to the database."""
        title = data['title']
        url = data['url']
        content = data['content']
        embedding = data['embedding']
        source = data['source']
        bias = data['bias']
        
        # Store embedding as JSON string
        if hasattr(embedding, 'tolist'):
            embedding = embedding.tolist()
        embedding_str = json.dumps(embedding)
        
        conn = sqlite3.connect(DB_FILE)
        try:
            conn.execute(f'''
                INSERT OR REPLACE INTO {TABLE_NAME} (title, url, content, embedding, source, bias)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (title, url, content, embedding_str, source, str(bias)))
            conn.commit()
        finally:
            conn.close()
    
    def queue_write(self, operation: str, data: Dict[str, Any], callback: Callable = None, wait: bool = False, timeout: float = 30.0) -> WriteTask:
        """Queue a write operation."""
        if not self.running:
            self.start()
        
        task = WriteTask(operation, data, callback)
        self.write_queue.put(task)
        
        with self._lock:
            self.stats['queue_size'] = self.write_queue.qsize()
        
        if wait:
            task.wait(timeout)
            if task.error:
                raise task.error
        
        return task
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        with self._lock:
            stats = self.stats.copy()
            stats['queue_size'] = self.write_queue.qsize()
            stats['running'] = self.running
        return stats

write_queue = DatabaseWriteQueue()

def write_record_queued(title, url, content, embedding, source, bias, wait=True, timeout=30.0):
    """
    Queue a write operation for the database.
    
    Args:
        title: Article title
        url: Article URL
        content: Article content
        embedding: Article embedding
        source: Article source
        bias: Article bias
        wait: Whether to wait for completion
        timeout: Maximum time to wait for completion
    
    Returns:
        WriteTask object
    """
    data = {
        'title': title,
        'url': url,
        'content': content,
        'embedding': embedding,
        'source': source,
        'bias': bias
    }
    
    return write_queue.queue_write('write_record', data, wait=wait, timeout=timeout)

def get_queue_stats():
    """Get write queue statistics."""
    return write_queue.get_stats()

def start_write_queue():
    """Start the write queue."""
    write_queue.start()

def stop_write_queue(timeout=10):
    """Stop the write queue."""
    write_queue.stop(timeout)

start_write_queue()
