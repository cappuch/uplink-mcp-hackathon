import requests
from concurrent.futures import ThreadPoolExecutor

from utils.rss_parse import get_rss
from utils.db import write_record

from utils.mappings import mappings
from utils.news_content_strip import extract_main_content

from utils.models import embed_text, extract, bias
import tqdm
import traceback

processed_urls = set()

def fetch_content(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.Timeout:
        print(f"Timeout fetching {url}")
        return ""
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

def process_entry(entry, feed_name):
    try:
        url = str(entry.links[0].content if hasattr(entry.links[0], "content") else entry.links[0])
        
        if url in processed_urls:
            return None
        processed_urls.add(url)
        
        content = fetch_content(url) if entry.links else ""
        if not content:
            print(f"No content found for {entry.title.content} in {feed_name} ({url})")
            return None
        
        extracted_content = extract_main_content(content)
        processed_content = extract(extracted_content)
        
        embedding = embed_text(processed_content)
        bias_result = bias(processed_content)
        
        return {
            'title': str(entry.title.content),
            'url': url,
            'content': str(processed_content),
            'embedding': embedding,
            'source': str(feed_name),
            'bias': str(bias_result)
        }
    except Exception as e:
        print("="*60)
        print(f"Error processing entry in feed '{feed_name}':")
        print(f"  Title: {getattr(entry.title, 'content', entry.title) if hasattr(entry, 'title') else entry}")
        print(f"  URL: {url if 'url' in locals() else 'N/A'}")
        print(f"  Exception: {e}")
        print("  Traceback:")
        traceback.print_exc()
        print("="*60)
        return None

def write_batch_to_db(batch_data):
    """Write a batch of processed articles to the database"""
    for data in batch_data:
        if data:
            write_record(**data)

def process_feed(feed_name, feeds):
    print(f"Fetching feeds for {feed_name}")
    batch_size = 10
    
    for feed_url in tqdm.tqdm(feeds, desc=f"{feed_name} feeds"):
        rss = get_rss(feed_url)
        entries = rss.channel.items if rss else []
        
        for i in range(0, len(entries), batch_size):
            batch_entries = entries[i:i + batch_size]
            
            batch_results = []
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [
                    executor.submit(process_entry, entry, feed_name)
                    for entry in batch_entries
                ]
                
                for future in tqdm.tqdm(futures, desc=f"Batch {i//batch_size + 1}", leave=False):
                    try:
                        result = future.result()
                        batch_results.append(result)
                    except Exception as e:
                        print(f"Error in thread: {e}")
                        batch_results.append(None)
            
            valid_results = [r for r in batch_results if r is not None]
            
            if valid_results:
                write_batch_to_db(valid_results)
                print(f"Processed and wrote batch of {len(valid_results)} articles to database")

def main():
    for feed_name, feeds in mappings.items():
        print(f"\n=== Processing {feed_name} ===")
        process_feed(feed_name, feeds)
        print(f"=== Completed {feed_name} ===\n")

if __name__ == "__main__":
    main()