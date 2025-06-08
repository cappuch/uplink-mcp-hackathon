from utils.db import write_record, read_records, find_record_by_url, get_write_queue_stats
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

API_KEY = os.getenv("DB_API_KEY")

def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

class NewsRecord(BaseModel):
    title: str
    url: str
    content: str
    embedding: List[float]
    source: str
    bias: str

@app.post("/news/write")
def write_record_endpoint(
    record: NewsRecord,
    _: None = Depends(verify_api_key)
) -> Dict[str, Any]:
    write_record(
        record.title, 
        record.url, 
        record.content, 
        record.embedding, 
        record.source, 
        record.bias
    )
    return {"message": "Record written successfully"}

@app.get("/news/read")
def read_records_endpoint(
    _: None = Depends(verify_api_key)
) -> List[Dict[str, Any]]:
    return read_records()

@app.get("/news/find")
def find_record_by_url_endpoint(
    url: str,
    _: None = Depends(verify_api_key)
) -> Dict[str, Any]:
    record = find_record_by_url(url)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record

@app.get("/queue/stats")
def get_queue_stats_endpoint(
    _: None = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Get write queue statistics."""
    return get_write_queue_stats()

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Database API",
        "queue_stats": get_write_queue_stats()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
