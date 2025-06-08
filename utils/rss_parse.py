from rss_parser import RSSParser
from requests import get
import feedparser
import xml.etree.ElementTree as ET

def get_rss(rss_url: str):
    """Get RSS feed with fallback parsing methods"""
    try:
        response = get(rss_url, timeout=10)
        response.raise_for_status()
        
        if not response.text.strip():
            print(f"Empty response from {rss_url}")
            return None
        
        try:
            rss = RSSParser.parse(response.text)
            return rss
        except Exception as parser_error:
            print(f"RSS parser failed for {rss_url}: {parser_error}")
            
            try:
                feed = feedparser.parse(response.text)
                if feed.entries:
                    return feed
                else:
                    print(f"Feedparser found no entries in {rss_url}")
                    return None
            except Exception as feedparser_error:
                print(f"Feedparser also failed for {rss_url}: {feedparser_error}")
                return None
                
    except Exception as e:
        print(f"Network error for {rss_url}: {e}")
        return None