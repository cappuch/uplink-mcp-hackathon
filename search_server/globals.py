from dotenv import load_dotenv
import os

load_dotenv()

global request_count
request_count = 0

REQUESTS_COUNT_FILE = os.environ.get("REQUESTS_COUNT_FILE", "req_count")

def load_request_count() -> int:
    """Load the request count from file."""
    try:
        with open(REQUESTS_COUNT_FILE, "rt") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        save_request_count(0)
        return 0

def save_request_count(count: int) -> None:
    """Save the request count to file."""
    try:
        with open(REQUESTS_COUNT_FILE, "wt") as f:
            f.write(str(count))
    except OSError as e:
        print(f"Error saving request count: {e}")

def increment_request_count() -> None:
    """Increment and save the request count."""
    global request_count
    request_count += 1
    save_request_count(request_count)

def get_request_count() -> int:
    """Get the current request count (refreshed from file)."""
    global request_count
    request_count = load_request_count()
    return request_count