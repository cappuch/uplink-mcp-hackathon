import requests

query = "north korea"
url = f"http://localhost:8000/news/search?query={query}&top_k=10"
response = requests.get(url)
if response.status_code == 200:
    results = response.json()
    print(f"Search results for '{query}':")
    for article in results:
        print(f"- {article['title']} ({article['url']})")